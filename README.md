# Ephys Link

Electrophysiology manipulator communication platform.

## Installation

1. Install UV.
2. Run uv sync to install the environment.
3. Run uv run lefthook install to set up hooks.

# Design Doc

Ephys Link V is a modern overhaul of [Ephys Link v2](https://github.com/VirtualBrainLab/ephys-link). This design doc is
meant for humans and LLMs to read.

## Goals

Provide a simple service with a single API to control any electrophysiology manipulators. Maintainers of Ephys Link will
provide first-party support for Sensapex uMp micromanipulators and New Scale manipulators.

This is achieved through these design decisions:

1. HTTP REST API: a very basic communication protocol that does not require additional dependencies for most platforms.
2. Stateless API: connections are ephemeral, making crashes or disconnects meaningless.
3. Minimal manipulator binding interface that also allows for custom features to be implemented.

Ephys Link's service is client-agnostic (anyone can use its API), but is primarily motivated to
serve [Pinpoint V](https://github.com/AllenNeuralDynamics/pinpoint).

## Architecture

Ephys Link is organized a lot like a database service. There is a client-facing API that is stateless, supports
idempotent access, and enables asynchronous messages, and there is a stateful backend that maintains connections to the
manipulators and fulfills client requests. The server will receive client messages, parse/validate them, and then
execute the desired behavior. Instead of registering manipulators from the client, on startup all found manipulators
will have their bindings initialized and placed into a pool. From there, the server endpoints will reach into that pool
to execute the desired behavior. Bindings use a base class to enforce the correct shape and let the server run behaviors
on a fixed API.

> [!NOTE]
> Unlike Ephys Link v2, Ephys Link V does not enforce a "unified coordinate system". Instead, it transparently maps
input values, in the order they are given, directly to the XYZ+ coordinates in the platform's SDK. Client applications
are the ones that should encode user plans to the correct axes for manipulators. This makes sense for Pinpoint V, where
the user can change coordinate system representation and have custom mappings between planning axes and manipulator
axes.
>
> Another deviation from Ephys Link v2 is the removal of the "inside brain" state. This is a responsibility of the
client application. Ephys Link should only be a communication handler.

## Client API

Ephys Link creates a local HTTP server with the proper CORS configuration to enable another service to connect to it via
a local IP. Similar to how [Vercel Serve](https://github.com/vercel/serve) creates a local file server accessible from
any other client with access to the same network.

There are two types of messages: a **request** and a **task**.

- **Requests** are handled through `GET` routes and are idempotent.
- **Tasks** are handled through `PUT` routes and are expected to be long-running (i.e., moving a manipulator to a pose).

> [!TIP]
> `PUT` is used instead of `POST` or `PATCH` since all routes modify the _entire_ manipulator state (which is really
just position) rather than _add_ a manipulator state/object (`POST`) or mutate a portion of it (`PATCH`).

The FastAPI system will handle type checking and validation for inbound messages. The endpoints route to the bindings or
provide an immediate response where applicable.

### Requests

Idempotent information retrieval from the server using `GET`.

| Route                      | Example                                       | Returns                                                                                                |
|---------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `/`                        |                                               | Report server version and an array of all found manipulators.                                          |
| `/find`                    |                                               | Search for manipulators again.                                                                         |
| `/state/{make}/{manipulator_id}` | `/state/sensapex/3`                      | An object with the current state of that manipulator. Returns 404 if that manipulator does not exist. |
| `/states?manipulator={make}/{id}` | `/states?manipulator=sensapex/3`        | An array of manipulator states based on the request. Supports filtering by make and ID.                |
| `/task/{task ID}`          | `/task/123e4567-e89b-12d3-a456-426614174000` | Polling endpoint for a task. Informs the state of the task or returns 404 if it's no longer running.   |
### Tasks
#### Manipulators

Details the information about a particular manipulator.

- Make ("Sensapex")
- Model ("uMp-4")
- Platform-specific ID ("3")
- Limits of each axis (the order is mapped to the native order of the platform's SDK, and the number of values here indicates the number of axes)
- List of custom state fields
- List of custom function signatures (object with name and list of parameters and their type)

Reports the known manipulators as part of the server state response at `/`. The response includes an array of `ManipulatorInfo` objects with make, model, id, axis_limits, custom_properties, and custom_functions. Clients can use this to show a list of available manipulators to use. This information will be converted to kebab-case when used in routes.

> [!IMPORTANT]
> Manipulator ID's are expected to be unique within their make namespace.

Custom state and functionality are also documented in the response for client applications to read.

#### Manipulator State

- Current position (in millimeters)
- Current active task ID

> [!IMPORTANT]
> All position units must be standardized to millimeters. Clients are expected to read and write in millimeters.

Having an active task ID means the manipulator is moving. Once cleared the manipulator is no longer moving, however the task may not be completed.

The contents of state information depend on the support of the platform. For example, New Scale has no concept of orientation, and Sensapex uMp-4 only knows the depth axis angle. This is why orientation is not a required field. Since this will be encoded as JSON at transit, additional custom fields can be added at the binding implementation. Bindings should document these custom fields for client applications to read.

Pydantic type checking and model definitions validate against required fields. The `ManipulatorStateResponse` includes position (list of floats), active_task_id, custom_properties, and custom_functions. For clients that frequently request the state of multiple manipulators, they can use `GET /states?manipulator={make}/{id}` to more efficiently get the state of multiple manipulators with one call. If a manipulator's state is unavailable, it will be omitted from the response. Client applications should understand this means there was a problem getting the manipulator's state (like a 404).

Note: Custom properties are retrieved as `__dunder__` methods in the binding implementation (e.g., `__custom_property__`). These must start and end with double underscores. Custom functions are called through duck typing and are identified by the function name and arguments as passed in a generic object by the `PUT /custom/{make}/{ID}` route.


### Custom State and Behavior

The current state has required fields to return, but additional custom state information can be added as additional
fields. It's all JSON encoded at the end of the day. Bindings should document these additional fields for client
applications to read.

Custom platform-specific functions are called through duck typing and are identified by the function name and arguments
as passed in a generic object by the `PUT /custom/{make}/{ID}` route. For example, Sensapex has a custom "jackhammer
mode" with special instructions that can be passed via this custom command.

### Stopping Logic

Once manipulator movement is stopped, it is also removed from the task it was in. If it was the only manipulator in that
### Tasks

Actions on the manipulators via `PUT` routes.

| Route                            | Example                                       | Input                                             | Description                                             |
|---------------------------------|----------------------------------------------|--------------------------------------------------|--------------------------------------------------------|
| `/stop-manipulator/{make}/{ID}` | `/stop-manipulator/sensapex/3`                |                                                   | Stops a specific manipulator.                           |
| `/stop-task/{task ID}`           | `/stop-task/123e4567-e89b-12d3-a456-426614174000` |                                                   | Stops all manipulators in a task.                       |
| `/stop-all`                      |                                               |                                                   | Stops all manipulator movement (any ongoing tasks).     |
| `/set-position/{make}/{ID}`      | `/set-position/sensapex/3`                    | Position and speed.                               | Sets the manipulator to this exact translation state.   |
| `/set-positions`                 |                                               | Position and speed for each manipulator to move. | Sets each manipulator to this exact translation state.  |
| `/custom/{make}/{ID}`            | `/custom/sensapex/3`                          | Arbitrary object.                                 | Calls a custom command matched with duck typing.        |

#### Task Lifecycle

Each `PUT` returns a task ID (some UUID). Tasks first add an entry into the task table with the list of manipulators involved. The message field can be updated as the task is being fulfilled. Clients poll the `GET /task/{ID}` route for the state of the task.

When a task is created, all ongoing tasks that use a manipulator in the current task are canceled (the task ends but not marked as canceled; it just clears its manipulators from the pool). This implies that running `/stop_all` will set all ongoing tasks to end state (has an end time).

> [!IMPORTANT]
> Every manipulator can only be in **at most one** ongoing task at a time.

Implementation should focus on idiomatic practices over high-performance tweaks.
## Manipulator Binding Interface

Once messages are validated through the client API, the desired manipulator behavior is passed to the binding system. A base interface is defined to ensure the required commands have bindings; however, bindings can have more functions that are name-mapped for the custom `PUT` route. A separate binding does not necessarily need to be made for each model of a manufacturer. For example, Sensapex uMp-4 and uMp-3 can be accessed via the same SDK, so they only need one manipulator binding.

| Function          | Inputs                          | Outputs                                                     | Description                                               |
|-----------------|-------------------------------|-----------------------------------------------------------|---------------------------------------------------------|
| `info`            |                                 | `ManipulatorInfo` object.                                    | Intrinsic manipulator info (make, model, id, axis_limits). Used for endpoint discovery. |
| `get_position`    | Manipulator to pull data for. | List of floats representing absolute position in mm.        | Returns the axis-order absolute position of the manipulator. Used internally by `state()` method. |
| `state`            |                                 | `ManipulatorStateResponse` object.                          | Returns the current state including position and active_task_id. Used for `GET /state/{make}/{ID}` endpoint. |
| `set_position`    | Manipulator, position, speed, task_id | Triggers movement and updates task.                     | Attempts to move the manipulator into the desired pose. Used for `PUT /set-position/{make}/{ID}` endpoint. |
| `stop`            |                                 | Stops manipulator movement.                                  | Stop a specific manipulator's movement. Used internally by `PUT /stop-manipulator/{make}/{ID}` endpoint. |
| `stop_all`         |                                 | Stops all manipulators in this binding.                     | Calls `stop` on all manipulators via the binding.        |

### Custom State and Behavior

The current state has required fields to return, but additional custom state information can be added as additional fields. It's all JSON encoded at the end of the day. Bindings should document these additional fields for client applications to read.

Custom platform-specific functions are called through duck typing and are identified by the function name and arguments as passed in a generic object by the `PUT /custom/{make}/{ID}` route. For example, Sensapex has a custom "jackhammer mode" with special instructions that can be passed via this custom command.

### Stopping Logic

Once manipulator movement is stopped, it is also removed from the task it was in. If it was the only manipulator in that task, then the task is marked as ended (without a cancel message).

### Movement Logic

The task state should be updated with the progress of the moment. This means the binding should have some indication of whether the manipulator achieved the goal pose or if it was off. A goal pose that is not reached is considered a failure and should be reported as such.

> [!IMPORTANT]
> If the binding can determine that the movement is impossible, it must terminate the movement early.

## Code Organization and Implementation

Ephys Link is a Python _application_, meaning it is organized to be a standalone service and not a library installed via PyPI. Python is chosen for its extensive infrastructure and for ease of use. This will be useful for future contributing manufacturers to add bindings for their platform.

The HTTP REST API is implemented via **FastAPI**. The data models are defined using **Pydantic** in a single `models.py` file. Model JSON schemas can be exposed so client applications can build compatible interfaces. Implementation should focus on idiomatic practices over high-performance tweaks.

The program starts with the `main.py` script at the root of the repository, with all other code organized under the `ephys_link` package (namespace). Standalone and singleton functionality should use module-level implementation. The bindings should inherit from an abstract base class that enforces the required functions in the binding. Binding implementations should be located in the `ephys_link/bindings` package. Message models and other data models are defined in the single `ephys_link/models.py` file.

All functions should aim to be pure (take in inputs and return outputs). This will make testing easier and help with the API pipeline structure. Binding functions should be pure where possible; however, manipulator side effects are expected.

All runtime errors should be caught to prevent permanent server crashes. Instead, errors should be notified via the message response in tasks or the route feedback (if the error is at the route endpoint).
