from __future__ import annotations

import abc
import asyncio
import enum
import pathlib
import platform
import re
import typing as t

from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin


class WiFiSecurity(str, enum.Enum):
    """WiFi security types."""

    OPEN = "open"
    WEP = "wep"
    WPA = "wpa"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    UNKNOWN = "unknown"


class WiFiStatus(str, enum.Enum):
    """WiFi connection status."""

    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    UNKNOWN = "unknown"


class WiFiNetwork(t.NamedTuple):
    """Represents a WiFi network.

    Attributes:
        ssid: Network SSID (name).
        bssid: MAC address of the access point.
        signal_strength: Signal strength in dBm (e.g., -50).
        signal_quality: Signal quality percentage (0-100).
        frequency: Frequency in MHz (e.g., 2412, 5180).
        channel: WiFi channel number.
        security: Security type.
        is_connected: Whether currently connected to this network.
    """

    ssid: str
    bssid: str | None
    signal_strength: int  # dBm
    signal_quality: int  # 0-100
    frequency: int | None  # MHz
    channel: int | None
    security: WiFiSecurity
    is_connected: bool


class WiFiConnectionInfo(t.NamedTuple):
    """Current WiFi connection information.

    Attributes:
        ssid: Connected network SSID.
        bssid: Connected access point BSSID.
        signal_strength: Current signal strength in dBm.
        signal_quality: Current signal quality percentage.
        frequency: Connection frequency in MHz.
        channel: Connection channel.
        link_speed: Link speed in Mbps.
        ip_address: Assigned IP address.
        status: Connection status.
    """

    ssid: str
    bssid: str | None
    signal_strength: int
    signal_quality: int
    frequency: int | None
    channel: int | None
    link_speed: int | None  # Mbps
    ip_address: str | None
    status: WiFiStatus


