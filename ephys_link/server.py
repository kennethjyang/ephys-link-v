from collections import defaultdict
from time import time
from typing import Annotated
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Query

from ephys_link.manipulators import find_manipulators, manipulators
from ephys_link.models import (
    ManipulatorStateResponse,
    ServerStateResponse,
    SetPositionPayload,
    SetPositionResponse,
    TaskState,
)
from ephys_link.tasks import tasks

# Configure API server.
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def server_state() -> ServerStateResponse:
    """Return the server state and known manipulators."""
    return ServerStateResponse(
        server_version="5.1.0-dev1",
        manipulators=[
            manipulator.info()
            for make in manipulators.values()
            for manipulator in make.values()
        ],
    )


@app.get("/find")
async def find() -> ServerStateResponse:
    """Prompt the server to find manipulators again and return the server state."""
    await find_manipulators()
    return server_state()


@app.get("/{make}/{manipulator_id}")
async def manipulator_state(make: str, manipulator_id: str) -> ManipulatorStateResponse:
    """Query the state of a manipulator.

    Args:
        make: Manufacturer of the manipulator in kebab-case
        manipulator_id: Manipulator ID. Must be unique to the make namespace.
    Returns:
        Manipulator state or 404 if the manipulator wasn't found at startup
        and 503 if there was a problem getting the state.
    """
    try:
        return await manipulators[make][manipulator_id].state()
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Manipulator {make} {manipulator_id} not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Manipulator state could not be retrieved: {e}."
        )


@app.get("/state")
async def manipulator_states(
    manipulators_requested: Annotated[
        list[str], Query(alias="manipulator", min_length=1)
    ],
) -> dict[str, dict[str, ManipulatorStateResponse]]:
    """Query the state of multiple manipulators.

    Args:
        manipulators_requested: List of manipulators to query formatted as "{make}/{manipulator_id}".
    Returns:
        Nested object with each manipulator's state requested in Make -> ID -> State format.
        Will immediately terminate if one of the requested manipulators fail to report state.
        Will return 400 if the identifier pair was malformed.
    """
    response = defaultdict(dict)
    for manipulator in manipulators_requested:
        try:
            make, manipulator_id = manipulator.split("/")
            response[make][manipulator_id] = await manipulator_state(
                make, manipulator_id
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f'Malformed manipulator identifier pair "{manipulator}".',
            )

    return dict(response)


@app.get("/task/{task_id}")
def task_state(task_id: str) -> TaskState:
    """Retrieves the state of a task.

    Removes completed tasks after reading.

    Args:
        task_id: Task ID.
    Returns:
        Task state or 404 if the task doesn't exist,
        503 if there was a problem getting the task.
    """
    try:
        requested_task = tasks[task_id]

        # Remove the task if it has ended.
        if not requested_task.time_ended:
            del tasks[task_id]

        return requested_task
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Task {task_id} could not be retrieved: {e}."
        )


@app.put("/stop-manipulator/{make}/{manipulator_id}")
async def stop_manipulator(make: str, manipulator_id: str):
    """Stops a manipulator and updates associated task.
    Args:
        make: Manufacturer of the manipulator in kebab-case.
        manipulator_id: Manipulator ID. Must be unique to the make namespace.
    Returns:
        200 if it worked,
        404 if the manipulator wasn't found,
        and 503 if there was a problem stopping the manipulator.
    """
    try:
        # Stop the manipulator.
        await manipulators[make][manipulator_id].stop()

        # Remove manipulator from its task.
        task_id = manipulators[make][manipulator_id].task_id

        # Exit if there wasn't a task attached (i.e. it was already stopped).
        if not task_id:
            return

        # Remove manipulator from task.
        associated_task = tasks[task_id]
        final_manipulators = associated_task.manipulators - {(make, manipulator_id)}

        # Also cancel the task if all manipulators removed.
        if len(final_manipulators) == 0:
            tasks[task_id] = associated_task.model_copy(
                update={"manipulators": {}, "time_ended": time(), "message": "Stopped."}
            )
        else:
            tasks[task_id] = associated_task.model_copy(
                update={"manipulators": final_manipulators}
            )

        # Remove task from manipulator.
        manipulators[make][manipulator_id].task_id = None

    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Manipulator {make} {manipulator_id} not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to stop manipulator {make} {manipulator_id}: {e}.",
        )


@app.put("/stop-task/{task_id}")
async def stop_task(task_id: str):
    """Stops all manipulators in a task.

    Args:
        task_id: Task ID to stop.
    Returns:
        200 if it worked,
        404 if the task or manipulator wasn't found,
        and 503 if there was a problem stopping the task.
    """
    try:
        requested_task = tasks[task_id]

        # Exit if already stopped.
        if requested_task.time_ended:
            return

        for make, manipulator_id in requested_task.manipulators:
            await stop_manipulator(make, manipulator_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")


@app.put("/stop-all")
async def stop_all():
    """Stops all tasks.

    Returns:
        200 if it worked and 404 or 503 if there was a problem stopping the tasks.
    """
    for task_id in manipulators:
        await stop_task(task_id)


@app.put("/set-position/{make}/{manipulator_id}")
async def set_position(
    make: str,
    manipulator_id: str,
    payload: SetPositionPayload,
    background_task: BackgroundTasks,
):
    """Sets the position of a manipulator.

    Args:
        make: Manufacturer of the manipulator in kebab-case.
        manipulator_id: Manipulator ID. Must be unique to the make namespace.
        payload: Set position task payload.
        background_task: Background task system to launch movement in.
    Returns:
        Task ID on successful creation,
        404 if the manipulator wasn't found,
        and 503 if there was a problem creating the task.
    """
    try:
        associated_manipulator = manipulators[make][manipulator_id]

        # Create task.
        task = TaskState(time_started=time(), manipulators={(make, manipulator_id)})
        task_id = str(uuid4())
        tasks[task_id] = task

        # Schedule movement.
        background_task.add_task(
            associated_manipulator.set_position,
            payload.position,
            payload.speed,
            task_id,
        )

        return SetPositionResponse(task_id=task_id)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Manipulator {make} {manipulator_id} not found."
        )
