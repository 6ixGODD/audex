from __future__ import annotations

import argparse
import collections
import importlib
import inspect
import pathlib
import sys
import traceback
import typing as t

from audex.entity import BaseEntity
from audex.entity import Entity
from audex.entity import FieldSpec
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
                    and obj is not Entity
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


def resolve_type_alias(type_hint: t.Any) -> t.Any:
    """Resolve TypeAlias to its actual type."""
    if t.get_origin(type_hint) is not None:
        return type_hint

    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        try:
            module = importlib.import_module(type_hint.__module__)
            actual_type = getattr(module, type_hint.__name__, None)

            if actual_type is not None:
                if hasattr(actual_type, "__value__"):
                    return actual_type.__value__
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
    if type_hint is type(None):
        return

    origin = t.get_origin(type_hint)
    args = t.get_args(type_hint)

    if origin is not None:
        if origin in (list, list, t.Sequence, t.Union):
            for arg in args:
                extract_imports_from_type(arg, collected_imports)
            return
        extract_imports_from_type(origin, collected_imports)
        for arg in args:
            extract_imports_from_type(arg, collected_imports)
        return

    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        module = type_hint.__module__
        type_name = type_hint.__name__

        if module in ("builtins", "typing"):
            return

        if module.startswith("audex."):
            collected_imports.add(f"from {module} import {type_name}")
            return

        if module == "datetime":
            collected_imports.add("import datetime")
            return

        if module != "__main__":
            collected_imports.add(f"from {module} import {type_name}")


def format_type_annotation(type_hint: t.Any) -> str:
    """Format a type annotation to a proper string representation."""
    import datetime as dt

    if type_hint is type(None):
        return "None"

    origin = t.get_origin(type_hint)
    args = t.get_args(type_hint)

    if origin is t.Union:
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            formatted_type = format_type_annotation(non_none_type)
            return f"{formatted_type} | None"
        formatted_args = []
        for arg in args:
            formatted_arg = format_type_annotation(arg)
            formatted_args.append(formatted_arg)
        return " | ".join(formatted_args)

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

    if type_hint in (int, str, float, bool):
        return type_hint.__name__

    if type_hint is dt.datetime:
        return "datetime.datetime"
    if type_hint is dt.date:
        return "datetime.date"
    if type_hint is dt.time:
        return "datetime.time"

    if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
        module = type_hint.__module__
        type_name = type_hint.__name__

        if module in ("builtins", "typing"):
            return type_name

        if module.startswith("audex."):
            return type_name

        if module == "datetime":
            return f"datetime.{type_name}"

        if module != "__main__":
            return type_name

        return type_name

    hint_str = str(type_hint)

    if hint_str.startswith("<class '") and hint_str.endswith("'>"):
        return hint_str[8:-2]

    if hint_str.startswith("<enum '") and hint_str.endswith("'>"):
        return hint_str[7:-2]

    if "typing.Union[" in hint_str:
        import re

        match = re.search(r"typing\.Union\[(.*)]", hint_str)
        if match:
            union_content = match.group(1)
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

            cleaned_parts = []
            for part in parts:
                part = part.strip()
                if part.startswith("audex."):
                    part = part.split(".")[-1]
                if part.startswith("<class '") and part.endswith("'>"):
                    part = part[8:-2]
                cleaned_parts.append(part)

            return " | ".join(cleaned_parts)

    hint_str = hint_str.replace("typing.", "t.")

    if "audex." in hint_str:
        import re

        hint_str = re.sub(r"audex\.[a-zA-Z0-9_.]+\.([a-zA-Z0-9_]+)", r"\1", hint_str)

    return hint_str


def get_field_type_annotation(
    field_name: str, entity_class: type[BaseEntity], field_spec: FieldSpec[t.Any]
) -> str:
    """Get the type annotation string for a field."""
    try:
        hints = t.get_type_hints(entity_class)
        if field_name in hints:
            hint = hints[field_name]
            resolved_hint = resolve_type_alias(hint)
            return format_type_annotation(resolved_hint)

        if hasattr(field_spec, "_field_type") and field_spec._field_type:
            resolved_type = resolve_type_alias(field_spec._field_type)
            return format_type_annotation(resolved_type)

    except Exception as e:
        common.log_warn(f"Failed to get type annotation for {field_name}: {e}")

    return "t.Any"


