from __future__ import annotations

from audex.valueobj import EnumValueObject


class Speaker(EnumValueObject):
    """Speaker identification enumeration.

    Represents the speaker in a conversation:
    - DOCTOR: The registered doctor (verified by voiceprint)
    - PATIENT: The patient (anyone not matching doctor's voiceprint)
    """

    DOCTOR = "doctor"
    PATIENT = "patient"
