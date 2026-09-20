from typing import Any

import pytest
from fastapi.testclient import TestClient

from ephys_link import manipulators as manipulators_module
from ephys_link import tasks as tasks_module
from ephys_link.manipulators import manipulators
from ephys_link.models import ManipulatorInfo, ManipulatorStateResponse, TaskState
from ephys_link.server import app

client = TestClient(app)


class FakeBinding:
    jackhammer: Any = None

    def __init__(
        self,
        task_id: str | None = None,
        fail_state: bool = False,
        fail_stop: bool = False,
    ) -> None:
        self.manipulator_id = "0"
        self.task_id = task_id
        self.fail_state = fail_state
        self.fail_stop = fail_stop
        self.state_calls = 0
        self.stop_calls = 0

    def info(self) -> ManipulatorInfo:
        return ManipulatorInfo(
            make="fake",
            model="Fake",
            id="0",
            axis_limits=[(0, 10)],
        )

    async def get_position(self) -> list[float]:
        return [1.0, 2.0]

    async def state(self) -> ManipulatorStateResponse:
        self.state_calls += 1
        if self.fail_state:
            raise RuntimeError("state boom")
        return ManipulatorStateResponse(
            position=[1.0, 2.0],
            active_task_id=self.task_id,
        )

    async def set_position(
        self,
        position: list[float],
        speed: float,
        task_id: str,
    ) -> None:
        self.task_id = task_id

    async def stop(self) -> bool:
        self.stop_calls += 1
        if self.fail_stop:
            raise RuntimeError("stop boom")
        return True


class _EmptyUMP:
    def list_devices(self) -> list[int]:
        return []


class _EmptyUmpClass:
    @staticmethod
    def get_ump() -> _EmptyUMP:
        return _EmptyUMP()


@pytest.fixture(autouse=True)
def clean_pool():
    manipulators.clear()
    tasks_module.tasks.clear()
    yield
    manipulators.clear()
    tasks_module.tasks.clear()


def install(make: str, manipulator_id: str, binding: FakeBinding) -> FakeBinding:
    manipulators[make][manipulator_id] = binding  # type: ignore[unsupported-operation]
    return binding


def _task(
    manipulators_set: set[tuple[str, str]],
    time_ended: float | None = None,
    time_started: float = 1.0,
) -> TaskState:
    return TaskState(
        manipulators=manipulators_set,
        time_ended=time_ended,
        time_started=time_started,
    )


# GET /


def test_root_returns_server_version():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["serverVersion"] == "5.1.0-dev1"


# GET /find


