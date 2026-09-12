from time import time

from ephys_link.models import TaskState

# Map of Task ID (UUID) -> Task State.
tasks: dict[str, TaskState] = {}


def remove_manipulator(task_id: str, make: str, manipulator_id: str) -> bool:
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
    # Exit if the task doesn't exist.
    if task_id not in tasks:
        return False

    target_task = tasks[task_id]

    updated_manipulators = target_task.manipulators - {(make, manipulator_id)}

    tasks[task_id] = target_task.model_copy(
        update={"manipulators": updated_manipulators}
    )

    return len(updated_manipulators) == 0


def set_message(task_id: str, message: str | None = None) -> None:
    """Set a message for a task.

    If the task ID doesn't exist, nothing will happen.

    Args:
        task_id: ID of the task to set the message to.
        message: Message to add to the task (None would remove it).
    """
    # Exit if the task doesn't exist.
    if task_id not in tasks:
        return

    target_task = tasks[task_id]
    tasks[task_id] = target_task.model_copy(update={"message": message})


def end_task(task_id: str, message: str | None = None):
    """Marks a task as inactive and adds an optional message.

    If the task ID doesn't exist, nothing will happen.

    Args:
        task_id: ID of the task to mark as inactive.
        message: Optional message to add to the task.
    """
    # Exit if the task doesn't exist.
    if task_id not in tasks:
        return

    target_task = tasks[task_id]

    tasks[task_id] = target_task.model_copy(
        update={"time_ended": time(), "message": message}
    )
