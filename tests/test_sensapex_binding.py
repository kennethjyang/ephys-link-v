from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Iterable, Iterator
from typing import Any

import pytest

from ephys_link import tasks as tasks_module
from ephys_link.bindings import sensapex_binding
from ephys_link.bindings.sensapex_binding import SensapexBinding
from ephys_link.models import TaskState


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    """Drive a single coroutine to completion without pytest-asyncio."""
    return asyncio.run(coro)


# ---- Fakes for the sensapex UMP / device / movement event. ----------------


class FakeFinishedEvent:
    def __init__(self, raise_wait: bool = False) -> None:
        self._raise = raise_wait
        self.waited = False

    def wait(self) -> bool:
        self.waited = True
        if self._raise:
            raise RuntimeError("movement wait failed")
        return True


class FakeMovementEvent:
    def __init__(
        self,
        *,
        reached: bool = True,
        interrupted: bool = False,
        finished: FakeFinishedEvent | None = None,
    ) -> None:
        self._reached = reached
        self._interrupted = interrupted
        self.finished_event = finished or FakeFinishedEvent()

    def reached_target(self) -> bool:
        return self._reached

    @property
    def interrupted(self) -> bool:
        return self._interrupted


class FakeDevice:
    def __init__(self, event: FakeMovementEvent | None = None, n_axes: int = 4) -> None:
        self._event = event or FakeMovementEvent()
        self._n_axes = n_axes
        self.got_calls: list[tuple[list[int], float]] = []
        self.stop_calls: list[None] = []

    def n_axes(self) -> int:
        return self._n_axes

    def get_pos(self) -> list[int]:
        return [0, 1000, 0, 1000]

    def goto_pos(self, positions: list[int], speed: float) -> FakeMovementEvent:
        self.got_calls.append((list(positions), speed))
        return self._event

    def stop(self) -> None:
        self.stop_calls.append(None)


class FakeUMP:
    _device: FakeDevice | None = None

    @classmethod
    def get_ump(cls) -> FakeUMP:
        return cls()

    def get_device(self, manipulator_id: str) -> FakeDevice:
        assert FakeUMP._device is not None
        return FakeUMP._device


@pytest.fixture(autouse=True)
def patch_ump(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeDevice]:
    device = FakeDevice()
    monkeypatch.setattr(sensapex_binding, "UMP", FakeUMP)
    FakeUMP._device = device
    tasks_module.tasks.clear()
    yield device
    FakeUMP._device = None
    tasks_module.tasks.clear()


def make_binding(device: FakeDevice, manipulator_id: str = "0") -> SensapexBinding:
    binding = SensapexBinding(manipulator_id)
    binding.device = device  # type: ignore[bad-assignment]
    return binding


def seed_task(task_id: str, manipulators: Iterable[tuple[str, str]]) -> None:
    tasks_module.tasks[task_id] = TaskState(manipulators=manipulators, time_started=1.0)


# ---- get_position / state / info / stop -----------------------------------


def test_get_position_converts_um_to_mm(patch_ump: FakeDevice):
    binding = make_binding(patch_ump)
    assert run(binding.get_position()) == [0.0, 1.0, 0.0, 1.0]


def test_state_reports_position_and_active_task_id(patch_ump: FakeDevice):
    binding = make_binding(patch_ump)
    binding.task_id = "t1"
    state = run(binding.state())
    assert state.position == [0.0, 1.0, 0.0, 1.0]
    assert state.active_task_id == "t1"


def test_info_reports_four_axis_model(patch_ump: FakeDevice):
    binding = make_binding(patch_ump)
    info = binding.info()
    assert info.model == "uMp-4"
    assert info.make == "Sensapex"
    assert info.custom_functions == {"jackhammer": ["a", "b", "c", "d"]}


def test_info_reports_three_axis_model(patch_ump: FakeDevice):
    binding = make_binding(FakeDevice(n_axes=3))
    assert binding.info().model == "uMp-3"


def test_stop_calls_device_stop_and_returns_true(patch_ump: FakeDevice):
    binding = make_binding(patch_ump)
    assert run(binding.stop()) is True
    assert patch_ump.stop_calls == [None]


# ---- set_position end-state branches --------------------------------------


def test_set_position_finished_message(patch_ump: FakeDevice):
    device = patch_ump
    seed_task("t1", {("sensapex", "0"), ("sensapex", "1")})
    binding = make_binding(device)

    run(binding.set_position([1.0, 2.0, 3.0, 4.0], 0.5, "t1"))

    assert device.got_calls == [([1000, 2000, 3000, 4000], 0.5)]
    assert tasks_module.tasks["t1"].message == "Sensapex 0 movement FINISHED."
    # Two manipulators remain -> task is not ended by this one.
    assert tasks_module.tasks["t1"].time_ended is None


def test_set_position_did_not_reach_message(patch_ump: FakeDevice):
    device = patch_ump
    device._event = FakeMovementEvent(reached=False)
    seed_task("t1", {("sensapex", "0"), ("sensapex", "1")})
    binding = make_binding(device)

    run(binding.set_position([1.0], 0.5, "t1"))

    assert tasks_module.tasks["t1"].message == "Sensapex 0 DID NOT reach target."


def test_set_position_interrupted_message(patch_ump: FakeDevice):
    device = patch_ump
    device._event = FakeMovementEvent(reached=True, interrupted=True)
    seed_task("t1", {("sensapex", "0"), ("sensapex", "1")})
    binding = make_binding(device)

    run(binding.set_position([1.0], 0.5, "t1"))

    assert tasks_module.tasks["t1"].message == "Sensapex 0 movement INTERRUPTED."


def test_set_position_failure_message(patch_ump: FakeDevice):
    device = patch_ump
    device._event = FakeMovementEvent(finished=FakeFinishedEvent(raise_wait=True))
    seed_task("t1", {("sensapex", "0"), ("sensapex", "1")})
    binding = make_binding(device)

    run(binding.set_position([1.0], 0.5, "t1"))

    message = tasks_module.tasks["t1"].message
    assert message is not None and "movement failed" in message


def test_set_position_ends_task_when_last_manipulator(patch_ump: FakeDevice):
    device = patch_ump
    seed_task("t1", {("sensapex", "0")})
    binding = make_binding(device)

    run(binding.set_position([1.0], 0.5, "t1"))

    ended = tasks_module.tasks["t1"]
    assert ended.time_ended is not None
    assert ended.message == "Completed"
    assert binding.task_id is None
