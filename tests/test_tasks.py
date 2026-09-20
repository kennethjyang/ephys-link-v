import asyncio

import pytest

from ephys_link import tasks as tasks_module
from ephys_link.models import TaskState


def run(coro):
    """Drive a single coroutine to completion without pytest-asyncio."""
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_tasks():
    tasks_module.tasks.clear()
    yield
    tasks_module.tasks.clear()


# get_task


def test_get_task_missing_returns_none():
    assert run(tasks_module.get_task("nope")) is None


def test_get_task_returns_existing():
    tasks_module.tasks["t1"] = TaskState(manipulators={("fake", "0")})

    assert run(tasks_module.get_task("t1")).manipulators == {("fake", "0")}


# delete_task


def test_delete_task_removes_existing():
    tasks_module.tasks["t1"] = TaskState(manipulators=set())

    run(tasks_module.delete_task("t1"))

    assert "t1" not in tasks_module.tasks


def test_delete_task_missing_is_noop():
    run(tasks_module.delete_task("nope"))

    assert tasks_module.tasks == {}


# remove_manipulator


def test_remove_manipulator_missing_task_returns_false():
    assert run(tasks_module.remove_manipulator("nope", "fake", "0")) is False


def test_remove_manipulator_last_returns_true_and_clears():
    tasks_module.tasks["t1"] = TaskState(manipulators={("fake", "0")})

    assert run(tasks_module.remove_manipulator("t1", "fake", "0")) is True
    assert tasks_module.tasks["t1"].manipulators == set()


def test_remove_manipulator_not_last_returns_false_and_keeps_rest():
    tasks_module.tasks["t1"] = TaskState(manipulators={("fake", "0"), ("fake", "1")})

    assert run(tasks_module.remove_manipulator("t1", "fake", "0")) is False
    assert tasks_module.tasks["t1"].manipulators == {("fake", "1")}


def test_remove_manipulator_absent_pair_is_noop_but_task_stays():
    tasks_module.tasks["t1"] = TaskState(manipulators={("fake", "0")})

    # The pair isn't in the task, so nothing is removed and there is still one
    # manipulator left -> not the last one.
    assert run(tasks_module.remove_manipulator("t1", "fake", "9")) is False
    assert tasks_module.tasks["t1"].manipulators == {("fake", "0")}


# set_message


def test_set_message_missing_task_is_noop():
    run(tasks_module.set_message("nope", "hello"))

    assert "nope" not in tasks_module.tasks


def test_set_message_sets_and_clears_message():
    tasks_module.tasks["t1"] = TaskState(manipulators=set())

    run(tasks_module.set_message("t1", "hello"))
    assert tasks_module.tasks["t1"].message == "hello"

    run(tasks_module.set_message("t1", None))
    assert tasks_module.tasks["t1"].message is None


# end_task


def test_end_task_missing_task_is_noop():
    run(tasks_module.end_task("nope", "done"))

    assert "nope" not in tasks_module.tasks


def test_end_task_marks_ended_and_sets_message():
    tasks_module.tasks["t1"] = TaskState(manipulators=set(), time_started=1.0)

    run(tasks_module.end_task("t1", "done"))

    ended = tasks_module.tasks["t1"]
    assert ended.time_ended is not None
    assert ended.message == "done"