def get_all_fields_in_mro(entity_class: type[BaseEntity]) -> dict[str, FieldSpec[t.Any]]:
    """Get all fields from the entity and its base classes in MRO
    order."""
    all_fields: dict[str, FieldSpec[t.Any]] = {}

    # Traverse MRO in reverse to get base class fields first
    for base in reversed(entity_class.__mro__):
        if base is object:
            continue
        if hasattr(base, "_fields"):
            all_fields.update(base._fields)

    return all_fields


def extract_all_imports_from_entity(entity_class: type[BaseEntity]) -> set[str]:
    """Extract all type-related imports needed for the stub."""
    imports: set[str] = set()

    all_fields = get_all_fields_in_mro(entity_class)

    for field_name, field_spec in all_fields.items():
        try:
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

    # Extract imports from method signatures
    for name, method in inspect.getmembers(entity_class, predicate=inspect.isfunction):
        if name.startswith("_") and name not in ("__init__", "__eq__", "__hash__"):
            continue
        try:
            inspect.signature(method)
            hints = t.get_type_hints(method)
            for _param_name, param_hint in hints.items():
                resolved_hint = resolve_type_alias(param_hint)
                extract_imports_from_type(resolved_hint, imports)
        except Exception:
            pass

    return imports


def get_field_default_value(field_spec: FieldSpec[t.Any]) -> str | None:
    """Get the default value representation for a field."""
    if field_spec.default_factory is not None:
        return "..."
    if field_spec.default is not None:
        if isinstance(field_spec.default, (bool, int, float)):
            return str(field_spec.default)
        if isinstance(field_spec.default, str):
            return repr(field_spec.default)
        return "..."
    if field_spec.nullable:
        return "None"
    # Required field
    return None


def get_base_classes(entity_class: type[BaseEntity]) -> list[str]:
    """Get the list of base class names for the entity."""
    bases = []
    for base in entity_class.__bases__:
        if base is Entity or base is object:
            continue
        bases.append(base.__name__)
    return bases if bases else ["BaseEntity"]


def get_entity_methods(entity_class: type[BaseEntity]) -> list[tuple[str, inspect.Signature]]:
    """Get all public methods and their signatures for the entity."""
    methods = []

    for name, method in inspect.getmembers(entity_class, predicate=inspect.isfunction):
        # Skip private methods except __init__
        if name.startswith("_") and name != "__init__":
            continue

        # Skip inherited methods from BaseEntity/Entity unless overridden
        if (
            name in ("touch", "filter", "dumps", "is_field_sortable")
            and hasattr(BaseEntity, name)
            and getattr(entity_class, name) is getattr(BaseEntity, name)
        ):
            continue

        # Only include methods defined in this class
        if method.__qualname__.split(".")[0] != entity_class.__name__:
            continue

        try:
            sig = inspect.signature(method)
            methods.append((name, sig))
        except Exception:
            pass

    return methods


def get_entity_properties(entity_class: type[BaseEntity]) -> list[tuple[str, t.Any]]:
    """Get all properties for the entity."""
    properties = []

    for name, attr in inspect.getmembers(entity_class):
        if isinstance(attr, property):
            # Only include properties defined in this class
            for cls in entity_class.__mro__:
                if name in cls.__dict__ and isinstance(cls.__dict__[name], property):
                    if cls is entity_class:
                        properties.append((name, attr))
                    break

    return properties


