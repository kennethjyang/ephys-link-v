from fastapi import FastAPI

from ephys_link.models import ManipulatorStateResponse, ServerStateResponse

app = FastAPI()


@app.get("/")
async def server_state() -> ServerStateResponse:
    return ServerStateResponse(server_version="5.1.0-dev1", manipulators=[])


@app.get("/{make}/{id}")
async def manipulator_state(make: str, id: int) -> ManipulatorStateResponse:
    return ManipulatorStateResponse(make=make, id=id)
