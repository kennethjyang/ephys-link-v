from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Model with camel-case named enabled."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ManipulatorInfo(CamelModel):
    """Definition of a manipulator.

    Args:
        make: Manufacturer/vendor display name (kebab-case version is used as key).
        model: Display name of the manipulator model.
        id: Manipulator ID (unique within the make namespace).
        axis_limits: Minimum and maximum values for each axis of the manipulator.
        custom_properties: Names of the custom properties in the manipulator state.
        custom_functions: Signatures of the custom functions to call on the binding (name -> parameter name list)
    """

    make: Annotated[str, Field(min_length=1)]
    model: Annotated[str, Field(min_length=1)]
    id: Annotated[str, Field(min_length=1)]
    axis_limits: Annotated[list[tuple[float, float]], Field(min_length=1)]
    custom_properties: list[str]
    custom_functions: dict[str, list[str]]


class ServerStateResponse(CamelModel):
    """Version and known manipulators response.

    Args:
        server_version: Ephys Link V server version.
        manipulators: List of found manipulators at startup.
    """

    server_version: str
    manipulators: list[ManipulatorInfo]


class ManipulatorStateResponse(CamelModel):
    """Individual manipulator state response.

    Args:
        position: Manipulator translation stage values in mm.
        is_moving: Flag for if this manipulator is in an _ongoing_ task.
    """

    model_config = ConfigDict(extra="allow")

    position: Annotated[list[float], Field(min_length=1)]
    is_moving: bool
