// hand.js — the virtual hand renderer (Canvas 2D, zero dependencies).
//
// THE ONE INTERFACE THAT MATTERS:  createHand(canvas) -> { applyPose(activation, meta) }
//   activation : number in [0, 1].  0 = fully open hand, 1 = closed fist.
//   meta       : { state, signalOk } for colour/greyed-out feedback.
//
// This is the single seam for the visuals. To swap in a rigged 3D model later
// (three.js + a glTF hand, Blender export, etc.), implement the SAME contract:
//   export function createHand(container) {
//       // build your 3D scene here
//       return { applyPose(activation, meta) { /* drive finger blendshapes/bones to
//                 `activation`: 0 open, 1 fist; tint by meta.state */ } };
//   }
// app.js drives applyPose ~60x/sec with an interpolated value, so the 3D module does
// NOT need its own smoothing — just map activation -> pose. Nothing else changes.

const STATE_COLORS = {
  engaged: "#39d98a",     // green
  ambiguous: "#f5c451",   // amber
  rest: "#8a94a6",        // grey-blue
};

export function createHand(canvas) {
  const ctx = canvas.getContext("2d");

  // Draw one finger as a chain of phalanges that bend more as `curl` -> 1.
  function drawFinger(x, y, lengths, baseAngle, curl, width) {
    let angle = baseAngle;
    let px = x, py = y;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(px, py);
    lengths.forEach((len, i) => {
      // Knuckle bends most; distal joints add more curl progressively.
      angle += curl * (0.5 + 0.35 * i);
      px += Math.cos(angle) * len;
      py += Math.sin(angle) * len;
      ctx.lineTo(px, py);
    });
    ctx.stroke();
  }

  function applyPose(activation, meta = {}) {
    const a = Math.max(0, Math.min(1, activation));
    const { state = "rest", signalOk = true } = meta;
    const W = canvas.width, H = canvas.height;

    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.globalAlpha = signalOk ? 1.0 : 0.25;            // grey out on bad signal
    const color = signalOk ? (STATE_COLORS[state] || STATE_COLORS.rest) : "#556";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;

    // Layout centred in the canvas.
    const cx = W / 2, palmTop = H * 0.58, palmW = W * 0.28, palmH = H * 0.22;

    // Palm.
    roundRect(ctx, cx - palmW / 2, palmTop, palmW, palmH, 22);
    ctx.fill();

    // Four fingers along the top of the palm. curl in radians (0 straight .. ~1.1 fist).
    const curl = a * 1.15;
    const up = -Math.PI / 2;
    const fingerSpec = [
      { dx: -0.34, lens: [0.16, 0.13, 0.10] }, // index
      { dx: -0.11, lens: [0.19, 0.15, 0.11] }, // middle
      { dx: 0.11, lens: [0.17, 0.14, 0.10] },  // ring
      { dx: 0.32, lens: [0.13, 0.11, 0.08] },  // pinky
    ];
    for (const f of fingerSpec) {
      drawFinger(cx + f.dx * palmW * 1.6, palmTop + 6,
                 f.lens.map((l) => l * H), up, curl, palmW * 0.22);
    }

    // Thumb curls across from the left side of the palm.
    drawFinger(cx - palmW / 2, palmTop + palmH * 0.35,
               [0.12 * H, 0.10 * H], -Math.PI / 5, a * 0.9, palmW * 0.24);

    ctx.restore();
  }

  function roundRect(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  applyPose(0, { state: "rest" });   // initial open hand
  return { applyPose };
}
