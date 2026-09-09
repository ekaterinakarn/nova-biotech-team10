# Rigged right hand

Source: https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets/profiles/generic-hand
Downloaded September 8, 2026, `right.glb`. Asset-specific MIT license: ASSET-LICENSE.md.
Upstream repository license notice: LICENSE.md. Upstream Blender-exported mesh is unchanged.
Our animation reparents its WebXR sibling joints into finger chains at runtime.
It is used as a feedback visualization, not an anatomically validated biomechanical model.

Three.js 0.180.0 is vendored in ../vendor/three with its MIT LICENSE.
GLTFLoader's BufferGeometryUtils import is adjusted to the local flat directory.
No code or models from Hand-Detection-3D were copied; its Blender/rig approach inspired this upgrade.

Asset SHA-256: `291790c14f7f88a7f9bd35330c47392ed8e8d395ae6728f4bb7089f1bc1f2b96`
