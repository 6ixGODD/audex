from __future__ import annotations

import json
import os
import pathlib
import typing as t

from pydantic import BaseModel as PydBaseModel
from pydantic import ConfigDict
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings

from audex import utils
from audex.exceptions import RequiredModuleNotFoundError


class BaseModel(PydBaseModel):
    """Base model class with common configuration for all models.

    This class sets default configurations for Pydantic models used in
    the Audex project, ensuring consistent behavior across all derived
    models.
    """

    model_config: t.ClassVar[ConfigDict] = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    def __hash__(self) -> int:
        """Generate a hash based on the model's serializable
        representation.

        Returns:
            An integer hash value.
        """
        serl_dict = self.model_dump()
        serl_json = json.dumps(serl_dict, sort_keys=True)
        return hash(serl_json)

    def __repr__(self) -> str:
        field_reprs = ", ".join(
            f"{field_name}={getattr(self, field_name)!r}"
            for field_name in self.model_fields  # type: ignore
        )
        return f"MODEL <{self.__class__.__name__}({field_reprs})>"


class Settings(BaseSettings):
    """Base settings class with YAML/JSON/dotenv export capabilities."""

    # ============================================================================
    # Public Methods - Loading
    # ============================================================================

    @classmethod
    def from_yaml(cls, path: str | pathlib.Path | os.PathLike[str]) -> t.Self:
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Settings instance.

        Raises:
            RequiredModuleNotFoundError: If PyYAML is not installed.
        """
        try:
            import yaml

            data = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
            return cls.model_validate(data, strict=False)
        except ImportError as e:
            raise RequiredModuleNotFoundError(
                "`yaml` module is required to load configuration from YAML "
                "files. Please install it using `pip install pyyaml`."
            ) from e

    # ============================================================================
    # Public Methods - Export
    # ============================================================================

    def serl(self, include_none: bool = False) -> dict[str, t.Any]:
        """Get a serializable version of the model dump.

        Args:
            include_none: If True, include fields with None values.

        Returns:
            Dictionary with only serializable values.
        """
        raw_dump = self.model_dump()
        return self._clean_dict(raw_dump, include_none=include_none)

    def to_yaml(self, fpath: str | pathlib.Path | os.PathLike[str]) -> None:
        """Export configuration to YAML file with field descriptions as
        comments.

        Args:
            fpath: Path to the output YAML file.
        """
        descriptions = self._collect_field_desc()
        data = self.serl(include_none=True)

        def write_yaml_value(
            f: t.TextIO,
            key: str,
            value: t.Any,
            field_path: str,
            indent: int = 0,
        ) -> None:
            """Write a single YAML key-value pair with proper
            formatting."""
            indent_str = "  " * indent
            desc = descriptions.get(field_path, "")
            comment = f" # {desc}" if desc else ""

            if value is None:
                f.write(f"{indent_str}{key}: ~{comment}\n")
            elif isinstance(value, dict):
                f.write(f"{indent_str}{key}:{comment}\n")
                write_yaml_dict(f, value, field_path, indent + 1)
            elif isinstance(value, list):
                f.write(f"{indent_str}{key}:{comment}\n")
                write_yaml_list(f, value, field_path, indent + 1)
            elif isinstance(value, str) and ("\n" in value or len(value) > 80):
                f.write(f"{indent_str}{key}: |-{comment}\n")
                for line in value.split("\n"):
                    f.write(f"{indent_str}  {line}\n")
            else:
                yaml_value = self._yaml_repr(value)
                f.write(f"{indent_str}{key}: {yaml_value}{comment}\n")

        def write_yaml_dict(
            f: t.TextIO,
            obj: dict[str, t.Any],
            prefix: str,
            indent: int = 0,
        ) -> None:
            """Write a dictionary as YAML."""
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key
                write_yaml_value(f, key, value, field_path, indent)

        def write_yaml_list(
            f: t.TextIO,
            items: list[t.Any],
            prefix: str,
            indent: int = 0,
        ) -> None:
            """Write a list as YAML."""
            indent_str = "  " * indent
            for item in items:
                if isinstance(item, dict):
                    items_list = list(item.items())
                    if items_list:
                        first_key, first_value = items_list[0]
                        first_field_path = f"{prefix}.{first_key}"
                        first_desc = descriptions.get(first_field_path, "")
                        first_comment = f"  # {first_desc}" if first_desc else ""

                        if first_value is None:
                            f.write(f"{indent_str}- {first_key}: ~{first_comment}\n")
                        elif isinstance(first_value, dict):
                            f.write(f"{indent_str}- {first_key}:{first_comment}\n")
                            write_yaml_dict(f, first_value, first_field_path, indent + 1)
                        elif isinstance(first_value, list):
                            f.write(f"{indent_str}- {first_key}:{first_comment}\n")
                            write_yaml_list(f, first_value, first_field_path, indent + 1)
                        elif isinstance(first_value, str) and (
                            "\n" in first_value or len(first_value) > 80
                        ):
                            f.write(f"{indent_str}- {first_key}: |-{first_comment}\n")
                            for line in first_value.split("\n"):
                                f.write(f"{indent_str}    {line}\n")
                        else:
                            yaml_val = self._yaml_repr(first_value)
                            f.write(f"{indent_str}- {first_key}: {yaml_val}{first_comment}\n")

                        for sub_key, sub_value in items_list[1:]:
                            sub_field_path = f"{prefix}.{sub_key}"
                            write_yaml_value(f, sub_key, sub_value, sub_field_path, indent + 1)
                elif isinstance(item, list):
                    f.write(f"{indent_str}-\n")
                    write_yaml_list(f, item, prefix, indent + 1)
                else:
                    yaml_item = self._yaml_repr(item)
                    f.write(f"{indent_str}- {yaml_item}\n")

        with pathlib.Path(fpath).open("w", encoding="utf-8") as f:
            write_yaml_dict(f, data, "")

    def to_system_yaml(
        self,
        fpath: str | pathlib.Path | os.PathLike[str],
        platform: t.Literal["linux", "windows"] | None = None,
    ) -> None:
        """Export system configuration to YAML file with platform-
        specific defaults.

        This method generates a system configuration file using platform-specific
        default values defined in AudexFieldInfo descriptors. Fields with Unset
        values are omitted. Empty nested models (all fields Unset) are also omitted.

        Args:
            fpath: Path to the output YAML file
            platform: Target platform ("linux" or "windows"). If None, uses current platform.
        """
        if platform is None:
            platform = "linux" if os.name != "nt" else "windows"

        # Build data with platform-specific defaults
        data = self._build_platform_data(self.__class__, platform)

        # Clean Unset values and empty dicts
        data = self._clean_unset_values(data)

        # Write YAML without comments
        with pathlib.Path(fpath).open("w", encoding="utf-8") as f:
            self._write_system_yaml_header(f, platform)
            self._write_yaml_dict(f, data)

    def to_dotenv(self, fpath: str | pathlib.Path | os.PathLike[str]) -> None:
        """Export configuration to .env file with field descriptions as
        comments.

        Args:
            fpath: Path to the output .env file.
        """
        sep = self.model_config.get("env_nested_delimiter") or "__"
        prefix = self.model_config.get("env_prefix") or "AUDEX__"

        if prefix.endswith(sep):
            prefix = prefix[: -len(sep)]

        serializable_data = self.serl(include_none=True)
        descriptions = self._collect_field_desc()

        grouped_keys = {}
        for top_level_key in serializable_data:
            section_data = {top_level_key: serializable_data[top_level_key]}
            flattened = utils.flatten_dict(section_data, sep=sep)
            grouped_keys[top_level_key] = flattened

        with pathlib.Path(fpath).open("w", encoding="utf-8") as f:
            f.write(
                "# Description: Example environment configuration file for Audex application.\n"
            )
            f.write("# Note: Copy this file to '.env' and modify the values as needed.\n\n")
            for top_key, flattened in grouped_keys.items():
                f.write(f"# {'=' * 70}\n")

                top_key_desc = descriptions.get(top_key)
                if top_key_desc:
                    f.write(f"# {top_key.upper()}: {top_key_desc}\n")
                f.write(f"# {'=' * 70}\n")
                f.write("\n")

                for key, value in flattened.items():
                    env_key = f"{prefix}{sep}{key.upper()}"

                    field_path = key.replace(sep, ".")
                    if field_path in descriptions:
                        f.write(f"# {descriptions[field_path]}\n")

                    if value is None:
                        f.write(f"# {env_key}=\n")
                    else:
                        formatted_value = self._format_env_value(value)
                        f.write(f"{env_key}={formatted_value}\n")
                    f.write("\n")

    # ============================================================================
    # Private Methods - Field Introspection
    # ============================================================================

    def _collect_field_desc(
        self,
        model: type[BaseModel] | None = None,
        prefix: str = "",
    ) -> dict[str, str]:
        """Recursively collect field descriptions from the model and
        nested models.

        Args:
            model: The pydantic model to collect descriptions from.
            prefix: The prefix for nested field paths.

        Returns:
            A dictionary mapping field paths to their descriptions.
        """
        if model is None:
            model = self.__class__

        descriptions = {}
        for field_name, field_info in model.model_fields.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            if field_info.description:
                descriptions[field_path] = field_info.description

            if hasattr(field_info.annotation, "model_fields"):
                nested_descriptions = self._collect_field_desc(
                    field_info.annotation, prefix=field_path
                )
                descriptions.update(nested_descriptions)

        return descriptions

    # ============================================================================
    # Private Methods - Serialization
    # ============================================================================

    def _serl_value(self, value: t.Any, include_none: bool = False) -> t.Any:
        """Serialize a value, handling special cases like callables.

        Args:
            value: The value to serialize.
            include_none: If True, preserve None values in nested structures.

        Returns:
            Serialized value or None if not serializable.
        """
        if value is None:
            return value if include_none else None

        if isinstance(value, os.PathLike):
            try:
                return os.fspath(value)
            except Exception:
                return None

        if callable(value):
            try:
                return self._serl_value(value(), include_none=include_none)
            except Exception:
                return None

        if isinstance(value, PydBaseModel):
            return value.model_dump()

        serialized: list[t.Any] | dict[str, t.Any]

        if isinstance(value, (list, tuple)):
            serialized = []
            for item in value:
                serialized_item = self._serl_value(item, include_none=include_none)
                if include_none or serialized_item is not None:
                    serialized.append(serialized_item)
            return serialized if serialized or include_none else None

        if isinstance(value, dict):
            serialized = {}
            for k, v in value.items():
                serialized_v = self._serl_value(v, include_none=include_none)
                if include_none or serialized_v is not None:
                    serialized[k] = serialized_v
            return serialized if serialized or include_none else None

        if isinstance(value, (str, int, float, bool)):
            return value

        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return None

    def _clean_dict(self, data: dict[str, t.Any], include_none: bool = False) -> dict[str, t.Any]:
        """Recursively clean a dictionary to remove non-serializable
        values.

        Args:
            data: Dictionary to clean.
            include_none: If True, include fields with None values.

        Returns:
            Cleaned dictionary.
        """
        cleaned: dict[str, t.Any] = {}
        for key, value in data.items():
            if value is None:
                if include_none:
                    cleaned[key] = None
            else:
                serialized = self._serl_value(value, include_none=include_none)
                if serialized is not None or include_none:
                    cleaned[key] = serialized
        return cleaned

    # ============================================================================
    # Private Methods - System YAML Generation
    # ============================================================================

    def _build_platform_data(
        self,
        model: type[PydBaseModel],
        platform: str,
        prefix: str = "",
    ) -> dict[str, t.Any]:
        """Recursively build configuration data with platform-specific
        defaults.

        Args:
            model: Pydantic model to process.
            platform: Target platform.
            prefix: Field path prefix.

        Returns:
            Dictionary with platform-specific default values.
        """
        from audex.helper.settings.fields import AudexFieldInfo

        result = {}

        for field_name, field_info in model.model_fields.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            # Handle nested models
            if hasattr(field_info.annotation, "model_fields"):
                nested_data = self._build_platform_data(
                    field_info.annotation,  # type: ignore
                    platform,
                    field_path,
                )
                # Only add if nested model has content
                if nested_data:
                    result[field_name] = nested_data
                continue

            # Get value based on field type
            if isinstance(field_info, AudexFieldInfo):
                value = field_info.get_platform_default(platform)
            else:
                # Standard field - use current value or default
                current_value = getattr(self, field_name, PydanticUndefined)
                if current_value is not PydanticUndefined:
                    value = current_value
                elif field_info.default is not PydanticUndefined:
                    value = field_info.default
                elif field_info.default_factory is not None:
                    value = field_info.default_factory()
                else:
                    value = PydanticUndefined

            # Serialize the value (handle Pydantic models, lists, dicts, etc.)
            if value is not PydanticUndefined:
                serialized_value = self._serl_value(value, include_none=True)
                result[field_name] = serialized_value
            else:
                result[field_name] = value

        return result

    def _clean_unset_values(self, data: t.Any) -> t.Any:
        """Recursively remove Unset values, PydanticUndefined, and empty
        dictionaries.

        Args:
            data: Data structure to clean.

        Returns:
            Cleaned data structure, or None if all values were Unset.
        """
        # Check for Unset or PydanticUndefined
        if isinstance(data, utils.Unset) or data is PydanticUndefined:
            return None

        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Skip Unset and PydanticUndefined
                if isinstance(value, utils.Unset) or value is PydanticUndefined:
                    continue

                cleaned_value = self._clean_unset_values(value)

                # Skip None values from recursive cleaning
                if cleaned_value is None:
                    continue

                # Skip empty dicts (all fields were Unset)
                if isinstance(cleaned_value, dict) and not cleaned_value:
                    continue

                cleaned[key] = cleaned_value

            return cleaned if cleaned else None

        if isinstance(data, list):
            cleaned_list = []
            for item in data:
                if isinstance(item, utils.Unset) or item is PydanticUndefined:
                    continue

                cleaned_item = self._clean_unset_values(item)
                if cleaned_item is not None:
                    cleaned_list.append(cleaned_item)

            return cleaned_list if cleaned_list else None

        return data

    def _write_system_yaml_header(self, f: t.TextIO, platform: str) -> None:
        """Write system YAML file header.

        Args:
            f: File object.
            platform: Target platform.
        """
        import audex

        f.write("# Audex System Configuration\n")
        f.write(f"# Platform: {platform}\n")
        f.write(f"# Version: {audex.__version__}\n")
        f.write("#\n")
        f.write("# This file is generated automatically. Do not edit manually.\n")
        f.write("# User configuration should be placed in ~/.config/audex/config.yml\n")
        f.write("#\n")
        f.write("# For configuration examples, see: /etc/audex/config.example.yml\n")
        f.write("\n")

    def _write_yaml_dict(
        self,
        f: t.TextIO,
        obj: dict[str, t.Any],
        indent: int = 0,
    ) -> None:
        """Write a dictionary as YAML without comments.

        Args:
            f: File object.
            obj: Dictionary to write.
            indent: Indentation level.
        """
        for key, value in obj.items():
            self._write_yaml_value(f, key, value, indent)

    def _write_yaml_value(
        self,
        f: t.TextIO,
        key: str,
        value: t.Any,
        indent: int = 0,
    ) -> None:
        """Write a single YAML key-value pair without comments.

        Args:
            f: File object.
            key: Key name.
            value: Value to write.
            indent: Indentation level.
        """
        indent_str = "  " * indent

        if value is None:
            f.write(f"{indent_str}{key}: ~\n")
        elif isinstance(value, dict):
            f.write(f"{indent_str}{key}:\n")
            self._write_yaml_dict(f, value, indent + 1)
        elif isinstance(value, list):
            f.write(f"{indent_str}{key}:\n")
            self._write_yaml_list(f, value, indent + 1)
        elif isinstance(value, str) and ("\n" in value or len(value) > 80):
            f.write(f"{indent_str}{key}: |-\n")
            for line in value.split("\n"):
                f.write(f"{indent_str}  {line}\n")
        else:
            yaml_value = self._yaml_repr(value)
            f.write(f"{indent_str}{key}: {yaml_value}\n")

    def _write_yaml_list(
        self,
        f: t.TextIO,
        items: list[t.Any],
        indent: int = 0,
    ) -> None:
        """Write a list as YAML without comments.

        Args:
            f: File object.
            items: List items to write.
            indent: Indentation level.
        """
        indent_str = "  " * indent
        for item in items:
            if isinstance(item, dict):
                items_list = list(item.items())
                if items_list:
                    first_key, first_value = items_list[0]

                    if first_value is None:
                        f.write(f"{indent_str}- {first_key}: ~\n")
                    elif isinstance(first_value, dict):
                        f.write(f"{indent_str}- {first_key}:\n")
                        self._write_yaml_dict(f, first_value, indent + 1)
                    elif isinstance(first_value, list):
                        f.write(f"{indent_str}- {first_key}:\n")
                        self._write_yaml_list(f, first_value, indent + 1)
                    elif isinstance(first_value, str) and (
                        "\n" in first_value or len(first_value) > 80
                    ):
                        f.write(f"{indent_str}- {first_key}: |-\n")
                        for line in first_value.split("\n"):
                            f.write(f"{indent_str}    {line}\n")
                    else:
                        yaml_val = self._yaml_repr(first_value)
                        f.write(f"{indent_str}- {first_key}: {yaml_val}\n")

                    for sub_key, sub_value in items_list[1:]:
                        self._write_yaml_value(f, sub_key, sub_value, indent + 1)
            elif isinstance(item, list):
                f.write(f"{indent_str}-\n")
                self._write_yaml_list(f, item, indent + 1)
            else:
                yaml_item = self._yaml_repr(item)
                f.write(f"{indent_str}- {yaml_item}\n")

    # ============================================================================
    # Private Methods - YAML Formatting
    # ============================================================================

    def _yaml_repr(self, value: t.Any) -> str:
        """Convert a Python value to YAML representation string.

        Args:
            value: The value to convert.

        Returns:
            YAML string representation.
        """
        if value is None:
            return "~"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if (
                not value
                or value[0] in "-?  :,[]{}#&*!  |>'\"%@`"
                or value in ("true", "false", "null", "yes", "no", "on", "off")
                or ":" in value
                or "#" in value
            ):
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            return value
        return str(value)

    # ============================================================================
    # Private Methods - Dotenv Formatting
    # ============================================================================

    def _format_env_value(self, value: t.Any) -> str:
        """Format a value for .env file with proper quoting.

        Args:
            value: The value to format.

        Returns:
            Formatted string value.
        """
        if value is None:
            return ""

        if isinstance(value, os.PathLike):
            try:
                return os.fspath(value)
            except Exception:
                return ""

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            needs_quotes = (
                " " in value
                or "#" in value
                or "=" in value
                or "\n" in value
                or "\t" in value
                or "\r" in value
                or value.startswith(('"', "'"))
                or not value
            )

            if needs_quotes:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            return value

        if isinstance(value, (list, dict)):
            json_str = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            escaped = json_str.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        str_value = str(value)
        if " " in str_value or "#" in str_value:
            escaped = str_value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return str_value
