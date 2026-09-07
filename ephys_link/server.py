from collections import defaultdict
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.params import Query

from ephys_link.manipulators import manipulators
from ephys_link.models import ManipulatorStateResponse, ServerStateResponse

app = FastAPI()


@app.get("/")
async def server_state() -> ServerStateResponse:
    return ServerStateResponse(
        server_version="5.1.0-dev1",
        manipulators=[
            manipulator.info()
            for make in manipulators.values()
            for manipulator in make.values()
        ],
    )


@app.get("/{make}/{manipulator_id}")
async def manipulator_state(make: str, manipulator_id: str) -> ManipulatorStateResponse:
    try:
        return await manipulators[make][manipulator_id].state()
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Manipulator {make} {manipulator_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Manipulator state could not be retrieved: {e}"
        )


@app.get("/state")
async def manipulator_states(
    manipulators_requested: Annotated[
        list[str], Query(alias="manipulator", min_length=1)
    ],
) -> dict[str, dict[str, ManipulatorStateResponse]]:
    response = defaultdict(dict)
    for manipulator in manipulators_requested:
        make, manipulator_id = manipulator.split("/")
        response[make][manipulator_id] = await manipulator_state(make, manipulator_id)

    return dict(response)
