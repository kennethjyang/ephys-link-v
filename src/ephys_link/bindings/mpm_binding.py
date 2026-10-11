from __future__ import annotations

import asyncio
from typing import Any, override

import httpx

from ephys_link.base_binding import BaseBinding
from ephys_link.models import ManipulatorInfo, ManipulatorStateResponse
from ephys_link.tasks import end_task, remove_manipulator, set_message

# Valid manipulator IDs for the New Scale Pathfinder MPM (28 channels).
VALID_MANIPULATOR_IDS: tuple[str, ...] = tuple(
    f"{chr(i)}" for i in range(ord("A"), ord("A") + 28)
)

# Server data update rate (30 Hz polling interval).
SERVER_DATA_UPDATE_RATE: float = 1 / 30

# Number of consecutive unchanged readings before declaring stuck.
UNCHANGED_COUNTER_LIMIT: int = 10

# Movement tolerance in mm for "reached" check.
MOVEMENT_TOLERANCE: float = 0.01

# Speed threshold (mm/s): above uses fine step mode (0), below uses coarse (1).
COARSE_SPEED_THRESHOLD: float = 0.1


class MPMBinding(BaseBinding):
    """Binding for the New Scale Pathfinder MPM HTTP server."""

    def __init__(self, manipulator_id: str, port: int = 8080) -> None:
        super().__init__(manipulator_id)
        self._port = port
        self._client = httpx.AsyncClient(
            base_url=f"http://localhost:{port}",
            timeout=10.0,
        )
        self._probe_index: int = self._get_probe_index()

    def _get_probe_index(self) -> int:
        """Resolve manipulator_id to zero-based index from VALID_MANIPULATOR_IDS."""
        try:
            return VALID_MANIPULATOR_IDS.index(self.manipulator_id)
        except ValueError:
            raise ValueError(
                f"Invalid MPM manipulator_id {self.manipulator_id!r}. "
                f"Must be one of {VALID_MANIPULATOR_IDS}."
            )

    @override
    def info(self) -> ManipulatorInfo:
        return ManipulatorInfo(
            make="New Scale",
            model="Pathfinder MPM",
            id=self.manipulator_id,
            axis_limits=[(0.0, 15.0), (0.0, 15.0), (0.0, 15.0)],
            custom_properties={"angles", "shankCount"},
        )

    # ---- private HTTP helpers --------------------------------------------

    async def _query_data(self) -> dict[str, Any]:
        """GET / — returns ProbeArray + PosteriorAngle."""
        resp = await self._client.get("/")
        resp.raise_for_status()
        return resp.json()

    async def _put_request(self, body: dict[str, Any]) -> None:
        """PUT / with a JSON body."""
        resp = await self._client.put("/", json=body)
        resp.raise_for_status()

    # ---- public API ------------------------------------------------------

    @override
    async def get_position(self) -> list[float]:
        data = await self._query_data()
        probe_array = data.get("ProbeArray", [])
        probe = probe_array[self._probe_index]
        return [
            float(probe["Stage_X"]),
            float(probe["Stage_Y"]),
            float(probe["Stage_Z"]),
        ]

    @override
    async def state(self) -> ManipulatorStateResponse:
        """Override to include angles and shankCount custom properties."""
        data = await self._query_data()
        probe_array = data.get("ProbeArray", [])
        probe = probe_array[self._probe_index]

        # Extract angle values.
        polar: float = float(probe.get("Polar", 0.0))
        pitch: float = float(probe.get("Pitch", 0.0))
        shank_orientation: float = float(probe.get("ShankOrientation", 0.0))
        shank_count: int = int(probe.get("ShankCount", 0))

        # Compute adjusted polar.
        posterior_angle: float = float(data.get("PosteriorAngle", 0.0))
        adjusted_polar = (polar - posterior_angle) % 360

        position = [
            float(probe["Stage_X"]),
            float(probe["Stage_Y"]),
            float(probe["Stage_Z"]),
        ]

        return ManipulatorStateResponse(
            position=position,
            active_task_id=self.task_id,
            angles={
                "polar": adjusted_polar,
                "pitch": pitch,
                "shankOrientation": shank_orientation,
            },
            shank_count=shank_count,
        )

    @override
    async def set_position(
        self, position: list[float], speed: float, task_id: str
    ) -> None:
        try:
            self.task_id = task_id

            await set_message(
                task_id,
                f"Sending movement to MPM {self.manipulator_id}.",
            )

            # Set step mode: fine (0) if speed > threshold, coarse (1) otherwise.
            step_mode = 0 if speed > COARSE_SPEED_THRESHOLD else 1
            await self._put_request(
                {
                    "PutId": "ProbeStepMode",
                    "Probe": self._probe_index,
                    "StepMode": step_mode,
                }
            )

            # Send absolute motion command.
            await self._put_request(
                {
                    "PutId": "ProbeMotion",
                    "Probe": self._probe_index,
                    "Absolute": 1,
                    "Stereotactic": 0,
                    "AxisMask": 7,
                    "X": position[0],
                    "Y": position[1],
                    "Z": position[2],
                }
            )

            await set_message(
                task_id,
                f"Movement sent to MPM {self.manipulator_id}. Waiting for completion...",
            )

            # Poll until position is reached or error.
            unchanged_count = 0
            previous: list[float] | None = None
            target = position

            while True:
                current = await self.get_position()

                # Check if reached.
                if all(
                    abs(current[i] - target[i]) <= MOVEMENT_TOLERANCE for i in range(3)
                ):
                    await set_message(
                        task_id,
                        f"MPM {self.manipulator_id} movement FINISHED.",
                    )
                    break

                # Check if stuck (position unchanged across polls).
                if previous is not None and current == previous:
                    unchanged_count += 1
                else:
                    unchanged_count = 0

                if unchanged_count >= UNCHANGED_COUNTER_LIMIT:
                    await set_message(
                        task_id,
                        f"MPM {self.manipulator_id} movement STUCK.",
                    )
                    break

                previous = current
                await asyncio.sleep(SERVER_DATA_UPDATE_RATE)

        except Exception as e:
            await set_message(
                task_id,
                f"MPM {self.manipulator_id} movement failed: {e}",
            )
        finally:
            if await remove_manipulator(task_id, "new-scale-mpm", self.manipulator_id):
                await end_task(task_id, "Completed")

            self.task_id = None

    @override
    async def stop(self) -> bool:
        await self._put_request(
            {
                "PutId": "ProbeStop",
                "Probe": self._probe_index,
            }
        )
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
