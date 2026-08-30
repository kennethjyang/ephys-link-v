# Pinpoint V (v5.1) Manipulator Design Doc.

Pinpoint V (v5.1) will reintroduce electrophysiology manipulator integration for visualization and automation. It is designed specifically to integrate with Ephys Link V (v5.1). This design doc is meant for humans and LLMs to read.

## Goals

- Manipulator should be a first-class entity like probes and is a distinct concept from them.
- Manipulators bodies should be visualized in the scene with both 3D models if given or by proxy geometry (like cubes). They don't need to animate, just show where they are.
- Manipulators will control visualizations of _in vivo_ probes. These are like regular probes but are not user controlled and are attached to the manipulator (not part of the probe hierarchy).
- Users can control manipulators through Pinpoint's interface. This can be done by driving the translation stages directly or by trajectory planning and automation.

## Scene Hierarchy

Manipulators are a first-class entity meaning they get their own section in the scene hierarchy. An "Add Manipulator" button starts the section and opens a connection and picking dialog. This should be modeled like the atlas picker with a source picker and a manipulator picker that populates with the results from the connection.

> [!NOTE]
> Manipulators from different Ephys Links instances can be added to the same experiment.

Connections to Ephys Link are ephemeral. If a connection is unable to be established when something needs to happen, show a connection error notification but don't remove the manipulator or the setup. Instead, show it is "disconnected" and provide a reconnect button to try connecting again. This will try using `GET /manipulators` to a) check for a connection to Ephys Link and b) check for the manipulator's existence.

## Coordinate System Update

To support manipulators, coordinate systems need to allow for syncing translation axes. For a given free axis, users can mark which index of the position array it should be attached to on the manipulator. When being used to update the _in vivo_ probe visualization these axes will be overwritten by the state of the manipulator and when used to drive the manipulator they are used to write the values back to the manipulator.

When the coordinate system is used on a regular planning probe these fields are treated as regular free axes.

## Manipulator Model

The manipulator model encapsulates both the manipulator's state and information to display a probe in the scene. It is modeled off of the probe model but has additional parts for manipulators.

- Source (Ephys Link address)
- Info object from the `GET /manipualtors` route
- State object from the last `GET /{make}/{ID}`
- _in vivo_ probe type
- Coordinate system
- Other probe states like the channel map and in-plane slice zoom, lock state (ignores user input), etc.

This setup has a lot of duplication with probes, so some refactoring may be useful to extract commonly used functions. Manipulators and probe should have separately defined interfaces though (even if they copy each other).

## Inspectors

It should look a lot like the probe inspector. It will have an in-plane slice window at the top followed by the coordinate system fields to configure. Configuring the coordinate system values is essentially used to accurately orient the manipulator.
