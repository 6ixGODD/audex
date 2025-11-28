from __future__ import annotations

import argparse


def register_apis(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    from audex.cli.apis import init
    from audex.cli.apis import serve

    # Only register serve and init, not run
    serve.Args.register_subparser(subparsers, name="serve", help_text="Serve Audex export service")
    init.register(subparsers)
