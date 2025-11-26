from __future__ import annotations

import argparse


def register_apis(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    from audex.cli.apis import init
    from audex.cli.apis import run
    from audex.cli.apis import serve

    run.Args.register_subparser(subparsers, name="run", help_text="Run Audex Application")
    serve.Args.register_subparser(subparsers, name="serve", help_text="Serve Audex export service")

    init.register(subparsers)  # Subparser registered inside function
