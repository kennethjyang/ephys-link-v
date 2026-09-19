import asyncio
from time import time

from ephys_link.models import TaskState

# Map of Task ID (UUID) -> Task State.
tasks: dict[str, TaskState] = {}

# Serializes every read-modify-write of the shared task table so that
# concurrent coroutines cannot interleave an update and clobber one
# another's changes.
_lock: asyncio.Lock = asyncio.Lock()


async def get_task(task_id: str) -> TaskState | None:
    """Return the state of a task.

    Returns None if the task ID doesn't exist. The lookup is performed
    under the shared lock so a concurrent mutation cannot swap the stored
    task out from under the read.

    Args:
        task_id: ID of the task to retrieve.

    Returns:
        The task state, or None if the task doesn't exist.
    """
    async with _lock:
        return tasks.get(task_id)


async def delete_task(task_id: str) -> None:
    """Delete a task.

    If the task ID doesn't exist, nothing will happen.

    Args:
        task_id: ID of the task to delete.
    """
    async with _lock:
        tasks.pop(task_id, None)


async def remove_manipulator(task_id: str, make: str, manipulator_id: str) -> bool:
    """Remove a manipulator from a task.

    If the task ID doesn't exist, nothing will happen.
    If the manipulator isn't in the task, nothing will change.

    Args:
        task_id: ID of the task to remove the manipulator from.
        make: Name of the manipulator to remove in kebab-case.
        manipulator_id: ID of the manipulator to remove.

    Returns:
        True if there are no more manipulators left in the task.
    """
    async with _lock:
        # Exit if the task doesn't exist.
        if task_id not in tasks:
            return False

        target_task = tasks[task_id]

        updated_manipulators = target_task.manipulators - {(make, manipulator_id)}

        tasks[task_id] = target_task.model_copy(
            update={"manipulators": updated_manipulators}
        )

        return len(updated_manipulators) == 0


async def set_message(task_id: str, message: str | None = None) -> None:
    """Set a message for a task.

    If the task ID doesn't exist, nothing will happen.

    Args:
        task_id: ID of the task to set the message to.
        message: Message to add to the task (None would remove it).
    """
    async with _lock:
        # Exit if the task doesn't exist.
        if task_id not in tasks:
            return

        target_task = tasks[task_id]
        tasks[task_id] = target_task.model_copy(update={"message": message})


async def end_task(task_id: str, message: str | None = None) -> None:
    """Marks a task as inactive and adds an optional message.

    If the task ID doesn't exist, nothing will happen.

    Args:
        task_id: ID of the task to mark as inactive.
        message: Optional message to add to the task.
    """
    async with _lock:
        # Exit if the task doesn't exist.
        if task_id not in tasks:
            return

        target_task = tasks[task_id]

        tasks[task_id] = target_task.model_copy(
            update={"time_ended": time(), "message": message}
        )
