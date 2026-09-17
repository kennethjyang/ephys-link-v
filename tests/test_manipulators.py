from pytest import MonkeyPatch

from ephys_link import manipulators


class _FakeUMP:
    def list_devices(self) -> list[int]:
        return [1, 2]


class _FakeUmpClass:
    @staticmethod
    def get_ump() -> _FakeUMP:
        return _FakeUMP()


class _FakeBinding:
    def __init__(self, manipulator_id: str) -> None:
        self.manipulator_id = manipulator_id


def test_find_manipulators_updates_pool_by_value(monkeypatch: MonkeyPatch) -> None:
    # server.py imports the pool by value (`from ephys_link.manipulators import
    # manipulators`); the pool must therefore be populated in place so that an
    # already-held reference observes the found manipulators.
    monkeypatch.setattr(manipulators, "UMP", _FakeUmpClass)
    monkeypatch.setattr(manipulators, "SensapexBinding", _FakeBinding)

    # Hold the pool the way server.py does, before discovery runs.
    manipulators.manipulators.clear()
    pool = manipulators.manipulators

    manipulators.find_manipulators()

    # The by-value reference must reflect the discovered manipulators.
    assert "sensapex" in pool
    assert set(pool["sensapex"]) == {"1", "2"}
