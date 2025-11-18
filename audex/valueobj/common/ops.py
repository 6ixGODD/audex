from __future__ import annotations

from audex.valueobj import EnumValueObject


class Op(EnumValueObject):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"
    IN = "in"
    NIN = "nin"
    BETWEEN = "between"
    HAS = "has"


class Order(EnumValueObject):
    ASC = "asc"
    DESC = "desc"
