// Pose the asset's native WebXR joints in their shared armature coordinate system.
// All finger hinges use one aligned flexion plane, preventing sideways joint drift.
import * as THREE from './vendor/three/three.module.js';

export function createGripRig(model) {
  const fingerNames = ['index', 'middle', 'ring', 'pinky'];
  const names = fingerNames.map(name => [
    `${name}-finger-metacarpal`, `${name}-finger-phalanx-proximal`,
    `${name}-finger-phalanx-intermediate`, `${name}-finger-phalanx-distal`, `${name}-finger-tip`,
  ]);
  names.push(['thumb-metacarpal', 'thumb-phalanx-proximal', 'thumb-phalanx-distal', 'thumb-tip']);
  const chains = names.map(list => list.map(name => {
    const bone = model.getObjectByName(name);
    if (!bone) throw new Error(`Missing hand joint: ${name}`);
    return {bone, position: bone.position.clone(), rotation: bone.quaternion.clone()};
  }));
  const hinge = new THREE.Vector3(0, 0, -1);
  const gatherAxis = new THREE.Vector3(1, 0, 0);
  const thumbAxis = new THREE.Vector3(0, 1, 0);
  const rotation = new THREE.Quaternion(), gather = new THREE.Quaternion();
  const offset = new THREE.Vector3();
  const radians = THREE.MathUtils.degToRad;
  return {
    apply(value) {
      const grip = THREE.MathUtils.clamp(value, 0, 1);
      chains.forEach((chain, finger) => {
        let total = 0;
        rotation.identity(); gather.identity();
        if (finger < 4) {
          const direction = chain[2].position.clone().sub(chain[1].position);
          const spread = Math.atan2(direction.z, -direction.y);
          gather.setFromAxisAngle(gatherAxis, spread * THREE.MathUtils.smoothstep(grip, 0, .55));
        }
        chain.forEach((joint, index) => {
          // The preceding segment's rotation determines this joint's position.
          if (index === 0) joint.bone.position.copy(joint.position);
          else {
            offset.copy(joint.position).sub(chain[index-1].position).applyQuaternion(rotation);
            joint.bone.position.copy(chain[index-1].bone.position).add(offset);
          }
          if (finger < 4) {
            // Interphalangeal joints fold first, then the knuckle brings them to the palm.
            const angles = [0, 85 + finger*2, 100, 60, 0];
            const progress = index === 1 ? grip : Math.sin(grip * Math.PI / 2);
            total += radians(angles[index]) * progress;
            rotation.setFromAxisAngle(hinge, total).multiply(gather);
            if (index === 0) rotation.identity();
          } else {
            const progress = THREE.MathUtils.smoothstep(grip, .3, 1);
            if (index === 0) rotation.setFromAxisAngle(thumbAxis, radians(70)*progress);
            else rotation.multiply(new THREE.Quaternion().setFromAxisAngle(hinge, radians([0,32,42,0][index])*progress));
          }
          joint.bone.quaternion.copy(rotation).multiply(joint.rotation);
        });
      });
      model.updateMatrixWorld(true);
    },
  };
}
