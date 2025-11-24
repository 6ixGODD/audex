from __future__ import annotations

import argparse
import collections
import importlib
import inspect
import pathlib
import sys
import traceback
import types
import typing as t

from audex.entity import BaseEntity
from audex.entity import FieldSpec
from audex.entity.fields import ListFieldSpec
from audex.entity.fields import StringBackedFieldSpec
from audex.entity.fields import StringFieldSpec
from scripts.tools import common

# Add project root to path
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class EntityInfo(t.NamedTuple):
    """Information about a discovered entity."""

    name: str
    class_obj: type[BaseEntity]
    module_path: str
    file_path: pathlib.Path


def find_entity_classes(entities_dir: pathlib.Path) -> dict[pathlib.Path, list[EntityInfo]]:
    """Find all BaseEntity subclasses in the entities directory, grouped
    by file.

    Args:
        entities_dir: Path to the entities package directory.

    Returns:
        Dictionary mapping file paths to lists of EntityInfo objects.
    """
    entities_by_file: dict[pathlib.Path, list[EntityInfo]] = collections.defaultdict(list)

    # Find all Python files
    for py_file in entities_dir.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        # Calculate module path
        relative_path = py_file.relative_to(entities_dir.parent.parent)
        module_parts = [*relative_path.parts[:-1], relative_path.stem]
        module_path = ".".join(module_parts)

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Find BaseEntity subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    obj is not BaseEntity
                    and issubclass(obj, BaseEntity)
                    and obj.__module__ == module_path
                ):
                    entity_info = EntityInfo(
                        name=name,
                        class_obj=obj,
                        module_path=module_path,
                        file_path=py_file,
                    )
                    entities_by_file[py_file].append(entity_info)

        except Exception as e:
            common.log_warn(f"Failed to import {module_path}: {e}")
            continue

    return dict(entities_by_file)


