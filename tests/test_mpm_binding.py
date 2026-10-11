from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ephys_link.base_binding import BaseBinding
from ephys_link.models import TaskState
from ephys_link.tasks import tasks


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    """Drive a single coroutine to completion without pytest-asyncio."""
    return asyncio.run(coro)


# ---- fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_tasks() -> None:
    tasks.clear()


def seed_task(task_id: str, manipulators: list[tuple[str, str]]) -> None:
    tasks[task_id] = TaskState(
        manipulators=manipulators,
        time_started=1.0,
    )


def make_binding(
    mock_client: MagicMock,
    manipulator_id: str = "A",
    port: int = 8080,
) -> BaseBinding:
    """Create an MPMBinding with a mocked httpx.AsyncClient."""
    from ephys_link.bindings.mpm_binding import MPMBinding

    binding = MPMBinding(manipulator_id, port=port)
    binding._client = mock_client  # type: ignore[assignment]
    return binding


# ---- Helpers for mock responses -------------------------------------------


def _make_probe_response(
    x: float = 1.0,
    y: float = 2.0,
    z: float = 3.0,
    polar: float = 45.0,
    pitch: float = 10.0,
    shank_orientation: float = 90.0,
    shank_count: int = 32,
    posterior_angle: float = 0.0,
    probe_index: int = 0,
) -> dict[str, Any]:
    """Build a ProbeArray response for a single probe."""
    probe = {
        "Stage_X": x,
        "Stage_Y": y,
        "Stage_Z": z,
        "Polar": polar,
        "Pitch": pitch,
        "ShankOrientation": shank_orientation,
        "ShankCount": shank_count,
    }
    return {
        "ProbeArray": [probe],
        "PosteriorAngle": posterior_angle,
    }


# ---- info -----------------------------------------------------------------


def test_info_returns_correct_metadata():
    mock_client = MagicMock()
    binding = make_binding(mock_client)
    info = binding.info()

    assert info.make == "New Scale"
    assert info.model == "Pathfinder MPM"
    assert info.id == "A"
    assert info.axis_limits == [(0.0, 15.0), (0.0, 15.0), (0.0, 15.0)]
    assert info.custom_properties == {"angles", "shankCount"}


# ---- get_position ---------------------------------------------------------


def test_get_position_returns_xyz_from_server():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = _make_probe_response(x=5.5, y=6.6, z=7.7)
    mock_client.get = AsyncMock(return_value=mock_response)

    binding = make_binding(mock_client)
    position = run(binding.get_position())

    assert position == [5.5, 6.6, 7.7]
    mock_client.get.assert_called_once_with("/")


# ---- state ----------------------------------------------------------------


def test_state_includes_angles_and_shank_count():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = _make_probe_response(
        x=1.0,
        y=2.0,
        z=3.0,
        polar=45.0,
        pitch=10.0,
        shank_orientation=90.0,
        shank_count=32,
        posterior_angle=5.0,
    )
    mock_client.get = AsyncMock(return_value=mock_response)

    binding = make_binding(mock_client)
    state = run(binding.state())

    assert state.position == [1.0, 2.0, 3.0]
    assert state.active_task_id is None
    state_any: Any = state
    assert state_any.angles["polar"] == 40.0  # (45 - 5) % 360
    assert state_any.angles["pitch"] == 10.0
    assert state_any.angles["shankOrientation"] == 90.0
    assert state_any.shank_count == 32


# ---- set_position ---------------------------------------------------------


def test_set_position_sends_correct_commands():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = _make_probe_response()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.put = AsyncMock(return_value=MagicMock())

    # Use two manipulators so end_task is NOT called (matching Sensapex pattern).
    seed_task("t1", [("new-scale-mpm", "A"), ("new-scale-mpm", "B")])
    binding = make_binding(mock_client)

    run(binding.set_position([1.0, 2.0, 3.0], speed=0.5, task_id="t1"))

    # Verify ProbeStepMode was sent (speed > 0.1 → fine mode 0).
    put_calls = mock_client.put.call_args_list
    step_mode_call = put_calls[0]
    assert step_mode_call[1]["json"]["PutId"] == "ProbeStepMode"
    assert step_mode_call[1]["json"]["Probe"] == 0
    assert step_mode_call[1]["json"]["StepMode"] == 0

    # Verify ProbeMotion was sent.
    motion_call = put_calls[1]
    assert motion_call[1]["json"]["PutId"] == "ProbeMotion"
    assert motion_call[1]["json"]["X"] == 1.0
    assert motion_call[1]["json"]["Y"] == 2.0
    assert motion_call[1]["json"]["Z"] == 3.0


def test_set_position_ends_task():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = _make_probe_response()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.put = AsyncMock(return_value=MagicMock())

    # Single manipulator → end_task IS called.
    seed_task("t1", [("new-scale-mpm", "A")])
    binding = make_binding(mock_client)

    run(binding.set_position([1.0, 2.0, 3.0], speed=0.5, task_id="t1"))

    assert tasks["t1"].time_ended is not None
    assert binding.task_id is None


def test_set_position_handles_stuck_condition():
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Return the same position every time (stuck).
    mock_response.json.return_value = _make_probe_response(x=0.0, y=0.0, z=0.0)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.put = AsyncMock(return_value=MagicMock())

    # Use two manipulators so end_task is NOT called.
    seed_task("t1", [("new-scale-mpm", "A"), ("new-scale-mpm", "B")])
    binding = make_binding(mock_client)

    run(binding.set_position([5.0, 5.0, 5.0], speed=0.5, task_id="t1"))

    # Should have detected stuck and set the message.
    assert tasks["t1"].message is not None
    assert "STUCK" in tasks["t1"].message


# ---- stop -----------------------------------------------------------------


def test_stop_sends_probe_stop():
    mock_client = MagicMock()
    mock_client.put = AsyncMock(return_value=MagicMock())

    binding = make_binding(mock_client)
    result = run(binding.stop())

    assert result is True
    put_calls = mock_client.put.call_args_list
    assert len(put_calls) == 1
    assert put_calls[0][1]["json"]["PutId"] == "ProbeStop"
    assert put_calls[0][1]["json"]["Probe"] == 0


# ---- error handling -------------------------------------------------------


def test_set_position_handles_http_error():
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Server error"))
    mock_client.put = AsyncMock(return_value=MagicMock())

    # Use two manipulators so end_task is NOT called.
    seed_task("t1", [("new-scale-mpm", "A"), ("new-scale-mpm", "B")])
    binding = make_binding(mock_client)

    run(binding.set_position([1.0, 2.0, 3.0], speed=0.5, task_id="t1"))

    assert tasks["t1"].message is not None
    assert "movement failed" in tasks["t1"].message
    assert binding.task_id is None
