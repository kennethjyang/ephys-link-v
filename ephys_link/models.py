from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel


class Model(BaseModel):
    """Immutable model with camel-case named enabled."""

    model_config = ConfigDict(
        frozen=True, alias_generator=to_camel, populate_by_name=True
    )


class ManipulatorInfo(Model):
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
    axis_limits: Annotated[
        list[tuple[float, float]],
        Field(min_length=1),
    ]
    custom_properties: set[str]
    custom_functions: dict[str, list[str]]

    # noinspection nested-decorators
    @field_validator("axis_limits")
    @classmethod
    def validate_range_ascending(
        cls,
        value: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        for pair in value:
            if pair[1] <= pair[0]:
                raise ValueError(f"Pair {pair} is an invalid range.")
        return value


class TaskState(Model):
    """State of a manipulator task.

    Args:
        time_started: Time stamp of when the task was created (in seconds).
        manipulators: Make-ID pairs of manipulators involved.
        time_ended: Time stamp of when the task was ended (in seconds). Is None when unfinished.
        message: Progress and any reports for clients. None means no message.
    """

    time_started: Annotated[float, Field(gt=0)]
    manipulators: set[tuple[str, str]]
    time_ended: Annotated[float | None, Field(None, gt=0)]
    message: str | None = None

    @model_validator(mode="after")
    def validate_time_stamp(self) -> Self:
        if self.time_ended is None:
            return self
        if self.time_ended < self.time_started:
            raise ValueError(
                f"Time stamp cannot have ended ({self.time_ended}) before it started ({self.time_started})."
            )

        return self


class ServerStateResponse(Model):
    """Version and known manipulators response.

    Args:
        server_version: Ephys Link V server version.
        manipulators: Set of found manipulators at startup.
    """

    server_version: str
    manipulators: set[ManipulatorInfo]


class ManipulatorStateResponse(Model):
    """Individual manipulator state response.

    Args:
        position: Manipulator translation stage values in mm.
        active_task_id: Task ID this manipulator is actively moving in. None means the manipulator is stopped.
    """

    model_config = ConfigDict(extra="allow")

    position: Annotated[list[float], Field(min_length=1)]
    active_task_id: str | None = None