def camel_to_snake(name: str) -> str:
    """Convert CamelCase or PascalCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def get_field_filter_type(field: FieldSpec[t.Any]) -> str:
    """Determine the appropriate FieldFilter type for a field."""
    if isinstance(field, StringFieldSpec):
        return "StringFieldFilter"
    if isinstance(field, StringBackedFieldSpec):
        return "StringBackedFieldFilter"
    if isinstance(field, ListFieldSpec):
        return "ListFieldFilter"
    return "FieldFilter"


def resolve_type_alias(type_hint: t.Any) -> t.Any:
    """Resolve TypeAlias to its actual type."""
    # If it's already a resolved type (like Union), return it
    if t.get_origin(type_hint) is not None:
        return type_hint

    # Try to get the actual type from the class's module
    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        try:
            module = importlib.import_module(type_hint.__module__)
            actual_type = getattr(module, type_hint.__name__, None)

            # Check if it's a TypeAlias
            if actual_type is not None:
                # For Python 3.10+ TypeAlias, try to get the actual type
                if hasattr(actual_type, "__value__"):
                    return actual_type.__value__
                # For older style type aliases, the value might be stored differently
                if (
                    hasattr(actual_type, "__args__")
                    or str(actual_type).startswith("typing.Union")
                    or "|" in str(actual_type)
                ):
                    return actual_type
        except Exception:
            pass

    return type_hint


def extract_imports_from_type(type_hint: t.Any, collected_imports: set[str]) -> None:
    """Recursively extract imports from a type hint."""
    # Handle None type
    if type_hint is type(None):
        return

    # Handle Union types
    origin = t.get_origin(type_hint)
    args = t.get_args(type_hint)

    if origin is types.UnionType:
        for arg in args:
            extract_imports_from_type(arg, collected_imports)
        return

    # Handle List, Sequence, etc.
    if origin is not None:
        if origin in (list, list, t.Sequence, t.Union):
            for arg in args:
                extract_imports_from_type(arg, collected_imports)
            return
        # Handle other generic types
        extract_imports_from_type(origin, collected_imports)
        for arg in args:
            extract_imports_from_type(arg, collected_imports)
        return

    # Handle custom types with modules
    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        module = type_hint.__module__
        type_name = type_hint.__name__

        # Skip built-ins and typing
        if module in ("builtins", "typing"):
            return

        # Handle audex types
        if module.startswith("audex."):
            collected_imports.add(f"from {module} import {type_name}")
            return

        # Handle datetime module specifically
        if module == "datetime":
            collected_imports.add("import datetime")
            return

        # Other modules
        if module != "__main__":
            collected_imports.add(f"from {module} import {type_name}")


def format_type_annotation(type_hint: t.Any) -> str:
    """Format a type annotation to a proper string representation."""
    import datetime as dt

    # Handle None type
    if type_hint is type(None):
        return "None"

    # Handle Union types (including Optional)
    origin = t.get_origin(type_hint)
    args = t.get_args(type_hint)

    if origin is t.Union:
        # Handle Optional[T] (Union[T, None])
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            formatted_type = format_type_annotation(non_none_type)
            return f"{formatted_type} | None"
        # Handle general Union types
        formatted_args = []
        for arg in args:
            formatted_arg = format_type_annotation(arg)
            formatted_args.append(formatted_arg)
        return " | ".join(formatted_args)

    # Handle List, Sequence, etc.
    if origin is not None:
        if origin in (list, list):
            if args:
                inner_type = format_type_annotation(args[0])
                return f"list[{inner_type}]"
            return "list[t.Any]"
        if origin in (t.Sequence,):
            if args:
                inner_type = format_type_annotation(args[0])
                return f"t.Sequence[{inner_type}]"
            return "t.Sequence[t.Any]"

    # Handle built-in types
    if type_hint in (int, str, float, bool):
        return type_hint.__name__

    # Handle datetime types
    if type_hint is dt.datetime:
        return "datetime.datetime"
    if type_hint is dt.date:
        return "datetime.date"
    if type_hint is dt.time:
        return "datetime.time"

    # Handle custom types with modules
    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        module = type_hint.__module__
        type_name = type_hint.__name__

        # Skip built-ins and typing
        if module in ("builtins", "typing"):
            return type_name

        # Handle audex types - just return the class name since we import them
        if module.startswith("audex."):
            return type_name

        # Handle datetime module specifically
        if module == "datetime":
            return f"datetime.{type_name}"

        # Other modules
        if module != "__main__":
            return type_name

        return type_name

    # Handle TypeAlias and other string-based representations
    hint_str = str(type_hint)

    # Handle common patterns
    if hint_str.startswith("<class '") and hint_str.endswith("'>"):
        return hint_str[8:-2]

    if hint_str.startswith("<enum '") and hint_str.endswith("'>"):
        return hint_str[7:-2]

    # Handle Union patterns in string form
    if "typing.Union[" in hint_str:
        # Extract the Union content and reformat
        import re

        match = re.search(r"typing\.Union\[(.*)]", hint_str)
        if match:
            union_content = match.group(1)
            # Split by comma but respect nested brackets
            parts = []
            current_part = ""
            bracket_depth = 0
            for char in union_content:
                if char == "[":
                    bracket_depth += 1
                elif char == "]":
                    bracket_depth -= 1
                elif char == "," and bracket_depth == 0:
                    parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char
            if current_part.strip():
                parts.append(current_part.strip())

            # Clean up each part
            cleaned_parts = []
            for part in parts:
                part = part.strip()
                # Remove module prefixes for audex types
                if part.startswith("audex."):
                    part = part.split(".")[-1]
                # Handle <class 'Name'> patterns
                if part.startswith("<class '") and part.endswith("'>"):
                    part = part[8:-2]
                cleaned_parts.append(part)

            return " | ".join(cleaned_parts)

    # Clean up typing module references
    hint_str = hint_str.replace("typing.", "t.")

    # Handle audex module references - extract just the class name
    if "audex." in hint_str:
        import re

        # Replace audex.module.ClassName with just ClassName
        hint_str = re.sub(r"audex\.[a-zA-Z0-9_.]+\.([a-zA-Z0-9_]+)", r"\1", hint_str)

    return hint_str


def get_field_type_annotation(
    field_name: str, entity_class: type[BaseEntity], field_spec: FieldSpec[t.Any]
) -> str:
    """Get the type annotation string for a field."""
    try:
        # For ListField, we need special handling
        if isinstance(field_spec, ListFieldSpec):
            # First try to get from type hints
            hints = t.get_type_hints(entity_class)
            if field_name in hints:
                hint = hints[field_name]
                # Resolve TypeAlias if needed
                resolved_hint = resolve_type_alias(hint)
                return format_type_annotation(resolved_hint)

            # Fallback: construct from _field_type
            if hasattr(field_spec, "_field_type") and field_spec._field_type:
                resolved_item_type = resolve_type_alias(field_spec._field_type)
                item_type = format_type_annotation(resolved_item_type)
                return f"list[{item_type}]"

            return "list[t.Any]"

        # For other fields, try type hints first
        hints = t.get_type_hints(entity_class)
        if field_name in hints:
            hint = hints[field_name]
            # Resolve TypeAlias if needed
            resolved_hint = resolve_type_alias(hint)
            return format_type_annotation(resolved_hint)

        # Fallback: try to get from field's _field_type if available
        if hasattr(field_spec, "_field_type") and field_spec._field_type:
            resolved_type = resolve_type_alias(field_spec._field_type)
            return format_type_annotation(resolved_type)

    except Exception as e:
        common.log_warn(f"Failed to get type annotation for {field_name}: {e}")

    return "t.Any"


def extract_type_imports(entity_classes: list[type[BaseEntity]]) -> set[str]:
    """Extract type-related imports needed for the filters."""
    imports: set[str] = set()

    for entity_class in entity_classes:
        try:
            for field_name, field_spec in entity_class._fields.items():
                # Get type annotation for the field and extract imports
                try:
                    # For ListField, we need special handling
                    if isinstance(field_spec, ListFieldSpec):
                        # First try to get from type hints
                        hints = t.get_type_hints(entity_class)
                        if field_name in hints:
                            hint = hints[field_name]
                            resolved_hint = resolve_type_alias(hint)
                            extract_imports_from_type(resolved_hint, imports)
                        elif hasattr(field_spec, "_field_type") and field_spec._field_type:
                            # For ListField, we need to extract from the item type
                            resolved_item_type = resolve_type_alias(field_spec._field_type)
                            extract_imports_from_type(resolved_item_type, imports)
                    else:
                        # For other fields
                        hints = t.get_type_hints(entity_class)
                        if field_name in hints:
                            hint = hints[field_name]
                            resolved_hint = resolve_type_alias(hint)
                            extract_imports_from_type(resolved_hint, imports)
                        elif hasattr(field_spec, "_field_type") and field_spec._field_type:
                            resolved_type = resolve_type_alias(field_spec._field_type)
                            extract_imports_from_type(resolved_type, imports)
                except Exception as e:
                    common.log_warn(f"Failed to extract imports for field {field_name}: {e}")
        except Exception as e:
            common.log_warn(f"Failed to extract type imports for {entity_class.__name__}: {e}")

    return imports


def iter_entity_fields_fallback(cls):
    """Yield Field instances from cls and its bases.

    Subclass definitions take precedence (i.e. override wins). Avoids
    duplicate yields when a field name is overridden in subclass.
    """
    seen: set[str] = set()
    # iterate cls first so subclass-defined fields are chosen before base ones
    for base in cls.__mro__:
        for name, attr in base.__dict__.items():
            if name in seen:
                continue
            if isinstance(attr, FieldSpec):
                seen.add(name)
                yield name, attr


def iter_entity_fields(cls):
    """Yield (name, Field) for cls using the metaclass-collected
    _fields.

    This respects overrides: if a subclass defines the same field name,
    that definition takes precedence.
    """
    fields = getattr(cls, "_fields", None)
    if fields is None:
        # Fallback to MRO scan if metaclass didn't populate _fields
        yield from iter_entity_fields_fallback(cls)
        return

    yield from fields.items()


def generate_entity_filter_code(entity_info: EntityInfo) -> tuple[list[str], set[str]]:
    """Generate the filter builder code for a single entity.

    Returns:
        Tuple of (code_lines, used_filter_types)
    """
    entity_name = entity_info.name
    filter_name = f"{entity_name}FilterBuilder"
    entity_class = entity_info.class_obj
    used_filter_types: set[str] = {"FilterBuilder", "Filter", "FieldFilter"}

    lines = [
        f"class {filter_name}(FilterBuilder[{entity_name}]):",
        f'    """{entity_name} filter builder with full type hints and IDE support.',
        "",
        "    This class is auto-generated. Do not edit manually.",
        '    """',
        "",
    ]

    # Generate wrapper classes for each field
    for field_name, field in iter_entity_fields(entity_class):
        filter_type = get_field_filter_type(field)
        type_annotation = get_field_type_annotation(field_name, entity_class, field)

        class_name = f"_{''.join(word.capitalize() for word in field_name.split('_'))}Field"

        # Determine base class and track used filter types
        if filter_type == "StringFieldFilter":
            base_class = "StringFieldFilter"
            used_filter_types.add("StringFieldFilter")
        elif filter_type == "StringBackedFieldFilter":
            base_class = f"StringBackedFieldFilter[{type_annotation}]"
            used_filter_types.add("StringBackedFieldFilter")
        elif filter_type == "ListFieldFilter":
            base_class = f"ListFieldFilter[{type_annotation}]"
            used_filter_types.add("ListFieldFilter")
        else:
            base_class = f"FieldFilter[{type_annotation}]"
            used_filter_types.add("FieldFilter")

        lines.extend([
            f"    class {class_name}({base_class}):",
            f'        """Chainable {field_name} filter with type-safe operations."""',
            "",
            f"        def __init__(self, builder: {filter_name}) -> None:",
            f'            super().__init__("{field_name}", object.__getattribute__(builder, "_filter"))',
            "            self._parent_builder = builder",
            "",
        ])

        # Base methods for all field types
        method_defs = [
            ("eq", [f"value: {type_annotation}"], "super().eq(value)"),
            ("ne", [f"value: {type_annotation}"], "super().ne(value)"),
            ("gt", [f"value: {type_annotation}"], "super().gt(value)"),
            ("lt", [f"value: {type_annotation}"], "super().lt(value)"),
            ("gte", [f"value: {type_annotation}"], "super().gte(value)"),
            ("lte", [f"value: {type_annotation}"], "super().lte(value)"),
            ("in_", [f"values: t.Sequence[{type_annotation}]"], "super().in_(values)"),
            ("nin", [f"values: t.Sequence[{type_annotation}]"], "super().nin(values)"),
            (
                "between",
                [f"value1: {type_annotation}", f"value2: {type_annotation}"],
                "super().between(value1, value2)",
            ),
            ("is_null", [], "super().is_null()"),
            ("is_not_null", [], "super().is_not_null()"),
            ("asc", [], "super().asc()"),
            ("desc", [], "super().desc()"),
        ]

        # Add string-specific methods for StringField and StringBackedField
        if filter_type in ("StringFieldFilter", "StringBackedFieldFilter"):
            method_defs.extend([
                ("contains", ["value: str"], "super().contains(value)"),
                ("startswith", ["value: str"], "super().startswith(value)"),
                ("endswith", ["value: str"], "super().endswith(value)"),
            ])

        # Add has method for ListField with proper type
        if filter_type == "ListFieldFilter":
            # Extract inner type from list annotation
            inner_type = type_annotation
            if inner_type.startswith("list[") and inner_type.endswith("]"):
                inner_type = inner_type[5:-1]
            elif inner_type.startswith("t.List[") and inner_type.endswith("]"):
                inner_type = inner_type[7:-1]
            method_defs.append(("has", [f"value: {inner_type}"], "super().has(value)"))
            method_defs.append((
                "contains",
                [f"value: list[{inner_type}]"],
                "super().contains(value)",
            ))

        for method_name, params, super_call in method_defs:
            params_str = ", ".join(params) if params else ""
            lines.extend([
                f"        def {method_name}(self{', ' + params_str if params_str else ''}) -> {filter_name}:",
                f"            {super_call}",
                "            return self._parent_builder",
                "",
            ])

    # Add and_() method support at the builder level
    lines.extend([
        "    def and_(self, *filters: Filter) -> Filter:",
        '        """Combine with other filters using AND logic.',
        "",
        "        Args:",
        "            *filters: Other filters to combine with AND.",
        "",
        "        Returns:",
        "            Combined filter with AND logic.",
        "",
        "        Example:",
        "            ```python",
        "            # username = 'john' AND email = 'john@ex.com'",
        "            filter = (",
        f"                {camel_to_snake(entity_name)}_filter()",
        "                .username.eq('john')",
        f"                .and_({camel_to_snake(entity_name)}_filter().email.eq('john@ex.com'))",
        "            )",
        "            ```",
        '        """',
        "        return object.__getattribute__(self, '_filter').and_(*filters)",
        "",
    ])

    # Add or_() method support at the builder level
    lines.extend([
        "    def or_(self, *filters: Filter) -> Filter:",
        '        """Combine with other filters using OR logic.',
        "",
        "        Args:",
        "            *filters: Other filters to combine with OR.",
        "",
        "        Returns:",
        "            Combined filter with OR logic.",
        "",
        "        Example:",
        "            ```python",
        "            # username = 'john' OR email = 'john@ex.com'",
        "            filter = (",
        f"                {camel_to_snake(entity_name)}_filter()",
        "                .username.eq('john')",
        f"                .or_({camel_to_snake(entity_name)}_filter().email.eq('john@ex.com'))",
        "            )",
        "            ```",
        '        """',
        "        return object.__getattribute__(self, '_filter').or_(*filters)",
        "",
    ])

    # Add not_() method support at the builder level
    lines.extend([
        "    def not_(self) -> Filter:",
        '        """Negate the current filter.',
        "",
        "        Returns:",
        "            Negated filter.",
        "",
        "        Example:",
        "            ```python",
        "            # NOT (username = 'john')",
        "            filter = (",
        f"                {camel_to_snake(entity_name)}_filter()",
        "                .username.eq('john')",
        "                .not_()",
        "            )",
        "            ```",
        '        """',
        "        return object.__getattribute__(self, '_filter').not_()",
        "",
    ])

    # Generate properties
    lines.extend(["    # Field properties", ""])

    for field_name, _field in entity_class._fields.items():
        class_name = f"_{''.join(word.capitalize() for word in field_name.split('_'))}Field"

        lines.extend([
            "    @property",
            f"    def {field_name}(self) -> {class_name}:",
            f'        """Filter by {field_name} field."""',
            f"        return self.{class_name}(self)",
            "",
        ])

    # Generate factory function
    lines.extend([
        "",
        f"def {camel_to_snake(entity_name)}_filter() -> {filter_name}:",
        f'    """Create a {entity_name} filter builder with full type safety.',
        "",
        "    Returns:",
        f"        A {filter_name} instance with full IDE support and chainable fields.",
        "",
        "    Example:",
        "        ```python",
        "        # AND conditions (chained)",
        "        filter = (",
        f"            {camel_to_snake(entity_name)}_filter()",
        "            .field1.eq(value1)",
        "            .field2.contains(value2)",
        "        )",
        "",
        "        # OR conditions",
        "        filter = (",
        f"            {camel_to_snake(entity_name)}_filter().field1.eq(value1)",
        f"            | {camel_to_snake(entity_name)}_filter().field2.eq(value2)",
        "        )",
        "        ```",
        '    """',
        f"    return {filter_name}({entity_name})",
        "",
    ])

    return lines, used_filter_types


