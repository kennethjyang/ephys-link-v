from typing import override

from ephys_link.base_binding import BaseBinding
from ephys_link.models import ManipulatorInfo
from ephys_link.tasks import end_task, remove_manipulator


class FakeBinding(BaseBinding):
    def __init__(self, manipulator_id: str) -> None:
        super().__init__(manipulator_id)
        self.position: list[float] = [0] * 4

    @override
    def info(self) -> ManipulatorInfo:
        return ManipulatorInfo(
            make="Fake", model="Fake", id=self.manipulator_id, axis_limits=[(0, 20)] * 4
        )

    @override
    async def get_position(self) -> list[float]:
        return self.position

    @override
    async def set_position(
        self, position: list[float], speed: float, task_id: str
    ) -> None:
        # Add set task for this manipulator.
        self.task_id = task_id

        # Do movement.
        self.position = position

        # Remove manipulator and then end task if there are no more manipulators on it.
        if await remove_manipulator(task_id, "fake", self.manipulator_id):
            await end_task(task_id, "Completed")

        # Remove task from manipulator.
        self.task_id = None

    @override
    async def stop(self) -> bool:
        return True
