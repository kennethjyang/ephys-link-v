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
- State object from the last poll
- _in vivo_ probe type
- Coordinate system
- Offset from reference coordinate
- Active task ID (if any)
- Movement speed (speed for setting its position)
- Other probe states like the channel map and in-plane slice zoom, lock state (ignores user input), etc.

This setup has a lot of duplication with probes, so some refactoring may be useful to extract commonly used functions. Manipulators and probe should have separately defined interfaces though (even if they copy each other).

## Inspectors

It should look a lot like the probe inspector. It will have an in-plane slice window at the top followed by the coordinate system fields to configure. Configuring the coordinate system values is essentially used to accurately orient the manipulator. The fields that are attached to the manipulator should be disabled from user input but still displayed.

An addition field above the coordinate system section is added to manage the offset to the reference coordinate. A button can be used to use the current position of the manipulator as the offset. This information should be pulled directly using the `GET /{make}/{ID}`.

The channel maps section should be split into probes and manipulators via the expansion component. Probes are still listed first.

When a manipulator is added to an experiment, it does not have a probe set yet. At this point it's only visualized by the manipulator body geometry and all the probe-centric inspector parts (in-plane slice, channel maps, probe body geometry, etc.) are all hidden. At the top of the inspector should be a probe type selector which will spawn the probe geometry. This is probe will have similar behavior to regular probes but is maintained separately by the manipulator system. The geometry is part of the same geometry group as the manipulator body (i.e. the selection outline layer highlights both the probe and the manipulator body).

During a disconnection from Ephys Link, the interface should be disabled (but not hidden) except for a reconnect button at the top.

## Syncing Position

Once a probe type is selected, its position will immediately be owned and set by the manipulator state. The scene canvas will be responsible for updating the position. It will maintain a throttled poll of the `GET /state[?ids={make:ID}]+` route based on the manipulators in the experiment and update the state of manipulators. The desired polling behavior is to go as fast as possible up to the scene's update rate (i.e. wait for the previous result to come back and then send another request). The state route is used instead of the individual route to be more efficient. The _in vivo_ probe's position is computed using forward kinematics like regular probes and the position is updated in the scene.

If a requested manipulator state does not come back, that means there was a problem getting it. Disable real-time polling until the user presses the reconnect button.

## Setting Position

Keyboard controls can be used to send fire-and-forget movements. The inspector will have a large stop button in the control cluster at the top that appears during movements and can be used to stop probes. There is also a speed input for how fast movements should go. At this stage there is not safety or speed reductions if the movement goes into the brain. If a movement increment looks like it will go into the brain, throw a warning notification in the top with a dismiss which will ignore the movement and a confirm button which will do the movement.

Positions are computed which results in the manipulator's positions and then they are transmitted using the `PATCH /set-position/{make}/{ID}` route. The task ID is added to the model and is used to poll for whether the movement is still ongoing or if something happened to it. A background polling task is spawned (something using `setInterval`) to watch the state of the task. On termination if it was completed successfully a success notification is shown (can be disabled in preferences) and the stop button is taken away. On error an error notification with the appropriate information is shown instead.

## Automation

> [!WARNING]
> Implement this last. It builds on everything else.

At the bottom of the manipulator section in the scene hierarchy, add a toggle to enable "Automation Mode". When enabled, all probes are changed to the shank-only visualization and locked (save what it was before so exiting this mode will revert it back to what it was before). All manipulators also have their configurations locked. For any manipulators that have not had their reference coordinate offsets calibrated, disable them in the hierarchy with a tooltip that explains only calibrated manipulators can be used in automation.

When selecting a manipulator, an automation inspector is shown. It should be modeled after the regular manipulator inspector. At the top is the in-plane slice, followed by the coordinate system state (read only), and then the automation pipeline components.

The automation pipeline has four sections:

1. Target selection
2. Entry coordinate drive
3. Surface calibration
3. Final depth drive
4. Reset

### Additions to the Manipulator State.

To enable automation, the manipulator state needs to now also have the following state:

