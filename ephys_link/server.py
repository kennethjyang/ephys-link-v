from fastapi import FastAPI, HTTPException

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