def generate_filter_file_code(entity_infos: list[EntityInfo]) -> str:
    """Generate the filter builder code for all entities in a file.

    Args:
        entity_infos: List of entity information from the same source file.

    Returns:
        Generated Python code as a string.
    """
    if not entity_infos:
        return ""

    # Get the module path from the first entity (all should be the same)
    module_path = entity_infos[0].module_path

    # Extract type-related imports and used filter types
    entity_classes = [info.class_obj for info in entity_infos]
    type_imports = extract_type_imports(entity_classes)

    # Track which filter types are actually used
    all_used_filter_types: set[str] = set()
    all_entity_lines: list[str] = []

    # Generate code for each entity and collect used filter types
    for entity_info in sorted(entity_infos, key=lambda e: e.name):
        entity_lines, used_filter_types = generate_entity_filter_code(entity_info)
        all_entity_lines.extend(entity_lines)
        all_used_filter_types.update(used_filter_types)

    # Build imports section
    imports = [
        "# This file is auto-generated by PrototypeX filter generator.",
        "# Do not edit manually - changes will be overwritten.",
        "# Regenerate using: python -m scripts.gen_filters gen",
        "",
        "from __future__ import annotations",
        "",
        "import typing as t",
    ]

    # Add datetime import if needed
    if any("import datetime" in imp for imp in type_imports):
        imports.append("import datetime")
        # Remove the datetime import from type_imports to avoid duplication
        type_imports = {imp for imp in type_imports if imp != "import datetime"}

    imports.append("")

    # Import all entities from the module
    entity_names = [info.name for info in entity_infos]
    imports.append(f"from {module_path} import {', '.join(sorted(entity_names))}")

    # Only import the filter types that are actually used
    filter_imports = []
    for filter_type in sorted(all_used_filter_types):
        filter_imports.append(f"from audex.filters import {filter_type}")

    imports.extend(filter_imports)

    # Add type imports (excluding datetime since we handled it above)
    if type_imports:
        imports.append("")
        imports.extend(sorted(type_imports))

    imports.extend(["", "", ""])

    return "\n".join(imports) + "\n".join(all_entity_lines)


