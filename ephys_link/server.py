from fastapi import FastAPI

from ephys_link.models import ServerStateResponse

app = FastAPI()


@app.get("/")
async def server_state() -> ServerStateResponse:
    return ServerStateResponse(server_version="5.1.0-dev1", manipulators=[])