class WiFiBackend(abc.ABC):
    """Abstract base class for WiFi backends."""

    def __init__(self, logger: t.Any) -> None:
        self.logger = logger

    @abc.abstractmethod
    async def scan(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks."""

    @abc.abstractmethod
    async def connect(self, ssid: str, password: str | None = None) -> bool:
        """Connect to a WiFi network."""

    @abc.abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from WiFi network."""

    @abc.abstractmethod
    async def get_connection_info(self) -> WiFiConnectionInfo | None:
        """Get current connection information."""

    @abc.abstractmethod
    async def is_available(self) -> bool:
        """Check if WiFi adapter is available."""


class LinuxWiFiBackend(WiFiBackend):
    """Linux WiFi backend using NetworkManager (nmcli)."""

    def __init__(self, logger: t.Any) -> None:
        super().__init__(logger)
        self._interface: str | None = None

    async def is_available(self) -> bool:
        """Check if nmcli is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                "nmcli",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def _get_interface(self) -> str | None:
        """Get the first available WiFi interface."""
        if self._interface:
            return self._interface

        try:
            result = await asyncio.create_subprocess_exec(
                "nmcli",
                "-t",
                "-f",
                "DEVICE,TYPE",
                "device",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                lines = stdout.decode("utf-8").strip().split("\n")
                for line in lines:
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[1] == "wifi":
                        self._interface = parts[0]
                        self.logger.debug(f"Found WiFi interface: {self._interface}")
                        return self._interface

        except Exception as e:
            self.logger.error(f"Failed to get WiFi interface: {e}")

        return None

    def _parse_security(self, security_str: str) -> WiFiSecurity:
        """Parse security type from nmcli output."""
        security_str = security_str.upper()
        if not security_str or security_str == "--":
            return WiFiSecurity.OPEN
        if "WPA3" in security_str:
            return WiFiSecurity.WPA3
        if "WPA2" in security_str:
            return WiFiSecurity.WPA2
        if "WPA" in security_str:
            return WiFiSecurity.WPA
        if "WEP" in security_str:
            return WiFiSecurity.WEP
        return WiFiSecurity.UNKNOWN

    def _dbm_to_quality(self, dbm: int) -> int:
        """Convert dBm to quality percentage."""
        # Typical range: -90 dBm (poor) to -30 dBm (excellent)
        if dbm >= -30:
            return 100
        if dbm <= -90:
            return 0
        return int((dbm + 90) * 100 / 60)

    async def scan(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks using nmcli."""
        interface = await self._get_interface()
        if not interface:
            self.logger.warning("No WiFi interface available")
            return []

        try:
            # Request rescan
            await asyncio.create_subprocess_exec(
                "nmcli",
                "device",
                "wifi",
                "rescan",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.sleep(1)  # Wait for scan to complete

            # Get scan results
            result = await asyncio.create_subprocess_exec(
                "nmcli",
                "-t",
                "-f",
                "SSID,BSSID,MODE,CHAN,FREQ,RATE,SIGNAL,SECURITY,IN-USE",
                "device",
                "wifi",
                "list",
                "ifname",
                interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                self.logger.error(f"WiFi scan failed: {stderr.decode('utf-8')}")
                return []

            networks: list[WiFiNetwork] = []
            seen_ssids: set[str] = set()

            lines = stdout.decode("utf-8").strip().split("\n")
            for line in lines:
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) < 9:
                    continue

                ssid = parts[0].strip()
                if not ssid or ssid in seen_ssids:
                    continue

                bssid = parts[1].strip() or None
                channel_str = parts[3].strip()
                freq_str = parts[4].strip()
                signal_str = parts[6].strip()
                security_str = parts[7].strip()
                is_connected = parts[8].strip() == "*"

                try:
                    signal_strength = -100 + int(signal_str)  # Convert to dBm
                    signal_quality = int(signal_str)
                    channel = int(channel_str) if channel_str else None
                    frequency = int(freq_str) if freq_str else None
                except ValueError:
                    signal_strength = -100
                    signal_quality = 0
                    channel = None
                    frequency = None

                security = self._parse_security(security_str)

                network = WiFiNetwork(
                    ssid=ssid,
                    bssid=bssid,
                    signal_strength=signal_strength,
                    signal_quality=signal_quality,
                    frequency=frequency,
                    channel=channel,
                    security=security,
                    is_connected=is_connected,
                )
                networks.append(network)
                seen_ssids.add(ssid)

            self.logger.debug(f"Found {len(networks)} WiFi networks")
            return networks

        except Exception as e:
            self.logger.error(f"WiFi scan error: {e}", exc_info=True)
            return []

    async def connect(self, ssid: str, password: str | None = None) -> bool:
        """Connect to a WiFi network using nmcli."""
        try:
            args = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                args.extend(["password", password])

            result = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await result.communicate()

            if result.returncode == 0:
                self.logger.info(f"Successfully connected to {ssid}")
                return True
            error_msg = stderr.decode("utf-8").strip()
            self.logger.error(f"Failed to connect to {ssid}: {error_msg}")
            return False

        except Exception as e:
            self.logger.error(f"Error connecting to {ssid}: {e}", exc_info=True)
            return False

    async def disconnect(self, ssid: str | None = None) -> bool:
        """Disconnect from WiFi network."""
        interface = await self._get_interface()
        if not interface:
            self.logger.warning("No WiFi interface available")
            return False

        try:
            if ssid:
                # Disconnect specific connection
                result = await asyncio.create_subprocess_exec(
                    "nmcli",
                    "connection",
                    "down",
                    ssid,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # Disconnect interface
                result = await asyncio.create_subprocess_exec(
                    "nmcli",
                    "device",
                    "disconnect",
                    interface,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            await result.communicate()

            if result.returncode == 0:
                self.logger.info("Successfully disconnected from WiFi")
                return True
            self.logger.warning("Failed to disconnect from WiFi")
            return False

        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}", exc_info=True)
            return False

    async def get_connection_info(self) -> WiFiConnectionInfo | None:
        """Get current connection information."""
        interface = await self._get_interface()
        if not interface:
            return None

        try:
            result = await asyncio.create_subprocess_exec(
                "nmcli",
                "-t",
                "-f",
                "GENERAL.CONNECTION,GENERAL.STATE,IP4.ADDRESS",
                "device",
                "show",
                interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode != 0:
                return None

            lines = stdout.decode("utf-8").strip().split("\n")
            connection_name = None
            state = None
            ip_address = None

            for line in lines:
                if "GENERAL.CONNECTION:" in line:
                    connection_name = line.split(":", 1)[1].strip()
                elif "GENERAL.STATE:" in line:
                    state_str = line.split(":", 1)[1].strip()
                    state = state_str.split()[0] if state_str else None
                elif "IP4.ADDRESS[1]:" in line:
                    ip_str = line.split(":", 1)[1].strip()
                    ip_address = ip_str.split("/")[0] if ip_str else None

            if not connection_name or connection_name == "--":
                return None

            # Get detailed connection info
            result = await asyncio.create_subprocess_exec(
                "nmcli",
                "-t",
                "-f",
                "SSID,BSSID,FREQ,CHAN,SIGNAL",
                "device",
                "wifi",
                "list",
                "ifname",
                interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            ssid = connection_name
            bssid = None
            signal_strength = -100
            signal_quality = 0
            frequency = None
            channel = None

            if result.returncode == 0:
                lines = stdout.decode("utf-8").strip().split("\n")
                for line in lines:
                    parts = line.split(":")
                    if len(parts) >= 5 and parts[0] == ssid:
                        bssid = parts[1].strip() or None
                        freq_str = parts[2].strip()
                        chan_str = parts[3].strip()
                        sig_str = parts[4].strip()

                        try:
                            frequency = int(freq_str) if freq_str else None
                            channel = int(chan_str) if chan_str else None
                            signal_quality = int(sig_str) if sig_str else 0
                            signal_strength = -100 + signal_quality
                        except ValueError:
                            pass
                        break

            status = WiFiStatus.CONNECTED if state == "100" else WiFiStatus.UNKNOWN

            return WiFiConnectionInfo(
                ssid=ssid,
                bssid=bssid,
                signal_strength=signal_strength,
                signal_quality=signal_quality,
                frequency=frequency,
                channel=channel,
                link_speed=None,
                ip_address=ip_address,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error getting connection info: {e}", exc_info=True)
            return None


class WindowsWiFiBackend(WiFiBackend):
    """Windows WiFi backend using netsh."""

    def __init__(self, logger: t.Any) -> None:
        super().__init__(logger)
        self._interface: str | None = None

    async def is_available(self) -> bool:
        """Check if netsh is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "show",
                "interfaces",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _parse_security(self, auth: str, cipher: str) -> WiFiSecurity:
        """Parse security type from Windows output."""
        auth = auth.upper()
        if "WPA3" in auth:
            return WiFiSecurity.WPA3
        if "WPA2" in auth:
            return WiFiSecurity.WPA2
        if "WPA" in auth:
            return WiFiSecurity.WPA
        if "WEP" in cipher.upper():
            return WiFiSecurity.WEP
        if "OPEN" in auth or not auth:
            return WiFiSecurity.OPEN
        return WiFiSecurity.UNKNOWN

    def _signal_to_dbm(self, quality: int) -> int:
        """Convert Windows signal quality (0-100) to dBm."""
        # Approximate conversion
        if quality >= 100:
            return -30
        if quality <= 0:
            return -90
        return -90 + int(quality * 0.6)

    async def scan(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks using netsh."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "show",
                "networks",
                "mode=bssid",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                self.logger.error(f"WiFi scan failed: {stderr.decode('utf-8')}")
                return []

            output = stdout.decode("utf-8", errors="ignore")
            networks: list[WiFiNetwork] = []
            current_ssid = None
            current_bssid = None
            current_signal = 0
            current_auth = ""
            current_cipher = ""
            current_channel = None

            # Get currently connected network
            connected_ssid = None
            conn_info = await self.get_connection_info()
            if conn_info:
                connected_ssid = conn_info.ssid

            for line in output.split("\n"):
                line = line.strip()

                if line.startswith("SSID"):
                    # Save previous network
                    if current_ssid and current_bssid:
                        signal_dbm = self._signal_to_dbm(current_signal)
                        security = self._parse_security(current_auth, current_cipher)
                        is_connected = current_ssid == connected_ssid

                        network = WiFiNetwork(
                            ssid=str(current_ssid),
                            bssid=current_bssid,
                            signal_strength=signal_dbm,
                            signal_quality=current_signal,
                            frequency=None,
                            channel=current_channel,
                            security=security,
                            is_connected=is_connected,
                        )
                        networks.append(network)

                    # Start new network
                    match = re.search(r"SSID \d+ : (.+)", line)
                    if match:
                        current_ssid = match.group(1).strip()
                        current_bssid = None
                        current_signal = 0
                        current_auth = ""
                        current_cipher = ""
                        current_channel = None

                elif line.startswith("BSSID"):
                    match = re.search(r"BSSID \d+\s+:\s+(.+)", line)
                    if match:
                        current_bssid = match.group(1).strip()

                elif line.startswith("Signal"):
                    match = re.search(r"Signal\s+:\s+(\d+)%", line)
                    if match:
                        current_signal = int(match.group(1))

                elif line.startswith("Authentication"):
                    match = re.search(r"Authentication\s+:\s+(.+)", line)
                    if match:
                        current_auth = match.group(1).strip()

                elif line.startswith("Cipher"):
                    match = re.search(r"Cipher\s+:\s+(.+)", line)
                    if match:
                        current_cipher = match.group(1).strip()

                elif line.startswith("Channel"):
                    match = re.search(r"Channel\s+:\s+(\d+)", line)
                    if match:
                        current_channel = int(match.group(1))

            # Save last network
            if current_ssid and current_bssid:
                signal_dbm = self._signal_to_dbm(current_signal)
                security = self._parse_security(current_auth, current_cipher)
                is_connected = current_ssid == connected_ssid

                network = WiFiNetwork(
                    ssid=str(current_ssid),
                    bssid=current_bssid,
                    signal_strength=signal_dbm,
                    signal_quality=current_signal,
                    frequency=None,
                    channel=current_channel,
                    security=security,
                    is_connected=is_connected,
                )
                networks.append(network)

            self.logger.debug(f"Found {len(networks)} WiFi networks")
            return networks

        except Exception as e:
            self.logger.error(f"WiFi scan error: {e}", exc_info=True)
            return []

    async def connect(self, ssid: str, password: str | None = None) -> bool:
        """Connect to a WiFi network using netsh."""
        try:
            # Check if profile exists
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "show",
                "profiles",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            profiles = stdout.decode("utf-8", errors="ignore")

            profile_exists = ssid in profiles

            if not profile_exists and password:
                # Create profile with password
                profile_xml = f"""<? xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""

                # Save profile to temp file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".xml", delete=False, encoding="utf-8"
                ) as f:
                    f.write(profile_xml)
                    profile_path = f.name

                try:
                    # Add profile
                    result = await asyncio.create_subprocess_exec(
                        "netsh",
                        "wlan",
                        "add",
                        "profile",
                        f"filename={profile_path}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await result.communicate()
                finally:
                    pathlib.Path(profile_path).unlink()

            # Connect to network
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "connect",
                f"name={ssid}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                self.logger.info(f"Successfully connected to {ssid}")
                return True
            error_msg = stderr.decode("utf-8").strip()
            self.logger.error(f"Failed to connect to {ssid}: {error_msg}")
            return False

        except Exception as e:
            self.logger.error(f"Error connecting to {ssid}: {e}", exc_info=True)
            return False

    async def disconnect(self) -> bool:
        """Disconnect from WiFi network."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "disconnect",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            if result.returncode == 0:
                self.logger.info("Successfully disconnected from WiFi")
                return True
            self.logger.warning("Failed to disconnect from WiFi")
            return False

        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}", exc_info=True)
            return False

    async def get_connection_info(self) -> WiFiConnectionInfo | None:
        """Get current connection information."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netsh",
                "wlan",
                "show",
                "interfaces",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode != 0:
                return None

            output = stdout.decode("utf-8", errors="ignore")
            ssid = None
            bssid = None
            signal_quality = 0
            channel = None
            link_speed = None
            state = None

            for line in output.split("\n"):
                line = line.strip()

                if "SSID" in line and "BSSID" not in line:
                    match = re.search(r"SSID\s+:\s+(.+)", line)
                    if match:
                        ssid = match.group(1).strip()

                elif "BSSID" in line:
                    match = re.search(r"BSSID\s+:\s+(.+)", line)
                    if match:
                        bssid = match.group(1).strip()

                elif "Signal" in line:
                    match = re.search(r"Signal\s+:\s+(\d+)%", line)
                    if match:
                        signal_quality = int(match.group(1))

                elif "Channel" in line:
                    match = re.search(r"Channel\s+:\s+(\d+)", line)
                    if match:
                        channel = int(match.group(1))

                elif "Receive rate" in line or "Transmit rate" in line:
                    match = re.search(r":\s+(\d+)", line)
                    if match and not link_speed:
                        link_speed = int(match.group(1))

                elif "State" in line:
                    match = re.search(r"State\s+:\s+(.+)", line)
                    if match:
                        state_str = match.group(1).strip().lower()
                        if "connected" in state_str:
                            state = WiFiStatus.CONNECTED
                        elif "disconnected" in state_str:
                            state = WiFiStatus.DISCONNECTED

            if not ssid:
                return None

            signal_strength = self._signal_to_dbm(signal_quality)

            # Get IP address
            ip_address = None
            try:
                result = await asyncio.create_subprocess_exec(
                    "ipconfig",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()
                output = stdout.decode("utf-8", errors="ignore")

                # Find WiFi adapter section and extract IPv4
                in_wifi_section = False
                for line in output.split("\n"):
                    if "Wireless LAN adapter" in line or "Wi-Fi" in line:
                        in_wifi_section = True
                    elif "adapter" in line:
                        in_wifi_section = False
                    elif in_wifi_section and "IPv4 Address" in line:
                        match = re.search(r":\s+([\d.]+)", line)
                        if match:
                            ip_address = match.group(1)
                            break
            except Exception:
                pass

            return WiFiConnectionInfo(
                ssid=ssid,
                bssid=bssid,
                signal_strength=signal_strength,
                signal_quality=signal_quality,
                frequency=None,
                channel=channel,
                link_speed=link_speed,
                ip_address=ip_address,
                status=state if state else WiFiStatus.UNKNOWN,
            )

        except Exception as e:
            self.logger.error(f"Error getting connection info: {e}", exc_info=True)
            return None


class WiFiManager(LoggingMixin, AsyncContextMixin):
    """Cross-platform WiFi manager for scanning and connecting to
    networks.

    This manager provides functionality to scan for WiFi networks, connect
    and disconnect from networks, and monitor connection status. It
    automatically selects the appropriate backend (Linux/Windows) based
    on the platform.

    Example:
        ```python
        # Create manager
        manager = WiFiManager()
        await manager.init()

        # Scan for networks
        networks = await manager.scan()
        for network in networks:
            print(
                f"{network.ssid}: {network.signal_quality}% "
                f"({network.security.value})"
            )

        # Connect to a network
        success = await manager.connect("MyNetwork", "password123")

        # Get current connection
        info = await manager.get_connection_info()
        if info:
            print(
                f"Connected to {info.ssid} with IP {info.ip_address}"
            )

        # Disconnect
        await manager.disconnect()

        await manager.close()
        ```
    """

    __logtag__ = "audex.lib.wifi.manager"

    def __init__(self) -> None:
        super().__init__()

        # Initialize platform-specific backend
        system = platform.system()
        if system == "Linux":
            self._backend: WiFiBackend = LinuxWiFiBackend(self.logger)
            self.logger.info("Initialized Linux WiFi backend")
        elif system == "Windows":
            self._backend = WindowsWiFiBackend(self.logger)
            self.logger.info("Initialized Windows WiFi backend")
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

        self._available = False

    async def init(self) -> None:
        """Initialize the WiFi manager.

        Checks if WiFi functionality is available on the system.

        Raises:
            RuntimeError: If WiFi is not available.
        """
        self._available = await self._backend.is_available()
        if not self._available:
            raise RuntimeError(
                "WiFi functionality not available. "
                "On Linux, install NetworkManager (nmcli). "
                "On Windows, ensure WiFi adapter is enabled."
            )
        self.logger.info("WiFi manager initialized")

    async def close(self) -> None:
        """Close the WiFi manager and release resources."""
        self.logger.info("WiFi manager closed")

    @property
    def is_available(self) -> bool:
        """Check if WiFi is available."""
        return self._available

    async def scan(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks.

        Returns:
            List of available WiFi networks, sorted by signal strength.

        Example:
            ```python
            networks = await manager.scan()
            for network in networks:
                print(
                    f"{network.ssid}: "
                    f"{network.signal_quality}% "
                    f"({network.signal_strength} dBm) "
                    f"[{network.security.value}]"
                )
            ```
        """
        if not self._available:
            self.logger.warning("WiFi not available")
            return []

        networks = await self._backend.scan()

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda n: n.signal_strength, reverse=True)

        self.logger.debug(f"Scanned {len(networks)} networks")
        return networks

    async def connect(self, ssid: str, password: str | None = None) -> bool:
        """Connect to a WiFi network.

        Args:
            ssid: Network SSID to connect to.
            password: Network password (None for open networks).

        Returns:
            True if connection successful, False otherwise.

        Example:
            ```python
            # Connect to WPA2 network
            success = await manager.connect("MyNetwork", "password123")

            # Connect to open network
            success = await manager.connect("FreeWiFi")
            ```
        """
        if not self._available:
            self.logger.error("WiFi not available")
            return False

        self.logger.info(f"Connecting to {ssid}...")
        return await self._backend.connect(ssid, password)

    async def disconnect(self) -> bool:
        """Disconnect from WiFi network.

        Returns:
            True if disconnection successful, False otherwise.

        Example:
            ```python
            # Disconnect from current network
            await manager.disconnect()

            # Disconnect from specific network (Linux)
            await manager.disconnect("MyNetwork")
            ```
        """
        if not self._available:
            self.logger.error("WiFi not available")
            return False

        self.logger.info("Disconnecting from WiFi...")
        return await self._backend.disconnect()

    async def get_connection_info(self) -> WiFiConnectionInfo | None:
        """Get current WiFi connection information.

        Returns:
            Connection info if connected, None otherwise.

        Example:
            ```python
            info = await manager.get_connection_info()
            if info:
                print(f"SSID: {info.ssid}")
                print(f"Signal: {info.signal_quality}%")
                print(f"IP: {info.ip_address}")
                print(f"Speed: {info.link_speed} Mbps")
            else:
                print("Not connected")
            ```
        """
        if not self._available:
            return None

        return await self._backend.get_connection_info()

    async def is_connected(self) -> bool:
        """Check if currently connected to any WiFi network.

        Returns:
            True if connected, False otherwise.
        """
        info = await self.get_connection_info()
        return info is not None and info.status == WiFiStatus.CONNECTED

    async def get_current_ssid(self) -> str | None:
        """Get SSID of currently connected network.

        Returns:
            SSID if connected, None otherwise.
        """
        info = await self.get_connection_info()
        return info.ssid if info else None

    async def find_network(self, ssid: str) -> WiFiNetwork | None:
        """Find a specific network by SSID.

        Args:
            ssid: Network SSID to find.

        Returns:
            Network if found, None otherwise.

        Example:
            ```python
            network = await manager.find_network("MyNetwork")
            if network:
                if network.signal_quality > 70:
                    await manager.connect(network.ssid, "password")
            ```
        """
        networks = await self.scan()
        for network in networks:
            if network.ssid == ssid:
                return network
        return None
