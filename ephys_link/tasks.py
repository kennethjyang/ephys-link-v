from ephys_link.models import TaskState

# Map of Task ID (UUID) -> Task State.
tasks: dict[str, TaskState] = {}


def add_manipulator(task_id: str, make: str, manipulator_id: str) -> None:
    """Add a manipulator to a task.

    If the manipulator is already present in the task, nothing will change.

    Args:
        task_id: ID of the task to add the manipulator to.
        make: Name of the manipulator to add in kebab-case.
        manipulator_id: ID of the manipulator to add.
    """
    target_task = tasks[task_id]

    updated_manipulators = target_task.manipulators | {(make, manipulator_id)}

    tasks[task_id] = target_task.model_copy(
        update={"manipulators": updated_manipulators}
    )


def remove_manipulator(task_id: str, make: str, manipulator_id: str) -> bool:
    """Remove a manipulator from a task.

    If the manipulator isn't in the task, nothing will change.

    Args:
        task_id: ID of the task to remove the manipulator from.
        make: Name of the manipulator to remove in kebab-case.
        manipulator_id: ID of the manipulator to remove.

    Returns:
        True if there are no more manipulators left in the task.
    """
    target_task = tasks[task_id]

    updated_manipulators = target_task.manipulators - {(make, manipulator_id)}

    tasks[task_id] = target_task.model_copy(
        update={"manipulators": updated_manipulators}
    )

    return len(updated_manipulators) == 0
