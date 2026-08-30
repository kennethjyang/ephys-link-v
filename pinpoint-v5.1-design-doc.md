# Pinpoint V (v5.1) Manipulator Design Doc.

Pinpoint V (v5.1) will reintroduce electrophysiology manipulator integration for visualization and automation. It is designed specifically to integrate with Ephys Link V (v5.1). This desing doc is meant for humans and LLMs to read.

## Goals

- Manipulator should be a first-class entity like probes and is a distinct concept from them.
- Manipulators bodies should be visualized in the scene with both 3D models if given or by proxy geometry (like cubes). They don't need to animate, just show where they are.
- Manipulators will control visualizations of _in vivo_ probes. These are like regular probes but are not user controlled and are attached to the manipulator (not part of the probe hierarchy).
- Users can control manipulators through Pinpoint's interface. This can be done by driving the translation stages directly or by trajectory planning and automation.

## Scene Hierarchy

Manipulators are a first-class entity meaning they get their own section in the scene hierarchy. An "Add Manipulator" button starts the section and opens a connection and picking dialog. This should be modeled like the atlas picker with a source picker and a manipulator picker that populates with the results from the connection.

> [!NOTE]
> Manipulators from different Ephys Links instances can be added to the same experiment.

Connections to Ephys Link are ephemeral. If a connection is unable to be established when something needs to happen, show a connection error notification but don't remove the manipulator or the setup. Instead show it is "disconnected" and provide a re-connect button to try connecting again. This will try using `GET /manipulators` to a) check for a connection to Ephys Link and b) check for the manipualtor's existence.

### Manipulator Model

- Source (Ephys Link address)
- Info object from the `GET /manipualtors` route

## Organization and Implementation
