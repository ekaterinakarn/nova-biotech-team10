// Offline GLB skinning. Activation animates a fixed grip, not inferred finger positions.
// Dynamic imports preserve the Canvas fallback if WebGL or an asset is unavailable.
import { createHand as createFallback } from './hand-procedural.js';

export function createHand(canvas) {
  let draw = () => {}, status = 'Loading rigged hand';
  let activation = 0, meta = {}, failed = false;
  async function initialize() {
    const THREE = await import('./vendor/three/three.module.js');
    const { GLTFLoader } = await import('./vendor/three/GLTFLoader.js');
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 10);
    camera.position.set(0, 0.01, 0.47);
    camera.lookAt(0, 0.01, 0);
    scene.add(new THREE.HemisphereLight(0xe7f2f4, 0x26363f, 1.8));
    const key = new THREE.DirectionalLight(0xfff5df, 2.8);
    key.position.set(-1, 2, 3); scene.add(key);
    const rim = new THREE.DirectionalLight(0xa2d8d0, 1.4);
    rim.position.set(2, 1, -2); scene.add(rim);
    const gltf = await new GLTFLoader().loadAsync('./models/right.glb');
    const model = gltf.scene;
    const turntable = new THREE.Group();
    scene.add(turntable); turntable.add(model);
    // Preserve the original faceted feedback aesthetic on the continuous rigged mesh.
    const stateColors = { engaged: 0x58c5a4, ambiguous: 0xc9ad55, rest: 0x8294a7 };
    const surface = new THREE.MeshStandardMaterial({
      color: stateColors.ambiguous,
      roughness: 0.58,
      metalness: 0.32,
      flatShading: true,
    });
    model.traverse(object => {
      if (object.isMesh) { object.material = surface; object.frustumCulled = false; }
    });
    const { createGripRig } = await import('./hand-rig.js?v=aligned-grip-6');
    const rig = createGripRig(model);
    // Bind coordinates: fingers point down Y, palm thickness is X.
    model.rotation.set(0, Math.PI / 2, Math.PI);
    model.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(model);
    const center = bounds.getCenter(new THREE.Vector3());
    model.position.sub(center);
    turntable.rotation.y = -0.25;
    let pointer = null;
    canvas.addEventListener('pointerdown', event => {
      pointer = event.clientX; canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
      if (pointer !== null) { turntable.rotation.y += (event.clientX-pointer)*0.008; pointer=event.clientX; }
    });
    for (const event of ['pointerup', 'pointercancel']) canvas.addEventListener(event, () => { pointer=null; });
    canvas.addEventListener('webglcontextlost', event => {event.preventDefault(); fallback();});
    draw = (value, info) => {
      const width = canvas.clientWidth, height = canvas.clientHeight;
      const size = renderer.getSize(new THREE.Vector2());
      if (size.x !== width || size.y !== height) {
        renderer.setSize(width, height, false); camera.aspect=width/height; camera.updateProjectionMatrix();
      }
      rig.apply(value);
      surface.color.set(info.signalOk === false ? 0x485963
        : (stateColors[info.state] ?? stateColors.rest));
      surface.emissive.set(info.signalOk !== false && info.state === 'engaged' ? 0x062019 : 0x000000);
      renderer.render(scene, camera);
    };
    status = 'Rigged 3D hand';
    draw(activation, meta);
  }
  function fallback(error) {
    if (failed) return;
    failed = true;
    console.warn('Hand renderer fallback:', error || 'WebGL context lost');
    // A WebGL canvas cannot acquire a 2D context; replace it before fallback.
    const replacement = canvas.cloneNode(false);
    canvas.replaceWith(replacement); canvas = replacement;
    draw = createFallback(canvas).applyPose;
    status = '3D unavailable · showing old fallback';
    const label = document.getElementById('renderer-status');
    if (label) label.title = String(error?.message || 'WebGL context lost');
  }
  const ready = initialize().catch(fallback);
  return {
    ready,
    get status() { return status; },
    applyPose(value, info = {}) {
      activation = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
      meta = info; draw(activation, meta);
    }
  };
}
