from __future__ import annotations

import typing as t

from audex.valueobj.common.auth import Password
from audex.valueobj.common.email import Email
from audex.valueobj.common.phone import CNPhone


class LoginCommand(t.NamedTuple):
    eid: str
    password: Password


class RegisterCommand(t.NamedTuple):
    eid: str
    password: Password
    name: str
    department: str | None = None
    title: str | None = None
    hospital: str | None = None
    phone: CNPhone | None = None
    email: Email | None = None


class UpdateCommand(t.NamedTuple):
    name: str | None = None
    department: str | None = None
    title: str | None = None
    hospital: str | None = None
    phone: CNPhone | None = None
    email: Email | None = None
