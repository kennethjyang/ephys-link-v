from abc import ABC, abstractmethod

from ephys_link.models import ManipulatorInfo, ManipulatorStateResponse


class BaseBinding(ABC):
    """Definition of a manipulator binding."""

    def __init__(self, manipulator_id: str):
        self.manipulator_id = manipulator_id

    @abstractmethod
    def info(self) -> ManipulatorInfo:
        """Intrinsic manipulator info."""

    @abstractmethod
    async def state(self) -> ManipulatorStateResponse:
        """Current state of the manipulator."""
