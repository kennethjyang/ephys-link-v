from typing import override

from sensapex import UMP

from ephys_link.base_binding import BaseBinding
from ephys_link.models import ManipulatorInfo
from ephys_link.tasks import end_task, remove_manipulator, set_message


class SensapexBinding(BaseBinding):
    def __init__(self, manipulator_id: str) -> None:
        super().__init__(manipulator_id)
        self.ump = UMP.get_ump()
        self.device = self.ump.get_device(self.manipulator_id)

    @override
    def info(self) -> ManipulatorInfo:
        axis_count = self.device.n_axes()

        return ManipulatorInfo(
            make="Sensapex",
            model="uMp-4" if axis_count == 4 else "uMp-3",
            id=self.manipulator_id,
            axis_limits=[(0, 20)] * axis_count,
            custom_functions={"jackhammer": ["a", "b", "c", "d"]},
        )

    @override
    async def get_position(self) -> list[float]:
        return [axis / 1000 for axis in self.device.get_pos()]

    @override
    async def set_position(
        self, position: list[float], speed: float, task_id: str
    ) -> None:
        # Add set task for this manipulator.
        self.task_id = task_id

        # Start movement.
        set_message(task_id, f"Sending movement to Sensapex {self.manipulator_id}.")
        movement_event = self.device.goto_pos([axis * 1000 for axis in position], speed)
        set_message(
            task_id,
            f"Movement sent to Sensapex {self.manipulator_id}. Waiting for completion...",
        )

        # Wait for movement.
        movement_event.finished_event.wait()
        if not movement_event.interrupted:
            set_message(task_id, f"Sensapex {self.manipulator_id} movement finished.")

        # Remove manipulator and then end task if there are no more manipulators on it.
        if remove_manipulator(task_id, "sensapex", self.manipulator_id):
            end_task(task_id, "Completed")

        # Remove task from manipulator.
        self.task_id = None

    @override
    async def stop(self) -> bool:
        self.device.stop()
        return True
