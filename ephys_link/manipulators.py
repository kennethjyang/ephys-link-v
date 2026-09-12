from ephys_link.base_binding import BaseBinding

# Mapping of detected manipulators at startup.
# Make -> ID -> Binding.
# In kebab-case.
manipulators: dict[str, dict[str, BaseBinding]] = {}


def find_manipulators() -> dict[str, dict[str, BaseBinding]]:
    """Search across binding interfaces for manipulators and return them."""
    global manipulators

    manipulators = {}
    return manipulators