- Selected target probe (ID)
- Axis drive order (list of indices)
- Entry coordinate distance (default: 3 mm)
- Entry coordinate drop on DV vs depth (default: depth)
- Is moving flag
- Surface coordinate offset (for the _in vivo_ probe visualization)
- Surface coordinate offset axis
- Drive speed (speed inside the brain; default: 5 micrometers per second)
- Proximity distance (when it should start slowing down as it reaches the target; default: 1 mm)
- Proximity speed fraction (how much slower it should get; must be < 1; default: 2/3)
- Drive past distance (default: 50 micrometers)
- How long to wait at the drive past distance (default: 60 seconds)
- Rested at drive past flag
- Return to surface drive speed multiplier (default: 5)
- Exit safety margin (how much further it should retract after the manipulator is supposedly outside of the brain; default: 100 micrometers)

### Target Selection

This segment is a dropdown with all probes that haven't been selected by a manipulator yet. The selection can be cleared.

When a target is selected, the entry coordinate panel is enabled.

### Entry Coordinate

After a target is selected, compute two entry coordinates: one located directly above the surface coordinate of the target on DV and the other along the probe axis. The user can edit the entry coordinate distance. Use a button toggle to switch between selecting the DV and the probe axis entry coordinates.

Next is the planning of the trajectory there. Compute two options: one that follows the atlas axes (ML, AP, DV) and one that follows the manipulator's native axes. Break down the trajectory into steps that only edits one of these axes at a time. The user can select between these two trajectories using a toggle button and they can rearrange the order in which these axes are set. As part of the rearrangement of axes, users can also choose to _split_ the distance of an axes, to build a custom trajectory. So in the list of axes, there is a button to split (or delete a split). When there is a split a slider will appear with the total distance of the trajectory axis. The user can mode this slider to represent how far along in the trajectory this split will go. Subsequent splits will have their slider start where the last one left off so each slider will always represent the full distance of the axis. They all sum up to the total distance needed, but this splitting system will allow for custom movements along the axes. The trajectory plan is continuously computed based on the manipulator's position (throttled if needed).

> [!NOTE]
> A future implementation could consider using navigation to figure out the trajectory, but this version should use a highly specific and customizable trajectory planning system instead.

Finally, to visualize the trajectory draw trajectory lines from the manipulator's _in vivo_ probe tip to the entry coordinate. These lines follow the order and length of the plan. Also show a semi-transparent plane that extends from the line up along the length of the shank to represent the space the probe sweeps. This plane can be hidden in the inspector. It is used to help visualize for collisions.

Under this is a "Move" button to start the manipulator along this trajectory. While moving, the move button is replaced with a stop button.

Once at the entry coordinate, the trajectory lines are removed the surface calibration panel is enabled.

### Surface Calibration

Let the user manually move the probe to touch the surface. Then provide a button that does the same thing as the drop the surface button for probes (it will also show the DV/Depth choice arrows). Once surface calibration is one, the drive panel is enabled.

### Depth Drive

An arrow is drawn to show the trajectory from the manipulator's _in vivo_ probe tip to the drive past distance and then another arrow to show the movement back up to the target. The target location is also recalculated to be projected on the plane defined by the probe shank as the normal. This is to handle the case where the manipulator is moved slightly after going to the entry coordinate (so it is no longer exactly lined up along the probe's axis).

Fields are available to edit the remaining settings/states. The base speed is edited first with a dropdown containing the common safe speed options (1, 3, 5, 10 micrometers per second) and then the option to type in a custom one. The proximity and retraction speed fractions are regular number inputs with default values.

A drive is moving only on one manipulator axis (the drive axes) from the surface to the proximity distance, to the drive past distance, back up to the target, and then finally retracting to the surface after the recording. Once it has reached the drive past distance _and waited there for the required time_ it can mark the flag that it has done so.

At the bottom is the "Drive" button to start the movement. While moving, the button is replaced with a stop button. When stopped after a drive has started, a "resume" button will continue the drive path from the manipulator's current location and an "retract" button will start to pull the probe back up. Notably, if the drive past rest flag has not been set, any drive movement must go back to that point to complete it.

Once at the drive target, the retract panel is enabled.

### Retract

Once the experiment is done, the retract button pulls the probe back up to the surface and then to the entry coordinate. The retract button swaps with a stop button that pauses the movement.

> [!IMPORTANT]
> At this stage, there is no safety checks for going back and trying to change a previous step. Users are responsible for the safety and correctness of their movement through the automation pipeline.
