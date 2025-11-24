from __future__ import annotations

import typing as t

from audex.valueobj.common.auth import Password
from audex.valueobj.common.email import Email
from audex.valueobj.common.phone import CNPhone


class LoginCommand(t.NamedTuple):
    """Command for doctor login."""

    eid: str
    password: Password


class RegisterCommand(t.NamedTuple):
    """Command for doctor registration."""

    eid: str
    password: Password
    name: str
    department: str | None = None
    title: str | None = None
    hospital: str | None = None
    phone: CNPhone | None = None
    email: Email | None = None


class UpdateCommand(t.NamedTuple):
    """Command for updating doctor profile."""

    name: str | None = None
    department: str | None = None
    title: str | None = None
    hospital: str | None = None
    phone: CNPhone | None = None
    email: Email | None = None


class VPEnrollResult(t.NamedTuple):
    """Result of voiceprint enrollment/update.

    Attributes:
        vp_id: ID of the VP entity.
        vpr_uid: UID in the VPR system.
        audio_key: Storage key of the audio file.
        duration_ms: Duration of the recording in milliseconds.
    """

    vp_id: str
    vpr_uid: str
    audio_key: str
    duration_ms: int
