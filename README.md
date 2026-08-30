# Ephys Link

Electrophysiology manipulator communication platform.

## Installation

1. Install UV.
2. Run uv sync to install the environment.
3. Run uv run lefthook install to set up hooks.

# Design Doc

Ephys Link V is a modern overhaul of [Ephys Link v2](https://github.com/VirtualBrainLab/ephys-link). This design doc is meant for humans and LLMs to read.

## Goals

Provide a simple service with a single API to control any electrophysiology manipulators. Maintainers of Ephys Link will provide first-party support for Sensapex uMp micromanipulators and New Scale manipulators.

This is achieved through these design decisions:

1. HTTP REST API: very basic communication protocol that does not require additional dependencies for most platforms.
2. Stateless API: connections are ephemeral making crashes or disconnects meaningless.
3. Minimal manipulator binding interface that also allows for custom features to be implemented.

Ephys Link's service is client agnostic (anyone can use its API), but is primarily motivated to serve [Pinpoint V](https://github.com/AllenNeuralDynamics/pinpoint).

## Architecture

Ephys Link is organized a lot like a database service. There is a client-facing API that is stateless and allows for idempotent access and asynchronous messages, and there is a stateful backend that maintains connections to the manipulators and fulfills requests from clients. The server will receive client messages, parse/validate them, and then execute the desired behavior. Instead of registering manipulators from the client, on startup all found manipulators will have their bindings initialized and placed into a pool. From there the server endpoints will reach into that pool to execute the desired behavior. Bindings use a base class to enforce the correct shape and let the server run behaviors on a fixed API.

> [!NOTE]
> Unlike Ephys Link v2, Ephys Link V does not enforce a "unified coordinate system". Instead, it transparently maps input values in the order they are given to the XYZ+ coordinates in the platform's SDK directly. Client applications are the ones that should encode user plans to the correct axes for manipulators. This makes sense for Pinpoint V where the user can change coordinate system representation and have custom mappings between planning axes and manipulator axes.
>
> Another deviation from Ephys Link v2 is the removal of "inside brain" state. This is a responsibility of the client application. Ephys Link should only be a communication handler.

## Client API

Ephys Link creates a local HTTP server with the proper CORS configuration to enable another service to connect to it via a local IP. Similar to how [Vercel Serve](https://github.com/vercel/serve) creates a local file server accessible from any other client with access to the same network.

There are two types of messages: a **request** and a **task**.

- **Requests** are handled through `GET` routes and are idempotent.
- **Tasks** are handled through `PATCH` routes and are expected to be long running (i.e. moving a manipulator to a pose).

The FastAPI system will handle type checking and validation for inbound messages. The endpoints route to the bindings or provide an immediate response where applicable.

### Requests

Idempotent information retrieval from the server using `GET`.

| Route | Example | Returns |
| ----- | ------- | ------- |
| `/version` | | Ephys Link version. |
| `/manipulators` | | An array of all found manipulators. |
| `/{make}/{ID}` | `/sensapex/3` | An object with the current state of that manipulator. Returns 404 if that manipulator does not exist. |
| `/task/{ID}` | `/task/123e4567-e89b-12d3-a456-426614174000` | Polling endpoint for a task. Informs the state of the task or 404 if it's not running anymore. |

#### Manipulators

- Make ("Sensapex")
- Model ("uMp-4")
- Platform specific ID ("3")
- List of custom state fields
- List of custom function signatures (object with name and list of parameters and their type)

Reports the known manipulators by their make ("Sensapex"), model ("uMp-4"), and platform specific ID ("3"). Clients can use this to show a list of available manipulators to use. This information will be converted to kebab-case when used in routes.

> [!IMPORTANT]
> Manipulator ID's are expected to be unique within their make namespace.

Custom state and functionality is also documented here for client applications to read.

#### Manipulator State

- Make, model, ID
- Position
- Limits of each axes (the order is mapped to the native order of the platform's SDK and the number of values here indicate the number of axes)
- If it's moving (i.e. actively in a task)

> [!IMPORTANT]
> The contents of state information is dependent on the support of the platform.
>
> For example New Scale has no concept of orientation, and Sensapex uMp-4 only knows the depth axis angle. This is why orientation is not a required field.

Since this will be encoded as a JSON object in transit, additional custom fields can be added at the binding implementation. Pydantic type checking and model definitions will only validate against the required fields. Bindings should document these custom fields and share them with client applications via the `GET /manipulators` route.

#### Task State

- Time the task started
- List of manipulators involved
- Time the task ended
- Message (would be for reporting any errors)

The end time indicates if the task is still ongoing. It will be `null` while ongoing and then have a real value when done. The message field will describe the termination state (i.e. "Canceled").


### Tasks

Actions on the manipulators via `PATCH` routes.

| Route | Example | Input | Description |
| ----- | ------- | ----- | ------- |
| `/stop_all` | | | Stops all manipulator movement (any ongoing tasks). |
| `/stop/{make}/{ID}` | `/stop/sensapex/3` | | Stops a specific manipulator. |
| `/set-position/{make}/{ID}` | `/set-position/sensapex/3` | An array of positions for each axis. | Sets the manipulator to this exact translation state. |
| `/custom/{make}/{ID}` | `/custom/sensapex/3` | Arbitrary object. | Calls a custom command matched with duck typing. |


#### Task lifecycle

Each `PATCH` returns a task ID (some UUID). Tasks first add an entry into the task table with the list of manipulators involved. The message field can be updated as the task is being fulfilled. Clients poll the `GET /task/{ID}` route for the state of the task.

When a task is created, all ongoing tasks that use a manipulator in the current task is canceled. This implies running `/stop_all` will set all ongoing tasks to the canceled state (has an end time).

> [!IMPORTANT]
> Every manipulator should only be in **at most one** ongoing task at a time.

Tasks are set for removal once they stop (completion, error, or canceled). Their state message is set for errors or cancellation when they stop and then after a polling call is made (so someone read it) they are deleted from the task pool.

## Manipulator Binding Interface

Once messages are validated through the client API, the desired manipulator behavior is passed to the binding system. A base interface is defined to ensure the required commands have bindings, however bindings can have more functions that are name-mapped for the custom `PATCH` route. A separate binding does not necessarily need to be made for each model of a manufacturer. For example, Sensapex uMp-4 and uMp-3 can be accessed via the same SDK so they only need one manipulator binding.

| Function | Inputs | Outputs | Description |
| -------- | ------ | ------- | ----------- |
| `current_state` | Manipulator to pull data for. | Manipulator state object. | Response for `GET /{make}/{ID}` |
| `stop` | Manipulator to stop. | Stops manipulator movement and updates task. | Stop a specific manipulator's movement. |
| `stop_all` | | Stops all manipulators in this binding and updates tasks. | Calls `stop` on all manipulators in this binding. |
| `set_position` | Manipulator and pose | Triggers movement and updates task. | Attempts to move the manipulator into the desired pose. |


### Custom state and behavior

Current state has required fields to return but additional custom state information can be added as additional fields. It's all JSON encoded at the end of the day. Bindings should document these additional fields for client applications to read.

Custom platform-specific functions are called through duck typing and are identified by the function name and arguments as passed in a generic object by the `PATCH /custom/{make}/{ID}` route. For example, Sensapex has a custom "jackhammer mode" with special instructions that can be passed via this custom command.

### Stopping logic

Once manipulator movement is stopped, it is also removed from the task it was in. If it was the only manipulator in that task then the task is canceled (don't actually remove the manipulator from the task in this case).

### Movement logic

The task state should be updated with the progress of the moment. This means the binding should have some indication of whether the manipulator achieved the goal pose or if it was off. A goal pose that is not reached is considered a failure and should be reported as such.

> [!IMPORTANT]
> If the binding can determine that the movement is impossible it must terminate the movement early.

## Code Organization and Implementation

Ephys Link is a Python _application_ meaning it is organized to be a standalone service and not a library installed via PyPI. Python is chosen for its extensive infrastructure and for ease-of-use. This will be useful for future contributing manufacturers to add bindings for their platform.

The HTTP REST API is implemented via **FastAPI**. The data models are defined using **Pydantic**. Model and API JSON schemas can be exposed so client applications can build compatible interfaces.

Implementation should focus on idiomatic practices over high-performance tweaks.

The program starts with the `main.py` script at the root of the repository with all other code organized under the `ephys_link` package (namespace). Standalone and singleton functionality should use module-level implementation. The bindings should inherit from be an abstract base class that enforces the required functions in the binding. Binding implementations should be located in the `ephys_link/bindings` package. Message models and other data models should be implemented under the `ephys_link/models` package. Models are grouped together by use (i.e. a `request_models.py` holds the request message models).

All functions should aim to be pure (takes in inputs and returns outputs). This will make testing easier and help with the API pipeline structure. Binding functions should be pure where possible, however manipulator side effects is expected.

All runtime errors should be caught to prevent permanent server crashes. Instead, error should be notified via the message response in tasks or the route feedback (if the error is at the route endpoint).
