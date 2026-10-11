import sys
from collections import defaultdict

import httpx
from sensapex import UMP

from ephys_link.base_binding import BaseBinding
from ephys_link.bindings.fake_binding import FakeBinding
from ephys_link.bindings.mpm_binding import MPMBinding
from ephys_link.bindings.sensapex_binding import SensapexBinding

# Mapping of detected manipulators at startup.
# Make -> ID -> Binding.
# In kebab-case.
manipulators: defaultdict[str, dict[str, BaseBinding]] = defaultdict(dict)


def find_manipulators(
    num_fake_manipulators: int = 0,
) -> dict[str, dict[str, BaseBinding]]:
    """Search across binding interfaces for manipulators and return them."""

    # Reset bindings.
    manipulators.clear()

    # Sensapex — not available on macOS.
    if sys.platform != "darwin":
        ump = UMP.get_ump()
        found_manipulators = ump.list_devices()

        for manipulator_id in found_manipulators:
            manipulators["sensapex"][str(manipulator_id)] = SensapexBinding(
                str(manipulator_id)
            )

    # MPM — optional, skip if server unreachable.
    try:
        resp = httpx.get("http://localhost:8080/", timeout=2.0)
        resp.raise_for_status()
        data = resp.json()
        for probe in data.get("ProbeArray", []):
            manipulators["new-scale-mpm"][probe["Id"]] = MPMBinding(
                probe["Id"], port=8080
            )
    except Exception:  # noqa: S110
        pass

    # Fake bindings.
    for i in range(num_fake_manipulators):
        manipulators["fake"][str(i)] = FakeBinding(str(i))

    return manipulators
