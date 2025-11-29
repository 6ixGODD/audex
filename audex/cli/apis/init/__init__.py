from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    from audex.cli.apis.init import gencfg
    from audex.cli.apis.init import setup
    from audex.cli.apis.init import vprgroup

    parser = subparsers.add_parser(
        "init",
        help="Initialize various Audex components.",
    )
    init_subparsers = parser.add_subparsers(
        title="init commands",
        dest="init_command",
    )

    gencfg.Args.register_subparser(
        init_subparsers,
        name="gencfg",
        help_text="Generate a default configuration file for Audex.",
    )
    setup.Args.register_subparser(
        init_subparsers,
        name="setup",
        help_text="Run the initial setup wizard for Audex.",
    )
    vprgroup.Args.register_subparser(
        init_subparsers,
        name="vprgroup",
        help_text="Initialize a VPR service group.",
    )
