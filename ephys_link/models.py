from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Model with camel-case named enabled."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Manipulator(CamelModel):
    """Definition of a manipulator."""

    make: Annotated[str, Field(min_length=1)]
    model: Annotated[str, Field(min_length=1)]
    id: Annotated[str, Field(min_length=1)]
    axis_limits: Annotated[list[float], Field(min_length=1)]
    custom_properties: dict[str, Any]
    custom_functions: dict[str, dict[str, Any]]


class ServerStateResponse(CamelModel):
    """Version and known manipulators response."""

    server_version: str
    manipulators: list[Manipulator]