def test_find_with_no_devices(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(manipulators_module, "UMP", _EmptyUmpClass)
    monkeypatch.setattr(
        manipulators_module,
        "SensapexBinding",
        lambda manipulator_id: FakeBinding(),  # type: ignore[implicit-any-lambda]
    )

    response = client.get("/find")
    assert response.status_code == 200
    assert "sensapex" not in manipulators


# GET /state/{make}/{id}


def test_state_success():
    binding = install("fake", "0", FakeBinding())
    response = client.get("/state/fake/0")
    assert response.status_code == 200
    assert response.json()["position"] == [1.0, 2.0]
    assert binding.state_calls == 1


def test_state_unknown_manipulator_404():
    response = client.get("/state/fake/99")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_state_failure_503():
    install("fake", "0", FakeBinding(fail_state=True))
    response = client.get("/state/fake/0")
    assert response.status_code == 503


# GET /states


def test_states_success():
    install("fake", "0", FakeBinding())
    response = client.get("/states", params={"manipulator": "fake/0"})
    assert response.status_code == 200
    assert response.json()["fake"]["0"]["position"] == [1.0, 2.0]


def test_states_malformed_pair_400():
    response = client.get("/states", params={"manipulator": "nodelimiter"})
    assert response.status_code == 400
    assert "Malformed" in response.json()["detail"]


def test_states_unknown_manipulator_404():
    response = client.get("/states", params={"manipulator": "fake/99"})
    assert response.status_code == 404


def test_states_failure_503():
    install("fake", "0", FakeBinding(fail_state=True))
    response = client.get("/states", params={"manipulator": "fake/0"})
    assert response.status_code == 503


# GET /task/{task_id}


def test_task_active_is_deleted_after_read():
    tasks_module.tasks["t1"] = _task({("fake", "0")})
    response = client.get("/task/t1")
    assert response.status_code == 200
    assert "t1" not in tasks_module.tasks


def test_task_ended_is_retained():
    tasks_module.tasks["t1"] = _task(set(), time_ended=2.0)
    response = client.get("/task/t1")
    assert response.status_code == 200
    assert "t1" in tasks_module.tasks


def test_task_unknown_surfaces_503():
    # The route's own 404 is caught by its `except Exception` and re-raised as 503.
    response = client.get("/task/nope")
    assert response.status_code == 503


# PUT /stop-manipulator/{make}/{id}


def test_stop_manipulator_with_task_ends_task():
    binding = install("fake", "0", FakeBinding(task_id="t1"))
    tasks_module.tasks["t1"] = _task({("fake", "0")})

    response = client.put("/stop-manipulator/fake/0")
    assert response.status_code == 200
    assert binding.stop_calls == 1
    assert tasks_module.tasks["t1"].time_ended is not None
    assert binding.task_id is None


def test_stop_manipulator_already_stopped():
    binding = install("fake", "0", FakeBinding(task_id=None))

    response = client.put("/stop-manipulator/fake/0")
    assert response.status_code == 200
    assert binding.stop_calls == 1


def test_stop_manipulator_unknown_404():
    response = client.put("/stop-manipulator/fake/99")
    assert response.status_code == 404


def test_stop_manipulator_failure_503():
    install("fake", "0", FakeBinding(fail_stop=True))
    response = client.put("/stop-manipulator/fake/0")
    assert response.status_code == 503


# PUT /stop-task/{task_id}


def test_stop_task_stops_each_manipulator():
    b0 = install("fake", "0", FakeBinding(task_id="t1"))
    b1 = install("fake", "1", FakeBinding(task_id="t1"))
    tasks_module.tasks["t1"] = _task({("fake", "0"), ("fake", "1")})

    response = client.put("/stop-task/t1")
    assert response.status_code == 200
    assert b0.stop_calls == 1
    assert b1.stop_calls == 1
    assert tasks_module.tasks["t1"].time_ended is not None


def test_stop_task_unknown_404():
    response = client.put("/stop-task/nope")
    assert response.status_code == 404


def test_stop_task_already_ended_is_noop():
    tasks_module.tasks["t1"] = _task({("fake", "0")}, time_ended=2.0)
    response = client.put("/stop-task/t1")
    assert response.status_code == 200


# PUT /stop-all


def test_stop_all_runs_without_error():
    tasks_module.tasks["t1"] = _task({("fake", "0")})
    install("fake", "0", FakeBinding(task_id="t1"))

    response = client.put("/stop-all")
    assert response.status_code == 200
    assert tasks_module.tasks["t1"].time_ended is not None


# PUT /set-position/{make}/{id}


def test_set_position_creates_task():
    install("fake", "0", FakeBinding())
    response = client.put(
        "/set-position/fake/0", json={"position": [1.0, 2.0], "speed": 0.5}
    )
    assert response.status_code == 200
    task_id = response.json()["taskId"]
    assert task_id in tasks_module.tasks


def test_set_position_unknown_manipulator_404():
    response = client.put(
        "/set-position/fake/99", json={"position": [1.0], "speed": 0.5}
    )
    assert response.status_code == 404


def test_set_position_failure_503():
    install("fake", "0", FakeBinding(fail_stop=True))
    response = client.put(
        "/set-position/fake/0", json={"position": [1.0], "speed": 0.5}
    )
    assert response.status_code == 503


# PUT /set-positions


def test_set_positions_creates_task():
    install("fake", "0", FakeBinding())
    install("fake", "1", FakeBinding())
    payload = {
        "fake": {
            "0": {"position": [1.0], "speed": 0.5},
            "1": {"position": [2.0], "speed": 0.5},
        }
    }
    response = client.put("/set-positions", json=payload)
    assert response.status_code == 200
    assert response.json()["taskId"] in tasks_module.tasks


def test_set_positions_unknown_manipulator_503():
    # stop_manipulator's 404 is caught by the loop's `except Exception` and re-raised as 503.
    payload = {"fake": {"9": {"position": [1.0], "speed": 0.5}}}
    response = client.put("/set-positions", json=payload)
    assert response.status_code == 503


def test_set_positions_failure_503():
    install("fake", "0", FakeBinding(fail_stop=True))
    payload = {"fake": {"0": {"position": [1.0], "speed": 0.5}}}
    response = client.put("/set-positions", json=payload)
    assert response.status_code == 503


# PUT /custom/{make}/{id}


def test_custom_calls_callable_and_creates_task():
    binding = install("fake", "0", FakeBinding())
    binding.jackhammer = lambda **kwargs: None  # type: ignore[implicit-any-lambda]

    response = client.put("/custom/fake/0", json={"name": "jackhammer", "kwargs": {}})
    assert response.status_code == 200
    assert response.json()["taskId"] in tasks_module.tasks


def test_custom_unknown_manipulator_404():
    response = client.put("/custom/fake/99", json={"name": "jackhammer", "kwargs": {}})
    assert response.status_code == 404


def test_custom_non_callable_attribute_503():
    binding = install("fake", "0", FakeBinding())
    binding.jackhammer = 123

    response = client.put("/custom/fake/0", json={"name": "jackhammer", "kwargs": {}})
    assert response.status_code == 503


def test_custom_missing_attribute_503():
    install("fake", "0", FakeBinding())
    response = client.put(
        "/custom/fake/0", json={"name": "does_not_exist", "kwargs": {}}
    )
    assert response.status_code == 503
