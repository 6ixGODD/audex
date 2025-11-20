from __future__ import annotations

from audex import utils
from audex.entity import BaseEntity
from audex.entity import StringField


class Doctor(BaseEntity):
    id: str = StringField(immutable=True, default_factory=lambda: utils.gen_id(prefix="doctor-"))
