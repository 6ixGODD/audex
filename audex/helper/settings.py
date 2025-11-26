from __future__ import annotations

import json
import os
import pathlib
import typing as t

import pydantic as pyd
import pydantic_settings as ps

from audex import utils
from audex.exceptions import RequiredModuleNotFoundError


class Settings(ps.BaseSettings):
    @classmethod
    def from_yaml(cls, path: str | pathlib.Path | os.PathLike[str]) -> t.Self:
        try:
            import yaml

            data = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
            return cls.model_validate(data, strict=True)
        except ImportError as e:
            raise RequiredModuleNotFoundError(
                "`yaml` module is required to load configuration from YAML "
                "files. Please install it using `pip install pyyaml`."
            ) from e

    @classmethod
    def from_json(cls, fpath: str | pathlib.Path | os.PathLike[str]) -> t.Self:
        try:
            import json5

            data = json5.loads(pathlib.Path(fpath).read_text(encoding="utf-8"))
            return cls.model_validate(data, strict=True)
        except ImportError:
            import json

            try:
                data = json.loads(pathlib.Path(fpath).read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise RequiredModuleNotFoundError(
                    "If you need to load configuration from JSON5 files, please install the "
                    "`json5` module using `pip install json5`."
                ) from e
            return cls.model_validate(data, strict=True)

    def _collect_field_desc(
        self,
        model: type[pyd.BaseModel] | None = None,
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

            # Add description for current field
            if field_info.description:
                descriptions[field_path] = field_info.description

            # Recursively collect descriptions from nested models
            if hasattr(field_info.annotation, "model_fields"):
                nested_descriptions = self._collect_field_desc(
                    field_info.annotation, prefix=field_path
                )
                descriptions.update(nested_descriptions)

        return descriptions

    def _serl_value(self, value: t.Any, include_none: bool = False) -> t.Any:
        """Serialize a value, handling special cases like callables.

        Args:
            value: The value to serialize.
            include_none: If True, preserve None values in nested structures.

        Returns:
            Serialized value or None if not serializable.
        """
        # Handle None - return as-is if we want to include it
        if value is None:
            return value if include_none else None

        # Execute callables
        if callable(value):
            try:
                return self._serl_value(value(), include_none=include_none)
            except Exception:
                return None

        # Handle Pydantic models
        if isinstance(value, pyd.BaseModel):
            return value.model_dump()

        serialized: list[t.Any] | dict[str, t.Any]
        # Handle lists and tuples
        if isinstance(value, (list | tuple)):
            serialized = []
            for item in value:
                serialized_item = self._serl_value(item, include_none=include_none)
                if include_none or serialized_item is not None:
                    serialized.append(serialized_item)
            return serialized if serialized or include_none else None

        # Handle dictionaries
        if isinstance(value, dict):
            serialized = {}
            for k, v in value.items():
                serialized_v = self._serl_value(v, include_none=include_none)
                if include_none or serialized_v is not None:
                    serialized[k] = serialized_v
            return serialized if serialized or include_none else None

        # Return primitive types as-is
        if isinstance(value, (str | int | float | bool)):
            return value

        # Try to serialize other types, return None if failed
        try:
            import json

            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return None

    def serl(self, include_none: bool = False) -> dict[str, t.Any]:
        """Get a serializable version of the model dump.

        Args:
            include_none: If True, include fields with None values.

        Returns:
            Dictionary with only serializable values.
        """
        raw_dump = self.model_dump()
        return self._clean_dict(raw_dump, include_none=include_none)

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

    def _yaml_repr(self, value: t.Any) -> str:
        """Convert a Python value to YAML representation string.

        Args:
            value: The value to convert.

        Returns:
            YAML string representation.
        """
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int | float)):
            return str(value)
        if isinstance(value, str):
            # Check if string needs quoting
            if (
                not value
                or value[0] in "-?:,[]{}#&*!|>'\"%@`"
                or value in ("true", "false", "null", "yes", "no", "on", "off")
                or ":" in value
                or "#" in value
            ):
                # Escape and quote
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            return value
        return str(value)

    def to_yaml(self, fpath: str | pathlib.Path | os.PathLike[str]) -> None:
        """Export configuration to YAML file with field descriptions as
        comments.

        Args:
            fpath: Path to the output YAML file.
        """
        descriptions = self._collect_field_desc()
        data = self.serl(include_none=True)

        def add_comments(obj: t.Any, prefix: str = "", indent: int = 0) -> list[str]:
            """Recursively add comments to YAML structure."""
            lines = []
            indent_str = "  " * indent

            if isinstance(obj, dict):
                for key, value in obj.items():
                    field_path = f"{prefix}.{key}" if prefix else key

                    # Get description if available
                    desc = descriptions.get(field_path, "")
                    comment = f" # {desc}" if desc else ""

                    # Handle None values - use ~ to represent None
                    if value is None:
                        lines.append(f"{indent_str}{key}: ~{comment}")
                    elif isinstance(value, dict):
                        lines.append(f"{indent_str}{key}:{comment}")
                        nested = add_comments(value, prefix=field_path, indent=indent + 1)
                        lines.extend(nested)
                    elif isinstance(value, list):
                        lines.append(f"{indent_str}{key}:{comment}")
                        for item in value:
                            if isinstance(item, dict):
                                # Get first key-value pair for inline format
                                items_list = list(item.items())
                                if items_list:
                                    first_key, first_value = items_list[0]
                                    first_field_path = f"{field_path}.{first_key}"
                                    first_desc = descriptions.get(first_field_path, "")
                                    first_comment = f"  # {first_desc}" if first_desc else ""

                                    if first_value is None:
                                        lines.append(
                                            f"{indent_str}  - {first_key}: ~{first_comment}"
                                        )
                                    elif isinstance(first_value, str) and (
                                        "\n" in first_value or len(first_value) > 80
                                    ):
                                        lines.append(
                                            f"{indent_str}  - {first_key}: |-{first_comment}"
                                        )
                                        for line in first_value.split("\n"):
                                            lines.append(f"{indent_str}      {line}")
                                    else:
                                        yaml_val = self._yaml_repr(first_value)
                                        lines.append(
                                            f"{indent_str}  - {first_key}: {yaml_val}{first_comment}"
                                        )

                                    # Add remaining key-value pairs
                                    for sub_key, sub_value in items_list[1:]:
                                        sub_field_path = f"{field_path}.{sub_key}"
                                        sub_desc = descriptions.get(sub_field_path, "")
                                        sub_comment = f"  # {sub_desc}" if sub_desc else ""

                                        if sub_value is None:
                                            lines.append(
                                                f"{indent_str}    {sub_key}: ~{sub_comment}"
                                            )
                                        elif isinstance(sub_value, str) and (
                                            "\n" in sub_value or len(sub_value) > 80
                                        ):
                                            lines.append(
                                                f"{indent_str}    {sub_key}: |-{sub_comment}"
                                            )
                                            for line in sub_value.split("\n"):
                                                lines.append(f"{indent_str}      {line}")
                                        else:
                                            yaml_val = self._yaml_repr(sub_value)
                                            lines.append(
                                                f"{indent_str}    {sub_key}: {yaml_val}{sub_comment}"
                                            )
                            else:
                                yaml_item = self._yaml_repr(item)
                                lines.append(f"{indent_str}  - {yaml_item}")
                    # Handle multiline strings
                    elif isinstance(value, str) and ("\n" in value or len(value) > 80):
                        lines.append(f"{indent_str}{key}: |-{comment}")
                        for line in value.split("\n"):
                            lines.append(f"{indent_str}  {line}")
                    else:
                        yaml_value = self._yaml_repr(value)
                        lines.append(f"{indent_str}{key}: {yaml_value}{comment}")

            return lines

        with pathlib.Path(fpath).open("w", encoding="utf-8") as f:
            lines = add_comments(data)
            f.write("\n".join(lines))
            f.write("\n")

    def to_json(self, fpath: str | pathlib.Path | os.PathLike[str], jsonc: bool = True) -> None:
        """Export configuration to JSON or JSONC file.

        Args:
            fpath: Path to the output JSON/JSONC file.
            jsonc: If True, export as JSONC with comments. If False,
                export as plain JSON.
        """
        import json

        descriptions = self._collect_field_desc()
        data = self.serl(include_none=True)

        # Adjust file extension based on with_comments
        fpath_str = str(fpath)
        if jsonc and not fpath_str.endswith(".jsonc"):
            # Change extension to .jsonc if comments are enabled
            base = pathlib.Path(fpath_str).stem
            path = f"{base}.jsonc"
        elif not jsonc and fpath_str.endswith(".jsonc"):
            # Change extension to .json if comments are disabled
            base = pathlib.Path(fpath_str).stem
            path = f"{base}.json"
        else:
            path = fpath_str

        if jsonc:

            def add_json_comments(obj: t.Any, prefix: str = "", indent: int = 0) -> str:
                """Recursively add comments to JSON structure."""
                lines = []
                indent_str = "  " * indent

                if isinstance(obj, dict):
                    lines.append("{")
                    items = list(obj.items())
                    for i, (key, value) in enumerate(items):
                        field_path = f"{prefix}.{key}" if prefix else key

                        # Add description comment if available
                        if field_path in descriptions:
                            lines.append(f"{indent_str}  // {descriptions[field_path]}")

                        # Handle None values - comment out the line
                        if value is None:
                            lines.append(f'{indent_str}  // "{key}": null')
                        elif isinstance(value, dict):
                            lines.append(
                                f'{indent_str}  "{key}": '
                                + add_json_comments(value, prefix=field_path, indent=indent + 1)
                            )
                        elif isinstance(value, (list | tuple)):
                            json_value = json.dumps(value, indent=2, ensure_ascii=False)
                            indented_value = json_value.replace("\n", "\n" + indent_str + "  ")
                            lines.append(f'{indent_str}  "{key}": {indented_value}')
                        else:
                            json_value = json.dumps(value, ensure_ascii=False)
                            lines.append(f'{indent_str}  "{key}": {json_value}')

                        # Add comma if not last item and current line is not commented
                        if i < len(items) - 1 and value is not None:
                            lines[-1] += ","

                    lines.append(f"{indent_str}}}")
                    return "\n".join(lines)
                return json.dumps(obj, indent=2, ensure_ascii=False)

            with pathlib.Path(path).open("w", encoding="utf-8") as f:
                f.write(add_json_comments(data))
                f.write("\n")
        else:
            # Plain JSON without comments - remove None values for valid JSON
            data_without_none = self.serl(include_none=False)
            with pathlib.Path(path).open("w", encoding="utf-8") as f:
                json.dump(data_without_none, f, indent=2, ensure_ascii=False)
                f.write("\n")

    def _format_env_value(self, value: t.Any) -> str:
        """Format a value for .env file with proper quoting.

        Args:
            value: The value to format.

        Returns:
            Formatted string value.
        """
        import json

        # Handle None
        if value is None:
            return ""

        # Handle boolean
        if isinstance(value, bool):
            return "true" if value else "false"

        # Handle numbers
        if isinstance(value, (int | float)):
            return str(value)

        # Handle strings
        if isinstance(value, str):
            # Check if the string needs quoting
            needs_quotes = (
                " " in value  # Contains spaces
                or "#" in value  # Contains comment character
                or "=" in value  # Contains equals sign
                or "\n" in value  # Contains newline
                or "\t" in value  # Contains tab
                or "\r" in value  # Contains carriage return
                or value.startswith('"')
                or value.startswith("'")  # Starts with quote
                or not value  # Empty string
            )

            if needs_quotes:
                # Escape existing double quotes and backslashes
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            return value

        # Handle lists and dicts as JSON
        if isinstance(value, (list | dict)):
            json_str = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            # Always quote JSON strings
            escaped = json_str.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        # Default: convert to string and quote if necessary
        str_value = str(value)
        if " " in str_value or "#" in str_value:
            escaped = str_value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return str_value

    def to_dotenv(self, fpath: str | pathlib.Path | os.PathLike[str]) -> None:
        """Export configuration to .env file with field descriptions as
        comments.

        Args:
            fpath: Path to the output .env file.
        """
        sep = self.model_config.get("env_nested_delimiter") or "__"
        prefix = self.model_config.get("env_prefix") or "PROTOTYPEX__"

        # Remove trailing separator from prefix if present
        if prefix.endswith(sep):
            prefix = prefix[: -len(sep)]

        # Get serializable dump with None values included
        serializable_data = self.serl(include_none=True)

        # Collect field descriptions
        descriptions = self._collect_field_desc()

        # Group flattened keys by top-level keys
        grouped_keys = {}
        for top_level_key in serializable_data:
            # Flatten each top-level section
            section_data = {top_level_key: serializable_data[top_level_key]}
            flattened = utils.flatten_dict(section_data, sep=sep)
            grouped_keys[top_level_key] = flattened

        with pathlib.Path(fpath).open("w", encoding="utf-8") as f:
            for top_key, flattened in grouped_keys.items():
                # Add separator between top-level sections
                f.write(f"# {'=' * 70}\n")

                # Add top-level section comment
                top_key_desc = descriptions.get(top_key)
                if top_key_desc:
                    f.write(f"# {top_key.upper()}: {top_key_desc}\n")
                f.write(f"# {'=' * 70}\n")
                f.write("\n")

                for key, value in flattened.items():
                    # Convert key to uppercase for environment variable
                    env_key = f"{prefix}{sep}{key.upper()}"

                    # Add description comment if available
                    field_path = key.replace(sep, ".")
                    if field_path in descriptions:
                        f.write(f"# {descriptions[field_path]}\n")

                    # Handle None values - comment out the line and leave empty
                    if value is None:
                        f.write(f"# {env_key}=\n")
                    else:
                        # Format and write the environment variable
                        formatted_value = self._format_env_value(value)
                        f.write(f"{env_key}={formatted_value}\n")
                    f.write("\n")


class BaseModel(pyd.BaseModel):
    """Base model class with common configuration for all models.

    This class sets default configurations for Pydantic models used in
    the PrototypeX project, ensuring consistent behavior across all
    derived models.
    """

    model_config: t.ClassVar[pyd.ConfigDict] = pyd.ConfigDict(
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
