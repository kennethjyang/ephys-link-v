from sensapex import UMP

from ephys_link.base_binding import BaseBinding
from ephys_link.bindings.sensapex_binding import SensapexBinding

# Mapping of detected manipulators at startup.
# Make -> ID -> Binding.
# In kebab-case.
manipulators: dict[str, dict[str, BaseBinding]] = {}


def find_manipulators() -> dict[str, dict[str, BaseBinding]]:
    """Search across binding interfaces for manipulators and return them."""
    global manipulators

    # Reset.
    manipulators = {}

    # Sensapex.
    ump = UMP.get_ump()
    found_manipulators = ump.list_devices()

    for manipulator_id in found_manipulators:
        manipulators["sensapex"][str(manipulator_id)] = SensapexBinding(
            str(manipulator_id)
        )

    # Fake bindings (uncomment to use).
    # manipulators["fake"]["0"] = FakeBinding("0")
    # manipulators["fake"]["1"] = FakeBinding("1")

    return manipulators
