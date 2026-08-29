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
3. Enforceable "minimum" manipulator interface that allows for custom features to be access outside of the standard API.

Ephys Link is a Python _application_ meaning it is organized to be a standalone service and not a library installed via PyPI. Python is chosen for the extensive infrastructure and for ease-of-use (especially for future manufacturers to add implementations).

Ephys Link's service is platform agnostic, but is primarily motivated to serve [Pinpoint V](https://github.com/AllenNeuralDynamics/pinpoint).

## Architecture

Ephys Link is organized a lot like a database service. There is a client-facing API that is stateless and allows for idempotent access and asynchronous requests, and there is a stateful backend that maintains connections to the manipulators and fulfills requests from clients.

### Client API

Ephys Link creates a local HTTP server with the proper CORS configuration to enable another service to connect to it via a local IP. Similar to how [Vercel Serve](https://github.com/vercel/serve) creates a local file server accessible from any other client with access to the same network.
