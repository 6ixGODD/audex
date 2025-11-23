from __future__ import annotations

from audex.valueobj import EnumValueObject


class SessionStatus(EnumValueObject):
    """Session status enumeration.

    Represents the current state of a recording session:
    - DRAFT: Session created but not yet started
    - IN_PROGRESS: Session is actively recording
    - COMPLETED: Session finished successfully
    - CANCELLED: Session was cancelled before completion
    """

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