def format_method_signature(
    method_name: str,
    signature: inspect.Signature,
    entity_class: type[BaseEntity],
) -> list[str]:
    """Format a method signature for the stub file."""
    lines = []

    # Get type hints for the method
    try:
        method = getattr(entity_class, method_name)
        hints = t.get_type_hints(method)
    except Exception:
        hints = {}

    params = []
    for param_name, param in signature.parameters.items():
        if param_name == "self":
            params.append("self")
            continue

        # Get type annotation
        if param_name in hints:
            type_hint = format_type_annotation(hints[param_name])
        elif param.annotation != inspect.Parameter.empty:
            type_hint = format_type_annotation(param.annotation)
        else:
            type_hint = "t.Any"

        # Get default value
        if param.default != inspect.Parameter.empty:
            if param.default is None:
                default = " = None"
            elif isinstance(param.default, (bool, int, float)):
                default = f" = {param.default}"
            elif isinstance(param.default, str):
                default = f" = {param.default!r}"
            else:
                default = " = ..."
        else:
            default = ""

        # Handle *args and **kwargs
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            params.append(f"*{param_name}: {type_hint}")
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            params.append(f"**{param_name}: {type_hint}")
        else:
            params.append(f"{param_name}: {type_hint}{default}")

    # Get return type
    if "return" in hints:
        return_type = format_type_annotation(hints["return"])
    elif signature.return_annotation != inspect.Signature.empty:
        return_type = format_type_annotation(signature.return_annotation)
    else:
        return_type = "None"

    # Format the method signature
    if method_name == "__init__":
        lines.append("    def __init__(")
    else:
        lines.append(f"    def {method_name}(")

    for i, param in enumerate(params):
        if i == 0 and param == "self":
            if len(params) == 1:
                lines[-1] += "self"
            else:
                lines.append("        self,")
        else:
            if i == len(params) - 1:
                lines.append(f"        {param},")
            else:
                lines.append(f"        {param},")

    lines.append(f"    ) -> {return_type}: ...")

    return lines


def generate_entity_stub(entity_info: EntityInfo) -> list[str]:
    """Generate stub code for a single entity."""
    entity_name = entity_info.name
    entity_class = entity_info.class_obj

    lines = []

    # Get base classes
    base_classes = get_base_classes(entity_class)
    bases_str = ", ".join(base_classes)

    # Class definition
    lines.append(f"class {entity_name}({bases_str}):")

    # Get all fields from entity and its parents
    all_fields = get_all_fields_in_mro(entity_class)

    # Add field type annotations
    for field_name, field_spec in all_fields.items():
        type_annotation = get_field_type_annotation(field_name, entity_class, field_spec)
        lines.append(f"    {field_name}: {type_annotation}")

    # Add __init__ method
    init_params = ["self", "*"]
    for field_name, field_spec in all_fields.items():
        type_annotation = get_field_type_annotation(field_name, entity_class, field_spec)
        default_value = get_field_default_value(field_spec)

        if default_value is None:
            init_params.append(f"{field_name}: {type_annotation}")
        else:
            init_params.append(f"{field_name}: {type_annotation} = {default_value}")

    lines.append("    def __init__(")
    for i, param in enumerate(init_params):
        if param == "self":
            lines.append("        self,")
        elif param == "*":
            lines.append("        *,")
        else:
            if i == len(init_params) - 1:
                lines.append(f"        {param},")
            else:
                lines.append(f"        {param},")
    lines.append("    ) -> None: ...")

    # Add properties
    properties = get_entity_properties(entity_class)
    for prop_name, prop_obj in properties:
        # Get return type from property getter
        try:
            hints = t.get_type_hints(prop_obj.fget)
            return_type = format_type_annotation(hints["return"]) if "return" in hints else "t.Any"
        except Exception:
            return_type = "t.Any"

        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {return_type}: ...")

    # Add methods (excluding __init__)
    methods = get_entity_methods(entity_class)
    for method_name, signature in methods:
        if method_name == "__init__":
            continue
        method_lines = format_method_signature(method_name, signature, entity_class)
        lines.extend(method_lines)

    return lines


