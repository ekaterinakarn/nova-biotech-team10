# 3D hand and Blender workflow

> Latest update: EEG-only confirmed; hardware first available on build day. The hand now uses a locally bundled rigged GLB. See [EEG-to-hand connection and new validation](12_eeg-to-hand.md), which supersedes earlier renderer/validation status below.

The new hand runs in the browser now. It consists of 3D palm and finger ellipsoids, with
three bend angles per finger, a two-segment opposing thumb and a rotatable camera.
The CPU projects these shapes into Canvas and sorts faces by depth. It is a stylized
procedural model, not a Blender asset or anatomically validated simulation.

## Try it

```sh
.venv/bin/python src/server.py --source sim
```

Open http://127.0.0.1:8766. Synthetic windows drive the actual scorer and hand.
For recorded EEG: `.venv/bin/python src/server.py --source file --subject 4`.
For visuals alone: `python3 -m http.server 8000 -d ui`; open http://localhost:8000,
check Manual exploration and drag the slider. Drag the hand horizontally to orbit.
Open (0) and fist (1) are endpoints of a feedback animation, not decoded individual fingers.

## Blender installation and role

Blender is a separate desktop application; VS Code is the code editor for this project.
You do not need a VS Code plugin to use Blender or run this demo. Download Blender from
[the official site](https://www.blender.org/download/), choose the macOS Apple Silicon
build for the M4, open the downloaded disk image and move Blender to Applications.
Launch it normally. No Blender install was made during this review.

A VS Code integration can assist Blender Python scripting, but it does not replace the
Blender application. Begin with the standalone application to avoid an extra integration
and version compatibility step while learning.

## Optional realistic hand upgrade

1. Create or obtain a hand model with an explicit license allowing redistribution.
2. Rig its finger bones and make a single open-to-fist animation named `Grip`.
3. Export glTF 2.0 as a `.glb` with the mesh, material and animation included.
4. Store the asset locally with its license, then add a locally bundled Three.js renderer
   and GLTFLoader. The current renderer does not yet load GLB files.
5. Keep the animation paused and set animation time to `activation * duration` inside
   `applyPose`; continue using app.js for interpolation and networking.
6. Test activation 0, 0.5 and 1, lost connection, bad signal, offline loading and projector.
   On asset/WebGL failure, use the procedural renderer; retain `hand-2d.js` as a simpler backup.

References: [Blender glTF exporter](https://docs.blender.org/manual/en/4.0/addons/import_export/scene_gltf2.html),
[Three.js model loading](https://threejs.org/manual/en/loading-3d-models.html).
The task is to animate one feedback value; the current EEG model does not decode five
independent fingers or estimate hand pose.
