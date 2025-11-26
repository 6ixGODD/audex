from __future__ import annotations

import abc
import argparse
import pathlib
import typing as t

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import ModelWrapValidatorHandler
from pydantic import ValidationError
from pydantic import model_validator

from audex import __description__
from audex import __title__
from audex import __version__
from audex.cli.exceptions import InvalidArgumentError


class BaseArgs(BaseModel, abc.ABC):
    """Base class for CLI arguments with automatic argparse integration.

    Automatically generates argparse arguments from Pydantic fields with support for:
    - Basic types (str, int, float, bool)
    - Optional types (Optional[T])
    - List types (list[T])
    - Literal types for choices
    - Union types
    - Path types
    - Nested subcommands

    Example:
        ```python
        class MyArgs(BaseArgs):
            name: str = Field(description="Your name")
            age: int = Field(default=18, description="Your age")
            verbose: bool = Field(
                default=False, description="Verbose output"
            )

            def run(self) -> None:
                print(f"Hello {self.name}, age {self.age}")


        parser = argparse.ArgumentParser()
        MyArgs.build_args(parser)
        parser.set_defaults(func=MyArgs.func)
        args = parser.parse_args()
        args.func(args)
        ```
    """

    @abc.abstractmethod
    def run(self) -> None:
        """Execute the command logic.

        Must be implemented by subclasses.
        """
        pass

    @classmethod
    def func(cls, args: argparse.Namespace) -> None:
        """Entry point called by argparse.  Parses args and calls run().

        Args:
            args: The argparse Namespace containing parsed arguments.
        """
        instance = cls.parse_args(args)
        instance.run()

    @classmethod
    def build_args(cls, parser: argparse.ArgumentParser) -> None:
        """Build argparse arguments from Pydantic fields.

        Automatically generates appropriate argparse arguments based on field types:
        - bool: Uses store_true/store_false based on default value
        - list[T]: Uses nargs='+' or nargs='*'
        - Optional[T]: Makes argument optional with default None
        - Literal[... ]: Uses choices parameter
        - Path/pathlib.Path: Uses type=pathlib.Path

        Args:
            parser: The argparse parser to add arguments to.
        """
        for field, fieldinfo in cls.__pydantic_fields__.items():
            # Skip internal fields
            if field.startswith("_"):
                continue

            arg_name = f"--{field.replace('_', '-')}"
            alias = fieldinfo.alias
            flags = (arg_name, f"-{alias}") if alias else (arg_name,)
            required = fieldinfo.is_required()
            ann = fieldinfo.annotation
            help_text = fieldinfo.description or ""
            default = fieldinfo.default

            # Unwrap the annotation to get the actual type
            origin = t.get_origin(ann)
            args_types = t.get_args(ann)

            # Handle Optional[T] (Union[T, None])
            if origin is t.Union:
                # Filter out NoneType
                non_none_types = [a for a in args_types if a is not type(None)]
                if type(None) in args_types and non_none_types:
                    # This is Optional[T]
                    ann = (
                        non_none_types[0]
                        if len(non_none_types) == 1
                        else t.Union[tuple(non_none_types)]  # noqa
                    )
                    required = False
                    origin = t.get_origin(ann)
                    args_types = t.get_args(ann)

            # Handle Literal types
            choices = None
            if origin is t.Literal:
                choices = list(args_types)
                ann = type(choices[0]) if choices else str
                origin = None  # Reset origin since we've extracted the type

            # Handle List types
            if origin is list:
                item_type = args_types[0] if args_types else str

                # Handle List[Literal[...]]
                if t.get_origin(item_type) is t.Literal:
                    choices = list(t.get_args(item_type))
                    item_type = type(choices[0]) if choices else str

                # Determine nargs
                nargs = "*" if not required else "+"

                parser.add_argument(
                    *flags,
                    type=item_type,
                    nargs=nargs,
                    default=default if not required else None,
                    help=help_text,
                    choices=choices,
                    dest=field,
                )
                continue

            # Handle Path types
            if ann in (pathlib.Path, pathlib.PosixPath, pathlib.WindowsPath):
                if required:
                    parser.add_argument(
                        *flags,
                        required=True,
                        type=pathlib.Path,
                        help=help_text,
                        dest=field,
                    )
                else:
                    parser.add_argument(
                        *flags,
                        type=pathlib.Path,
                        default=default,
                        help=help_text,
                        dest=field,
                    )
                continue

            # Handle boolean types
            is_bool = ann is bool or (origin is None and ann is bool)
            if is_bool:
                # Determine action based on default value
                if default is True:
                    # If default is True, use store_false with --no-prefix
                    neg_flags = (
                        (f"--no-{field.replace('_', '-')}", f"-N{alias}")
                        if alias
                        else (f"--no-{field.replace('_', '-')}",)
                    )
                    parser.add_argument(
                        *neg_flags,
                        action="store_false",
                        help=help_text or f"Disable {field}",
                        dest=field,
                        default=True,
                    )
                else:
                    # If default is False or not set, use store_true
                    parser.add_argument(
                        *flags,
                        action="store_true",
                        help=help_text,
                        dest=field,
                        default=False,
                    )
                continue

            # Handle regular types (str, int, float, etc.)
            try:
                type_func = ann if callable(ann) else str
            except Exception:
                type_func = str

            if required:
                parser.add_argument(
                    *flags,
                    required=True,
                    type=type_func,
                    help=help_text,
                    choices=choices,
                    dest=field,
                )
            else:
                parser.add_argument(
                    *flags,
                    default=default,
                    type=type_func,
                    help=help_text,
                    choices=choices,
                    dest=field,
                )

    @classmethod
    def parse_args(cls, args: argparse.Namespace) -> t.Self:
        """Parse argparse Namespace into a Pydantic model instance.

        Args:
            args: The argparse Namespace to parse.

        Returns:
            An instance of the class with validated fields.

        Raises:
            pydantic.ValidationError: If validation fails.
        """
        # Convert Namespace to dict and filter out None values for optional fields
        args_dict = vars(args)

        # Remove non-field attributes (like 'func')
        field_names = set(cls.__pydantic_fields__.keys())
        filtered_dict = {k: v for k, v in args_dict.items() if k in field_names}

        return cls.model_validate(filtered_dict, by_alias=False, by_name=True, strict=False)

    @classmethod
    def register_subparser(
        cls,
        subparsers: argparse._SubParsersAction,
        name: str,
        help_text: str | None = None,
        aliases: list[str] | None = None,
    ) -> argparse.ArgumentParser:
        """Register this command as a subcommand.

        Supports nested subcommands by returning the parser which can have
        its own subparsers added.

        Args:
            subparsers: The subparsers action from parent parser.
            name: The name of this subcommand.
            help_text: Help text for this subcommand.  If None, uses class docstring.
            aliases: Alternative names for this subcommand.

        Returns:
            The argument parser for this subcommand, which can be used to
            add nested subcommands.

        Example:
            ```python
            # Create main parser
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(
                dest="command", required=True
            )

            # Register top-level command
            db_parser = DBCommand.register_subparser(
                subparsers, "db", "Database commands"
            )

            # Add nested subcommands
            db_subparsers = db_parser.add_subparsers(
                dest="db_command", required=True
            )
            MigrateCommand.register_subparser(
                db_subparsers, "migrate", "Run migrations"
            )
            ```
        """
        if help_text is None:
            help_text = cls.__doc__.strip() if cls.__doc__ else f"{name} command"

        parser = subparsers.add_parser(
            name,
            help=help_text,
            description=help_text,
            aliases=aliases or [],
        )
        cls.build_args(parser)
        parser.set_defaults(func=cls.func)
        return parser

    @model_validator(mode="wrap")
    @classmethod
    def reraise(cls, data: t.Any, handler: ModelWrapValidatorHandler[t.Self]) -> t.Self:
        """Reraise validation errors with clearer messages.

        Args:
            data: The input data to validate.
            handler: The model wrap validator handler.

        Returns:
            The validated model instance.

        Raises:
            InvalidArgumentError: If validation fails.
        """
        try:
            return handler(data)
        except ValidationError as e:
            raise InvalidArgumentError.from_validation_error(e) from e

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        arbitrary_types_allowed=True,  # Allow types like pathlib.Path
        populate_by_name=True,  # Allow population by field name
    )


def parser_with_version(
    prog: str = __title__,
    description: str = __description__,
) -> argparse.ArgumentParser:
    """Create an argument parser with --version and --help built-in.

    Helper function to create a parser with common options.

    Args:
        prog: Program name.
        description: Program description.

    Returns:
        Configured ArgumentParser with version info.
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit.",
    )
    return parser
