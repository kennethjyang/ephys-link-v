# Pinpoint V (v5.1) Manipulator Design Doc.

Pinpoint V (v5.1) will reintroduce electrophysiology manipulator integration for visualization and automation. It is designed specifically to integrate with Ephys Link V (v5.1). This design doc is meant for humans and LLMs to read.

## Goals

- Manipulator should be a first-class entity like probes and is a distinct concept from them.
- Manipulators bodies should be visualized in the scene with 3D models if given or by proxy geometry (like cubes). They don't need to animate, just show where they are.
- Manipulators will control visualizations of _in vivo_ probes. These are like regular probes but are not user controlled and are attached to the manipulator (not part of the probe hierarchy).
- Users can control manipulators through Pinpoint's interface. This can be done by driving the translation stages directly or by trajectory planning and automation.

## Scene Hierarchy

Manipulators are a first-class entity meaning they get their own section in the scene hierarchy. An "Add Manipulator" button starts the section and opens a connection and picking dialog. This should be modeled like the atlas picker with a source picker and a manipulator picker that populates with the results from the connection.

> [!NOTE]
> Manipulators from different Ephys Links instances can be added to the same experiment.

Connections to Ephys Link are ephemeral. If a connection is unable to be established when something needs to happen, show a connection error notification but don't remove the manipulator or the setup. Instead, show it is "disconnected" and provide a reconnect button to try connecting again. This will try using `GET /manipulators` to a) check for a connection to Ephys Link and b) check for the manipulator's existence. This essentially creates a connection error handling loop where any connection-related errors from Ephys Link will disable the manipulator and the user can use the button to reestablish connection and resume until another connection error happens again.

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

It should look a lot like the probe inspector. It will have an in-plane slice window at the top followed by the coordinate system fields to configure. Configuring the coordinate system values is essentially used to accurately orient the manipulator. The fields that are attached to the manipulator should be disabled from user input but still displayed.

The channel maps section should be split into probes and manipulators via the expansion component. Probes are still listed first.

When a manipulator is added to an experiment, it does not have a probe set yet. At this point it's only visualized by the manipulator body geometry and all the probe-centric inspector parts (in-plane slice, channel maps, probe body geometry, etc.) are all hidden. At the top of the inspector should be a probe type selector which will spawn the probe geometry. This is probe will have similar behavior to regular probes but is maintained separately by the manipulator system. The geometry is part of the same geometry group as the manipulator body (i.e. the selection outline layer highlights both the probe and the manipulator body).

During a disconnection from Ephys Link, the interface should be disabled (but not hidden) except for a reconnect button at the top.

## Syncing Position

Once a probe type is selected, its position will immediately be owned and set by the manipulator state. The scene canvas will be responsible for updating the position. It will maintain a throttled poll of the `GET /state[?ids={make:ID}]+` route based on the manipulators in the experiment and update the state of manipulators. The desired polling behavior is to go as fast as possible up to the scene's update rate (i.e. wait for the previous result to come back and then send another request). The state route is used instead of the individual route to be more efficient. The _in vivo_ probe's position is computed using forward kinematics like regular probes and the position is updated in the scene.

If a requested manipulator state does not come back, that means there was a problem getting it. Disable real-time polling until the user presses the reconnect button.
