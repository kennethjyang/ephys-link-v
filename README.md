# Ephys Link

Electrophysiology manipulator communication platform.

## Installation

1. Install UV.
2. Run uv sync to install the environment.
3. Run uv run lefthook install to set up hooks.

# Design Doc

Ephys Link V is a modern overhaul of [Ephys Link v3](https://github.com/VirtualBrainLab/ephys-link). This design doc is meant for humans and LLMs to read.

## Goals

Provide a simple service with a single API to control any electrophysiology manipulators. Maintainers of Ephys Link will provide first-party support for Sensapex uMp micromanipulators and New Scale manipulators.

This is achieved through these design decisions:

1. HTTP REST API: very basic communication protocol that does not require additional dependencies for most platforms.
2. Stateless API: connections are ephemeral making crashes or disconnects meaningless.
3. Enforceable "minimum" manipulator binding interface that allows for custom features to be access outside of the standard API.

Ephys Link is a Python _application_ meaning it is organized to be a standalone service and not a library installed via PyPI. Python is chosen for the extensive infrastructure and for ease-of-use (especially for future manufacturers to add bindings for their platform).

Ephys Link's service is client agnostic (anyone can use its API), but is primarily motivated to serve [Pinpoint V](https://github.com/AllenNeuralDynamics/pinpoint).

## Architecture

Ephys Link is organized a lot like a database service. There is a client-facing API that is stateless and allows for idempotent access and asynchronous requests, and there is a stateful backend that maintains connections to the manipulators and fulfills requests from clients. The server will recieve client messages, parse/validate them, and then execute the desired behavior. Instead of registering manipulators from the client, on startup all found manipulators have their bindings initialized and placed into a pool. From there the server endpoints will reach into the pool to execute the desired behavior. Bindings use a base class to enforce the correct shape and let the server run behaviors on a fixed API.

Unlike Ephys Link v3, Ephys Link V does not enforce a "unified coordinate system". Instead, it transparently maps input values in the order they are given to the XYZ+ coordinates in the platform's SDK directly. Client applications, which would be responsible for user interactions, are the ones that should encode user plans to the correct axes. This makes sense for Pinpoint V where the user can change coordinate system representation which can dramatically affect how axes map to manipulators.

Another deviation from Ephys Link v3 is the removal of "inside brain" state. This is a responsibility of the client application. Ephys Link should only be a communication handler.

## Client API

Ephys Link creates a local HTTP server with the proper CORS configuration to enable another service to connect to it via a local IP. Similar to how [Vercel Serve](https://github.com/vercel/serve) creates a local file server accessible from any other client with access to the same network.

There are two types of messages: a **request** and a **task**. **Requests** are handled through `GET` routes and are idempotent. **Tasks** are handled through `PATCH` routes and are expected to be long running (i.e. moving a manipulator to a pose).

### `GET` Routes

Idempotent information retrieval from the server.

| Route | Example | Returns |
| ----- | ------- | ------- |
| `/version` | | Ephys Link version. |
| `/manipulators` | | An array with each manipulator's manufacturer and its ID (the manufacturer is its ID namespace). |
| `/{manufacturer}/{ID}` | `/sensapex/3` | An object with the current state of that manipulator. Returns 404 if that manipulator does not exist. |
| `/task/{ID}` | `/task/123e4567-e89b-12d3-a456-426614174000` | Polling endpoint for a task. Informs the state of the task or 404 if it's not running anymore. |

#### Manipulator State

The `GET` route for a manipulator returns a lot of information about the manipulator.

- Position
- Orientation
- If it's moving (i.e. actively in a task).
- Limits of each axes (the order is mapped to the native order of the platform's SDK and the number of values here indicate the number of axes).

#### Task State

The `GET` route for a task allows client applications to poll it state and react accordingly.

- Time the task started.
- List of manipulators involved.
- Time the task ended.
- Message (would be for reporting any errors).


### `PATCH` Routes

Actions on the manipulators.

| Route | Example | Input | Description |
| ----- | ------- | ----- | ------- |
| `/stop_all` | | | Stops all manipulator movement (any ongoing tasks). |
| `/stop/{manufacturer}/{ID}` | `/stop/sensapex/3` | | Stops a specific manipulator. |
| `/set_position/{manufacturer}/{ID}` | `/set_position/sensapex/3` | An array of positions for each axis. | Sets the manipulator to this exact translation state. |


#### Task lifecycle

Each patch returns a task ID (some UUID). Tasks create their entry into the task table with the list of manipulators involved. The message field can be updated as the task is being fulfilled. Clients poll the `/task/{ID}` `GET` route for the state of the task.

When a task is created, all ongoing tasks that use a manipulator in the current task is canceled. Every manipulator should only be in at most one ongoing task at a time. This implies running `/stop_all` will clear the ongoing task table by canceling everything.

Tasks are set for removal once they stop (completion, error, or canceled). Their state message is set for errors or cancellation when they stop and then after a polling call is made (so something read it) they are deleted.