def generate_stub_file(entity_infos: list[EntityInfo]) -> str:
    """Generate stub file content for entities."""
    if not entity_infos:
        return ""

    # Collect all imports
    all_imports: set[str] = set()

    # Collect base classes used
    base_classes_used: set[str] = set()

    for entity_info in entity_infos:
        imports = extract_all_imports_from_entity(entity_info.class_obj)
        all_imports.update(imports)
        bases = get_base_classes(entity_info.class_obj)
        base_classes_used.update(bases)

    # Build the stub file
    lines = [
        "# This file is auto-generated by PrototypeX stub generator.",
        "# Do not edit manually - changes will be overwritten.",
        "# Regenerate using: python -m scripts.genstubs gen",
        "",
        "from __future__ import annotations",
        "",
        "import typing as t",
    ]

    # Add datetime import if needed
    if any("import datetime" in imp for imp in all_imports):
        lines.append("import datetime")
        all_imports = {imp for imp in all_imports if imp != "import datetime"}

    lines.append("")

    if "BaseEntity" in base_classes_used:
        lines.append("from audex.entity import BaseEntity")
    if "Entity" in base_classes_used:
        lines.append("from audex.entity import Entity")

    # Add other imports
    if all_imports:
        lines.extend(sorted(all_imports))
        lines.append("")

    lines.append("")

    # Generate stubs for each entity
    for entity_info in sorted(entity_infos, key=lambda e: e.name):
        entity_lines = generate_entity_stub(entity_info)
        lines.extend(entity_lines)
        lines.append("")

    return "\n".join(lines)


def generate_stubs(
    entities_dir: pathlib.Path,
    output_dir: pathlib.Path,
    force: bool = False,
) -> tuple[int, int]:
    """Generate stub files for all entities.

    Args:
        entities_dir: Directory containing entity files.
        output_dir: Directory to write generated stub files.
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

    # Generate stubs for each source file
    for source_file, entity_infos in sorted(entities_by_file.items(), key=lambda x: x[0].name):
        output_file = output_dir / (source_file.stem + ".pyi")
        entity_names = ", ".join(info.name for info in entity_infos)

        common.log_step(
            f"Generating stubs for {common.format_bold(source_file.name)}: "
            f"{common.format_dim(entity_names)}..."
        )

        # Check if file exists
        if output_file.exists() and not common.check_file_exists(output_file, force):
            skipped_count += 1
            print()
            continue

        try:
            # Generate code
            code = generate_stub_file(entity_infos)

            # Write file
            output_file.write_text(code, encoding="utf-8")

            common.log_success(f"Generated: {common.format_path(output_file)}")
            generated_count += 1

        except Exception as e:
            common.log_error(f"Failed to generate stub for {source_file.name}: {e}")
            traceback.print_exc()
            skipped_count += 1

        print()

    return generated_count, skipped_count


def clean_generated_stubs(output_dir: pathlib.Path, force: bool = False) -> int:
    """Clean generated stub files.

    Args:
        output_dir: Directory containing generated files.
        force: Whether to skip confirmation prompt.

    Returns:
        Number of files deleted.
    """
    if not output_dir.exists():
        common.log_warn(f"Directory does not exist: {output_dir}")
        return 0

    files = list(output_dir.glob("*.pyi"))
    if not files:
        common.log_info("No generated stub files to clean")
        return 0

    # Confirm deletion
    if not force:
        print()
        common.log_warn(f"This will delete {len(files)} generated stub file(s):")
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

    return deleted_count


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate type stub files (.pyi) for PrototypeX entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s gen                  # Generate stubs for all entities
  %(prog)s gen --force          # Overwrite existing files
  %(prog)s clean                # Remove all generated stubs
  %(prog)s clean --force        # Remove without confirmation
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Gen command
    gen_parser = subparsers.add_parser("gen", help="Generate stub files")
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
    clean_parser = subparsers.add_parser("clean", help="Remove generated stubs")
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
    output_dir = PROJECT_ROOT / "audex" / "entity"

    if args.command == "gen":
        common.print_header("PrototypeX Stub Generator")

        if not entities_dir.exists():
            common.die(f"Entities directory not found: {entities_dir}")

        # Generate stubs
        generated, skipped = generate_stubs(entities_dir, output_dir, args.force)

        # Print summary
        common.log_info("Summary:")
        print(f"  Generated: {common.format_bold(str(generated))}")
        if skipped > 0:
            print(f"  Skipped:   {common.format_dim(str(skipped))}")
        print()

        if generated > 0:
            common.log_success("Stub generation completed!")
            print()
        else:
            common.log_warn("No stubs were generated")

        sys.exit(0 if generated > 0 else 1)

    elif args.command == "clean":
        common.print_header("PrototypeX Stub Cleaner")

        deleted = clean_generated_stubs(output_dir, args.force)

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
