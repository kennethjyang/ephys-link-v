from sensapex import UMP

from ephys_link.base_binding import BaseBinding
from ephys_link.bindings.sensapex_binding import SensapexBinding

# Mapping of detected manipulators at startup.
# Make -> ID -> Binding.
# In kebab-case.
manipulators: dict[str, dict[str, BaseBinding]] = {}


def find_manipulators() -> dict[str, dict[str, BaseBinding]]:
    """Search across binding interfaces for manipulators and return them."""

    # Reset in place so importers holding the pool by value (server.py does
    # `from ephys_link.manipulators import manipulators`) observe the update.
    manipulators.clear()

    # Sensapex.
    ump = UMP.get_ump()
    found_manipulators = ump.list_devices()

    sensapex = manipulators.setdefault("sensapex", {})
    for manipulator_id in found_manipulators:
        sensapex[str(manipulator_id)] = SensapexBinding(str(manipulator_id))

    # Fake bindings (uncomment to use).
    # manipulators["fake"]["0"] = FakeBinding("0")
    # manipulators["fake"]["1"] = FakeBinding("1")

    return manipulators
