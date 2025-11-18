from __future__ import annotations

import abc
import argparse
import typing as t

from pydantic import BaseModel
from pydantic import ConfigDict


class BaseArgs(BaseModel, abc.ABC):
    @abc.abstractmethod
    def run(self) -> None:
        pass

    @classmethod
    def func(cls, args: argparse.Namespace) -> None:
        instance = cls.parse_args(args)
        instance.run()

    @classmethod
    @abc.abstractmethod
    def build_args(cls, parser: argparse.ArgumentParser) -> None:
        pass

    @classmethod
    def parse_args(cls, args: argparse.Namespace) -> t.Self:
        return cls.model_validate(vars(args), strict=True)

    model_config = ConfigDict(extra="ignore")
