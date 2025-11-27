from __future__ import annotations

import asyncio

from nicegui import ui

from audex.lib.wifi import WiFiManager
from audex.lib.wifi import WiFiNetwork
from audex.lib.wifi import WiFiSecurity


def _get_wifi_icon_and_color(signal_quality: int, is_connected: bool) -> tuple[str, str]:
    """Get WiFi icon and color based on signal quality."""
    if is_connected:
        if signal_quality >= 75:
            return "signal_wifi_4_bar", "text-positive"
        if signal_quality >= 50:
            return "network_wifi_3_bar", "text-positive"
        if signal_quality >= 25:
            return "network_wifi_2_bar", "text-warning"
        return "network_wifi_1_bar", "text-warning"
    return "signal_wifi_off", "text-grey-6"


def _get_security_label(security: WiFiSecurity) -> str:
    """Get human-readable security label."""
    security_map = {
        WiFiSecurity.OPEN: "开放",
        WiFiSecurity.WEP: "WEP",
        WiFiSecurity.WPA: "WPA",
        WiFiSecurity.WPA2: "WPA2",
        WiFiSecurity.WPA3: "WPA3",
        WiFiSecurity.UNKNOWN: "未知",
    }
    return security_map.get(security, "未知")


class WiFiIndicator:
    """WiFi status indicator component."""

    def __init__(self, wifi_manager: WiFiManager) -> None:
        self.wifi_manager = wifi_manager
        self.icon_display: ui.button | None = None

        # Dialog state
        self.dialog: ui.dialog | None = None
        self.current_conn_container: ui.column | None = None
        self.networks_container: ui.column | None = None
        self.scanning = False
        self.disconnecting = False

        # Track expanded state
        self.expanded_ssids: set[str] = set()

    def render(self) -> ui.button:
        """Render WiFi indicator as a simple icon button."""
        self.icon_display = (
            ui.button(icon="signal_wifi_off", on_click=self._show_dialog)
            .props("flat round")
            .classes("wifi-indicator-btn text-grey-6")
            .tooltip("WiFi 设置")
        )

        # Start status polling
        asyncio.create_task(self._initial_update())  # noqa
        ui.timer(5.0, self._update_status)

        return self.icon_display

    async def _initial_update(self) -> None:
        """Initial status update."""
        await asyncio.sleep(0.1)
        await self._update_status()

    async def _update_status(self) -> None:
        """Update WiFi status display."""
        if not self.icon_display:
            return

        try:
            is_available = getattr(self.wifi_manager, "is_available", False)
            if not is_available:
                self.icon_display.props('icon="signal_wifi_off"')
                self.icon_display.classes(
                    "text-grey-4", remove="text-positive text-warning text-grey-6"
                )
                return

            conn_info = await self.wifi_manager.get_connection_info()
            if conn_info:
                icon, color = _get_wifi_icon_and_color(conn_info.signal_quality, True)
                self.icon_display.props(f'icon="{icon}"')
                self.icon_display.classes(
                    color, remove="text-positive text-warning text-grey-6 text-grey-4"
                )
            else:
                self.icon_display.props('icon="signal_wifi_off"')
                self.icon_display.classes(
                    "text-grey-6", remove="text-positive text-warning text-grey-4"
                )

        except Exception as e:
            print(f"[WiFi] Update error: {e}")
            if self.icon_display:
                self.icon_display.props('icon="signal_wifi_off"')
                self.icon_display.classes(
                    "text-grey-4", remove="text-positive text-warning text-grey-6"
                )

    def _show_dialog(self) -> None:
        """Show WiFi management dialog."""
        with (
            ui.dialog() as dialog,
            ui.card()
            .classes("wifi-dialog-card")
            .style("width: 540px; max-width: 90vw; padding: 28px;"),
        ):
            self.dialog = dialog

            # Header
            with ui.row().classes("items-center justify-between w-full mb-4"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("wifi", size="md").classes("text-primary")
                    ui.label("WiFi 设置").classes("text-h6 font-bold text-grey-9")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense").classes(
                    "press-button"
                )

            # Loading overlay
            loading_container = ui.column().classes("w-full items-center gap-3 py-8")
            with loading_container:
                ui.spinner(size="lg").classes("text-primary")
                ui.label("正在扫描网络...").classes("text-body2 text-grey-7")

            # Current connection - fixed at top
            self.current_conn_container = ui.column().classes("w-full").style("display: none;")

            # Scan button
            with (
                ui.row()
                .classes("items-center justify-between w-full mb-3")
                .style("margin-top: 16px;")
            ):
                ui.label("可用网络").classes("text-subtitle2 font-semibold text-grey-8")

                async def do_rescan():
                    if self.scanning:
                        return
                    self.scanning = True
                    scan_btn.props("loading")
                    # Clear expanded state on rescan
                    self.expanded_ssids.clear()
                    await self._scan_networks()
                    scan_btn.props(remove="loading")
                    self.scanning = False

                scan_btn = (
                    ui.button(icon="refresh", on_click=do_rescan)
                    .props("flat round dense")
                    .classes("wifi-scan-btn")
                )

            # Networks container - scrollable
            self.networks_container = (
                ui.column()
                .classes("w-full gap-2")
                .style("max-height: 380px; overflow-y: auto; display: none; scrollbar-with: none;")
            )

            # Scan in background
            async def load_networks():
                await self._scan_networks()
                loading_container.style("display: none;")
                if self.current_conn_container:
                    self.current_conn_container.style("display: flex;")
                if self.networks_container:
                    self.networks_container.style("display: flex;")

            asyncio.create_task(load_networks())  # noqa

        dialog.open()

    async def _scan_networks(self) -> None:
        """Scan and display networks."""
        if not self.current_conn_container or not self.networks_container:
            return

        self.current_conn_container.clear()
        self.networks_container.clear()

        try:
            conn_info = await self.wifi_manager.get_connection_info()
            current_ssid = conn_info.ssid if conn_info else None

            # Current connection card - fixed at top
            if conn_info:
                with (
                    self.current_conn_container,
                    ui.card().classes("w-full wifi-current-card"),
                    ui.row().classes("items-center justify-between w-full"),
                ):
                    with ui.row().classes("items-center gap-3"):
                        icon, color = _get_wifi_icon_and_color(conn_info.signal_quality, True)
                        ui.icon(icon, size="md").classes(color)
                        with ui.column().classes("gap-0"):
                            ui.label(conn_info.ssid).classes("text-body1 font-semibold text-grey-9")
                            status_parts = [f"已连接 · {conn_info.signal_quality}%"]
                            if conn_info.ip_address:
                                status_parts.append(conn_info.ip_address)
                            ui.label(" · ".join(status_parts)).classes("text-xs text-grey-7")

                    async def do_disconnect():
                        if self.disconnecting:
                            return
                        self.disconnecting = True
                        disconnect_btn.props("loading")

                        success = await self.wifi_manager.disconnect()

                        disconnect_btn.props(remove="loading")
                        self.disconnecting = False

                        if success:
                            ui.notify("已断开连接", type="positive")
                            await self._update_status()
                            await self._scan_networks()
                        else:
                            ui.notify("断开失败", type="negative")

                    disconnect_btn = (
                        ui.button(icon="link_off", on_click=do_disconnect)
                        .props("flat")
                        .classes("wifi-disconnect-btn")
                        .tooltip("断开连接")
                    )

            # Scan networks
            networks = await self.wifi_manager.scan()

            if not networks:
                with self.networks_container, ui.column().classes("items-center gap-3 py-8"):
                    ui.icon("wifi_off", size="xl").classes("text-grey-4")
                    ui.label("未找到网络").classes("text-body2 text-grey-6")
                return

            # Filter out current network from list
            available_networks = [n for n in networks if n.ssid != current_ssid]

            # Display available networks
            with self.networks_container:
                for network in available_networks:
                    self._render_network_card(network)

        except Exception as e:
            if self.networks_container:
                self.networks_container.clear()
                with self.networks_container, ui.column().classes("items-center gap-3 py-8"):
                    ui.icon("error_outline", size="xl").classes("text-negative")
                    ui.label(f"扫描失败: {e!s}").classes("text-body2 text-negative")

    def _render_network_card(self, network: WiFiNetwork) -> None:
        """Render a single network card with expandable connect form."""
        is_expanded = network.ssid in self.expanded_ssids

        card_container = ui.column().classes("w-full").style("gap: 8px;")

        with card_container:
            # Store form container reference
            form_container = None
            expand_icon = None

            # Toggle function - only one expanded at a time
            def make_toggle_handler(ssid: str):
                def toggle():
                    # If clicking already expanded, just collapse it
                    if ssid in self.expanded_ssids:
                        self.expanded_ssids.remove(ssid)
                        if form_container:
                            # Collapse animation
                            form_container.style(
                                "display: flex; max-height: 0; opacity: 0; padding-top: 0; padding-bottom: 0;"
                            )
                            ui.timer(0.4, lambda: form_container.style("display: none;"), once=True)
                        if expand_icon:
                            expand_icon.props('name="expand_more"')
                    else:
                        # Collapse all other cards first
                        self.expanded_ssids.clear()

                        # Re-render to collapse others (we need to track all form containers)
                        # For now, just clear and add this one
                        self.expanded_ssids.add(ssid)

                        if form_container:
                            # Expand animation
                            form_container.style("display: flex; max-height: 0; opacity: 0;")
                            ui.timer(
                                0.01,
                                lambda: form_container.style(
                                    "display: flex; max-height: 80px; opacity: 1; padding-top: 12px; padding-bottom: 12px;"
                                ),
                                once=True,
                            )
                        if expand_icon:
                            expand_icon.props('name="expand_less"')

                return toggle

            # Network info card
            with (
                (
                    ui.card()
                    .classes("w-full wifi-network-card")
                    .on("click", make_toggle_handler(network.ssid))
                ),
                ui.row().classes("items-center justify-between w-full"),
            ):
                with ui.row().classes("items-center gap-3 flex-1"):
                    icon, color = _get_wifi_icon_and_color(
                        network.signal_quality, network.is_connected
                    )
                    ui.icon(icon, size="md").classes(color)

                    with ui.column().classes("gap-0 flex-1"):
                        ui.label(network.ssid).classes("text-body1 font-semibold text-grey-9")

                        info_parts = [
                            f"{network.signal_quality}%",
                            _get_security_label(network.security),
                        ]
                        if network.channel:
                            info_parts.append(f"信道 {network.channel}")
                        ui.label(" · ".join(info_parts)).classes("text-xs text-grey-7")

                with ui.row().classes("items-center gap-2"):
                    if network.security != WiFiSecurity.OPEN:
                        ui.icon("lock", size="sm").classes("text-grey-6")
                    expand_icon = ui.icon(
                        "expand_less" if is_expanded else "expand_more", size="sm"
                    ).classes("text-grey-6")

            # Expandable connect form
            initial_style = (
                "display: flex; max-height: 80px; opacity: 1; padding: 12px;"
                if is_expanded
                else "display: none; max-height: 0; opacity: 0; padding: 0;"
            )

            form_container = (
                ui.column().classes("w-full wifi-connect-form").style(f"{initial_style} gap: 0;")
            )
            # Row layout: password input + connect button
            with form_container, ui.row().classes("items-center w-full").style("gap: 12px;"):
                if network.security != WiFiSecurity.OPEN:
                    password_input = (
                        ui.input("密码", password=True, password_toggle_button=True)
                        .classes("flex-1 clean-input")
                        .props("standout dense outlined")
                        .style("margin: 0;")
                    )
                else:
                    password_input = None
                    ui.label("此网络无需密码").classes("text-body2 text-grey-6 flex-1")

                def make_connect_handler(net: WiFiNetwork, pwd_input):
                    async def do_connect():
                        # Get password if needed
                        password = None
                        if pwd_input:
                            password = pwd_input.value.strip()
                            if not password:
                                ui.notify("请输入密码", type="warning")
                                return

                        connect_btn.props("loading")

                        # Disconnect current connection first
                        conn_info = await self.wifi_manager.get_connection_info()
                        if conn_info:
                            await self.wifi_manager.disconnect()
                            await asyncio.sleep(1)

                        # Connect to new network
                        success = await self.wifi_manager.connect(net.ssid, password)

                        connect_btn.props(remove="loading")

                        if success:
                            ui.notify(f"已连接到 {net.ssid}", type="positive")
                            await self._update_status()
                            if self.dialog:
                                self.dialog.close()
                        else:
                            ui.notify("连接失败，请检查密码", type="negative")

                    return do_connect

                # Connect button with arrow_forward icon
                connect_btn = (
                    ui.button(
                        icon="arrow_forward",
                        on_click=make_connect_handler(network, password_input),
                    )
                    .props("flat")
                    .classes("wifi-connect-btn")
                    .tooltip("连接到此网络")
                )
