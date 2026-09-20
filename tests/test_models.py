import pytest
from pydantic import ValidationError

from ephys_link.models import (
    CustomPayload,
    ManipulatorInfo,
    ManipulatorStateResponse,
    ServerStateResponse,
    SetPositionPayload,
    TaskCreationResponse,
    TaskState,
)

# ManipulatorInfo


def test_manipulator_info_accepts_valid_range():
    info = ManipulatorInfo(
        make="fake", model="Fake", id="0", axis_limits=[(0, 20), (0, 10)]
    )
    assert info.make == "fake"
    assert info.axis_limits == [(0, 20), (0, 10)]


def test_manipulator_info_defaults_empty_optional_collections():
    info = ManipulatorInfo(make="fake", model="Fake", id="0", axis_limits=[(0, 1)])
    assert info.custom_properties == set()
    assert info.custom_functions == {}


def test_manipulator_info_rejects_descending_range():
    with pytest.raises(ValidationError):
        ManipulatorInfo(make="fake", model="Fake", id="0", axis_limits=[(20, 0)])


def test_manipulator_info_rejects_equal_range_bounds():
    with pytest.raises(ValidationError):
        ManipulatorInfo(make="fake", model="Fake", id="0", axis_limits=[(5, 5)])


@pytest.mark.parametrize("field", ["make", "model", "id"])
def test_manipulator_info_rejects_empty_identifier(field: str):
    with pytest.raises(ValidationError):
        ManipulatorInfo(**{field: "", "make": "fake", "model": "Fake", "id": "0"})  # type: ignore[bad-argument-type]


def test_manipulator_info_rejects_no_axis_limits():
    with pytest.raises(ValidationError):
        ManipulatorInfo(make="fake", model="Fake", id="0", axis_limits=[])


# TaskState


def test_task_state_defaults_to_unended():
    task = TaskState(manipulators={("fake", "0")}, time_started=1.0)
    assert task.time_ended is None
    assert task.message is None


def test_task_state_accepts_ended_after_started():
    task = TaskState(manipulators=set(), time_started=1.0, time_ended=2.0)
    assert task.time_ended == 2.0


def test_task_state_rejects_ended_before_started():
    with pytest.raises(ValidationError):
        TaskState(manipulators=set(), time_started=10.0, time_ended=5.0)


# ManipulatorStateResponse


def test_manipulator_state_response_accepts_extra_fields():
    response = ManipulatorStateResponse(position=[1.0, 2.0], temperature=20)
    assert response.position == [1.0, 2.0]
    assert response.active_task_id is None
    assert response.temperature == 20  # type: ignore[missing-attribute]


def test_manipulator_state_response_rejects_empty_position():
    with pytest.raises(ValidationError):
        ManipulatorStateResponse(position=[])


# SetPositionPayload


def test_set_position_payload_accepts_positive_speed():
    payload = SetPositionPayload(position=[0.0], speed=1.0)
    assert payload.speed == 1.0


def test_set_position_payload_rejects_non_positive_speed():
    with pytest.raises(ValidationError):
        SetPositionPayload(position=[0.0], speed=0)  # type: ignore[bad-argument-type]


def test_set_position_payload_rejects_empty_position():
    with pytest.raises(ValidationError):
        SetPositionPayload(position=[], speed=1.0)


# ServerStateResponse / TaskCreationResponse / CustomPayload


def test_server_state_response_holds_version():
    response = ServerStateResponse(server_version="5.1.0", manipulators=set())
    assert response.server_version == "5.1.0"
    assert response.manipulators == set()


def test_task_creation_response_holds_id():
    response = TaskCreationResponse(task_id="abc")
    assert response.task_id == "abc"


def test_custom_payload_holds_name_and_kwargs():
    payload = CustomPayload(name="jackhammer", kwargs={"a": 1, "b": 2})
    assert payload.name == "jackhammer"
    assert payload.kwargs == {"a": 1, "b": 2}
