// Articulated 3D geometry, projected and depth-sorted onto Canvas. No GPU/CDN required.
// The app owns smoothing; this module only maps activation to joint angles.
export function createHand(canvas) {
  const ctx = canvas.getContext('2d');
  let yaw = -0.42, drag = null;
  canvas.addEventListener('pointerdown', e => { drag = e.clientX; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (drag !== null) { yaw += (e.clientX-drag)*0.008; drag=e.clientX; } });
  canvas.addEventListener('pointerup', () => { drag = null; });
  canvas.addEventListener('pointercancel', () => { drag = null; });
  const rotate = ([x,y,z]) => {
    const X=x*Math.cos(yaw)+z*Math.sin(yaw), Z=-x*Math.sin(yaw)+z*Math.cos(yaw);
    return [X, y*Math.cos(-0.12)-Z*Math.sin(-0.12), y*Math.sin(-0.12)+Z*Math.cos(-0.12)];
  };
  function applyPose(activation, meta={}) {
    const a=Math.max(0,Math.min(1,activation));
    const dpr=Math.min(devicePixelRatio||1,2), w=canvas.clientWidth, h=canvas.clientHeight;
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){ canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr); }
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    const faces=[];
    const scale=Math.min(w/5.5,h/7.5);
    const project=p=>{const [x,y,z]=rotate(p),perspective=10/(10-z);return [w/2+x*scale*perspective,h*0.57-y*scale*perspective,z];};
    // Ellipsoids make palm, phalanges and knuckles. Every vertex lives in 3D.
    function solid(center, radii, bend=0, spread=0, joint=false){
      const point=(u,v)=>{
        let x=radii[0]*Math.sin(v)*Math.cos(u), y=radii[1]*Math.cos(v),z=radii[2]*Math.sin(v)*Math.sin(u);
        const Y=y*Math.cos(bend)-z*Math.sin(bend), Z=y*Math.sin(bend)+z*Math.cos(bend);
        return [center[0]+x*Math.cos(spread)-Y*Math.sin(spread),center[1]+x*Math.sin(spread)+Y*Math.cos(spread),center[2]+Z];
      };
      for(let j=0;j<8;j++)for(let i=0;i<12;i++){
        const pts=[[i,j],[i+1,j],[i+1,j+1],[i,j+1]].map(([u,v])=>project(point(u*Math.PI/6,v*Math.PI/8)));
        faces.push({pts,z:pts.reduce((s,p)=>s+p[2],0)/4,light:0.65+0.25*Math.cos(i*Math.PI/6-0.6)+0.1*Math.cos(j*Math.PI/8),joint});
      }
    }
    solid([0,-1.8,0],[0.58,1,0.34]);solid([0,-0.5,0],[1.02,1.15,0.38]);
    const fingers=[[-0.73,0.27,[0.88,0.58,0.44]],[-0.25,0.48,[1.02,0.68,0.46]],[0.25,0.42,[0.94,0.62,0.44]],[0.72,0.18,[0.72,0.48,0.38]]];
    for(const [x,y,lengths] of fingers){
      let p=[x,y,0], angle=0;
      for(let k=0;k<3;k++){
        angle+=a*[1.35,1.55,1.05][k];
        const len=lengths[k],end=[p[0],p[1]+len*Math.cos(angle),p[2]+len*Math.sin(angle)];
        solid(p,[0.23,0.23,0.23],0,0,true);
        solid(p.map((v,i)=>(v+end[i])/2),[0.205,len/2+0.1,0.205],angle);
        p=end;
      }
    }
    // Thumb opposes across the palm as activation increases.
    const spread=0.9-a*1.6;
    let p=[-0.88,-0.75,0.18];
    for(let k=0;k<2;k++){
      const len=k?0.58:0.76,bend=a*(0.7+k*0.6);
      const end=[p[0]-len*Math.sin(spread)*Math.cos(bend),p[1]+len*Math.cos(spread)*Math.cos(bend),p[2]+len*Math.sin(bend)];
      solid(p,[0.27,0.27,0.27],0,0,true);
      solid(p.map((v,i)=>(v+end[i])/2),[0.24,len/2+0.12,0.24],bend,spread);p=end;
    }
    const rgb=meta.signalOk===false?[92,108,119]:meta.state==='engaged'?[100,231,196]:meta.state==='ambiguous'?[215,195,130]:[155,186,197];
    faces.sort((a,b)=>a.z-b.z);
    ctx.globalAlpha=meta.signalOk===false?0.4:1;
    for(const f of faces){ctx.beginPath();f.pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();
      ctx.fillStyle=`rgb(${rgb.map(v=>Math.round(v*f.light*(f.joint?0.67:1))).join(',')})`;ctx.fill();ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=0.5;ctx.stroke();}
    ctx.globalAlpha=1;
  }
  return {applyPose};
}
