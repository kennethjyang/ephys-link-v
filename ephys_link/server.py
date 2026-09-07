from fastapi import FastAPI, HTTPException

from ephys_link.manipulators import manipulators
from ephys_link.models import ManipulatorStateResponse, ServerStateResponse

app = FastAPI()


@app.get("/")
async def server_state() -> ServerStateResponse:
    return ServerStateResponse(server_version="5.1.0-dev1", manipulators=[])


@app.get("/{make}/{manipulator_id}")
async def manipulator_state(make: str, manipulator_id: int) -> ManipulatorStateResponse:
    key = f"{make}:{manipulator_id}"
    try:
        return manipulators[key].state()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Manipulator {key} not found")
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Manipulator state could not be retrieved: {e}"
        )
