from abc import ABC, abstractmethod

from ephys_link.models import ManipulatorInfo, ManipulatorStateResponse


class BaseBinding(ABC):
    """Definition of a manipulator binding."""

    def __init__(self, manipulator_id: str):
        self.manipulator_id: str = manipulator_id
        self.task_id: str | None = None

    @abstractmethod
    def info(self) -> ManipulatorInfo:
        """Intrinsic manipulator info."""

    @abstractmethod
    async def get_position(self) -> list[float]:
        """Returns the axis-order absolute position of the manipulator."""

    async def state(self) -> ManipulatorStateResponse:
        """Returns the current state of the manipulator."""
        return ManipulatorStateResponse(
            position=await self.get_position(),
            active_task_id=self.task_id,
        )

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the manipulator."""
