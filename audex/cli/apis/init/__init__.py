from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    from audex.cli.apis.init import gencfg
    from audex.cli.apis.init import vprgroup

    gencfg.Args.register_subparser(
        subparsers,
        name="gencfg",
        help_text="Generate a default configuration file for Audex.",
    )
    vprgroup.Args.register_subparser(
        subparsers,
        name="vprgroup",
        help_text="Initialize a VPR service group.",
    )
