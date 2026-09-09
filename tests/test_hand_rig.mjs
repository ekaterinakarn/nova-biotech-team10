// Run: node tests/test_hand_rig.mjs. Exercise actual GLB bind joints and production rig.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from '../ui/vendor/three/three.module.js';
import { createGripRig } from '../ui/hand-rig.js';

const bytes = readFileSync(new URL('../ui/models/right.glb', import.meta.url));
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
const nodes = json.nodes.map(data => {
  const bone = new THREE.Bone();
  bone.name = data.name;
  if (data.translation) bone.position.fromArray(data.translation);
  if (data.rotation) bone.quaternion.fromArray(data.rotation);
  if (data.scale) bone.scale.fromArray(data.scale);
  return bone;
});
json.nodes.forEach((data, index) => (data.children || []).forEach(child => nodes[index].add(nodes[child])));
const model = new THREE.Group();
json.scenes[json.scene || 0].nodes.forEach(index => model.add(nodes[index]));
const position = name => model.getObjectByName(name).getWorldPosition(new THREE.Vector3());
const fingers = ['index', 'middle', 'ring', 'pinky'];
const rig = createGripRig(model);
rig.apply(0);
const open = Object.fromEntries(fingers.map(f => [f, position(`${f}-finger-tip`)]));
const thumbOpen = position('thumb-tip');
const segments = fingers.flatMap(finger => {
  const names = ['phalanx-proximal', 'phalanx-intermediate', 'phalanx-distal', 'tip']
    .map(joint => `${finger}-finger-${joint}`);
  return names.slice(1).map((name, index) => ({
    start: names[index], end: name, length: position(names[index]).distanceTo(position(name)),
  }));
});
for (const grip of [.1, .5, 1]) {
  rig.apply(grip);
  for (const finger of fingers) {
    const tip = position(`${finger}-finger-tip`);
    assert(tip.x < open[finger].x, `${finger} must curl toward palm (-X) at grip ${grip}`);
    assert(Number.isFinite(tip.length()));
    if (grip === 1) {
      const knuckle = position(`${finger}-finger-phalanx-proximal`);
      assert(Math.abs(tip.z - knuckle.z) < .012, `${finger} must not fan sideways on closure`);
    }
  }
}
for (const segment of segments) {
  assert(Math.abs(position(segment.start).distanceTo(position(segment.end)) - segment.length) < 1e-10,
    'Posing must preserve finger bone lengths');
}
assert(position('thumb-tip').z > thumbOpen.z, 'Thumb must oppose across palm (+Z)');
rig.apply(0);
for (const finger of fingers) {
  assert(position(`${finger}-finger-tip`).distanceTo(open[finger]) < 1e-10, 'Opening must restore bind pose');
}
console.log('Hand rig: inward curl at 10/50/100%, thumb opposition, and open-pose restoration passed.');
