from ephys_link.base_binding import BaseBinding

# Mapping of detected manipulators at startup.
# Make -> ID -> Binding.
# In kebab-case.
manipulators: dict[str, dict[str, BaseBinding]] = {}
