from abc import ABC, abstractmethod

from ephys_link.models import ManipulatorStateResponse


class BaseBinding(ABC):
    """Definition of a manipulator binding."""

    @abstractmethod
    async def state(self) -> ManipulatorStateResponse:
        """Current state of the manipulator."""
