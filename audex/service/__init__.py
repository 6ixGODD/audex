from __future__ import annotations

from audex.helper.mixin import LoggingMixin


class BaseService(LoggingMixin):
    """Base service class providing common infrastructure for domain services.

    All domain services should inherit from this base class to get access to
    logging capabilities and other shared infrastructure.

    Attributes:
        logger: Logger instance bound with the service's logtag.

    Example:
        ```python
        class DoctorService(BaseService):
            __logtag__ = "DoctorService"

            def __init__(self):
                super().__init__()
                # Service-specific initialization
        ```
    """

    def __init__(self) -> None:
        super().__init__()