def generate_init_file(entities_by_file: dict[pathlib.Path, list[EntityInfo]]) -> str:
    """Generate __init__.py for the generated filters package.

    Args:
        entities_by_file: Dictionary mapping file paths to entity information.

    Returns:
        Generated __init__.py content.
    """
    lines = [
        "# This file is auto-generated by PrototypeX filter generator.",
        "# Do not edit manually - changes will be overwritten.",
        "# Regenerate using: python -m scripts.gen_filters gen",
        "",
        '"""Auto-generated filter builders.',
        "",
        "This package contains type-safe filter builders for all entities.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]

    # Collect all imports
    imports = []
    for file_path, entity_infos in sorted(entities_by_file.items(), key=lambda x: x[0].name):
        module_name = file_path.stem  # e.g., "api_service"

        for entity_info in sorted(entity_infos, key=lambda e: e.name):
            entity_name = entity_info.name
            filter_name = f"{entity_name}FilterBuilder"
            factory_name = f"{camel_to_snake(entity_name)}_filter"

            imports.append(
                f"from audex.filters.generated.{module_name} import {factory_name} as {factory_name}"
            )
            imports.append(
                f"from audex.filters.generated.{module_name} import {filter_name} as {filter_name}"
            )

    lines.extend(sorted(imports))
    lines.append("")

    return "\n".join(lines)


def generate_filters(
    entities_dir: pathlib.Path,
    output_dir: pathlib.Path,
    force: bool = False,
) -> tuple[int, int]:
    """Generate filter builders for all entities.

    Args:
        entities_dir: Directory containing entity files.
        output_dir: Directory to write generated files.
        force: Whether to overwrite existing files without prompting.

    Returns:
        Tuple of (generated_count, skipped_count).
    """
    # Find all entities grouped by file
    common.log_step("Scanning for entity classes...")
    entities_by_file = find_entity_classes(entities_dir)

    if not entities_by_file:
        common.log_warn("No entity classes found")
        return 0, 0

    total_entities = sum(len(entities) for entities in entities_by_file.values())
    common.log_success(
        f"Found {total_entities} entity class(es) in {len(entities_by_file)} file(s)"
    )
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    skipped_count = 0

    # Generate filters for each source file
    for source_file, entity_infos in sorted(entities_by_file.items(), key=lambda x: x[0].name):
        output_file = output_dir / source_file.name
        entity_names = ", ".join(info.name for info in entity_infos)

        common.log_step(
            f"Generating filters for {common.format_bold(source_file.name)}: "
            f"{common.format_dim(entity_names)}..."
        )

        # Check if file exists
        if output_file.exists() and not common.check_file_exists(output_file, force):
            skipped_count += 1
            print()
            continue

        try:
            # Generate code
            code = generate_filter_file_code(entity_infos)

            # Write file
            output_file.write_text(code, encoding="utf-8")

            common.log_success(f"Generated: {common.format_path(output_file)}")
            generated_count += 1

        except Exception as e:
            common.log_error(f"Failed to generate filter for {source_file.name}: {e}")
            skipped_count += 1

        print()

    # Generate __init__.py
    if generated_count > 0 or force:
        init_file = output_dir / "__init__.py"
        common.log_step("Generating __init__.py...")

        try:
            init_content = generate_init_file(entities_by_file)
            init_file.write_text(init_content, encoding="utf-8")
            common.log_success(f"Generated: {common.format_path(init_file)}")
        except Exception as e:
            common.log_error(f"Failed to generate __init__.py: {e}")

        print()

    return generated_count, skipped_count


def clean_generated_filters(output_dir: pathlib.Path, force: bool = False) -> int:
    """Clean generated filter files.

    Args:
        output_dir: Directory containing generated files.
        force: Whether to skip confirmation prompt.

    Returns:
        Number of files deleted.
    """
    if not output_dir.exists():
        common.log_warn(f"Directory does not exist: {output_dir}")
        return 0

    files = list(output_dir.glob("*.py"))
    if not files:
        common.log_info("No generated files to clean")
        return 0

    # Confirm deletion
    if not force:
        print()
        common.log_warn(f"This will delete {len(files)} generated file(s):")
        print()
        for file in files:
            print(f"  - {common.format_path(file)}")
        print()

        response = input(common.format_key("Continue? [y/N]: ")).strip().lower()
        if response not in ("y", "yes"):
            common.log_info("Cancelled")
            return 0
        print()

    # Delete files
    deleted_count = 0
    for file in files:
        try:
            file.unlink()
            common.log_success(f"Deleted: {common.format_path(file)}")
            deleted_count += 1
        except Exception as e:
            common.log_error(f"Failed to delete {file}: {e}")

    # Remove directory if empty
    try:
        if not any(output_dir.iterdir()):
            output_dir.rmdir()
            common.log_success(f"Removed empty directory: {common.format_path(output_dir)}")
    except Exception:
        pass

    return deleted_count


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate type-safe filter builders for PrototypeX entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s gen                  # Generate filters for all entities
  %(prog)s gen --force          # Overwrite existing files
  %(prog)s clean                # Remove all generated filters
  %(prog)s clean --force        # Remove without confirmation
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Gen command
    gen_parser = subparsers.add_parser("gen", help="Generate filter builders")
    gen_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files without prompting",
    )
    gen_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Remove generated filters")
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clean_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Setup
    if args.quiet:
        common.setup_quiet_mode()

    common.init_ansi_formatter()

    # Determine paths
    entities_dir = PROJECT_ROOT / "audex" / "entity"
    output_dir = PROJECT_ROOT / "audex" / "filters" / "generated"

    if args.command == "gen":
        common.print_header("PrototypeX Filter Generator")

        if not entities_dir.exists():
            common.die(f"Entities directory not found: {entities_dir}")

        # Generate filters
        generated, skipped = generate_filters(entities_dir, output_dir, args.force)

        # Print summary
        common.log_info("Summary:")
        print(f"  Generated: {common.format_bold(str(generated))}")
        if skipped > 0:
            print(f"  Skipped:   {common.format_dim(str(skipped))}")
        print()

        if generated > 0:
            common.log_success("Filter generation completed!")
            print()
            common.log_info("Import filters like this:")
            print(f"  {common.format_code('from audex.filters.generated import user_filter')}")
            print()
        else:
            common.log_warn("No filters were generated")

        sys.exit(0 if generated > 0 else 1)

    elif args.command == "clean":
        common.print_header("PrototypeX Filter Cleaner")

        deleted = clean_generated_filters(output_dir, args.force)

        print()
        if deleted > 0:
            common.log_success(f"Deleted {deleted} file(s)")
        else:
            common.log_info("No files deleted")
        print()

        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        common.log_warn("Operation cancelled by user")
        print()
        sys.exit(130)
    except Exception as exc:
        print()
        common.log_error(f"Unexpected error: {exc}")
        traceback.print_exc()
        print()
        sys.exit(1)
