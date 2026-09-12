// Socket state and smoothing belong here; the renderer receives only a pose.
import {createHand} from './hand.js?v=aligned-grip-6';
const el=id=>document.getElementById(id), hand=createHand(el('hand'));
let lastTick=performance.now();
let ws, latest=null, received=0, current=0, manual=false, rows=[], history=[], dose=0, observed=0, previous=null;
const colors={engaged:'#72e2c2',ambiguous:'#e4c47c',rest:'#95aab2'};
function connect(){
  ws=new WebSocket(`ws://${location.hostname||'127.0.0.1'}:8765`);
  ws.onopen=()=>{el('conn').textContent='● Connected';el('conn').className='ok';};
  ws.onclose=()=>{latest=null;previous=null;el('conn').textContent='● Disconnected · reconnecting';el('conn').className='bad';setTimeout(connect,1500);};
  ws.onmessage=e=>{
    let f;try{f=JSON.parse(e.data);}catch{return;}
    if(![f.t,f.fidelity,f.activation].every(Number.isFinite)||f.fidelity<0||f.fidelity>1||f.activation<0||f.activation>1||typeof f.signal_ok!=='boolean')return;
    const now=performance.now();
    const dt=previous&&f.t>previous.t&&now-received<1000?Math.min(f.t-previous.t,0.2):0;
    const eligible=f.signal_ok&&!f.sham&&!manual;
    observed+=dt;
    if(eligible&&previous?.eligible)dose+=previous.fidelity*dt;
    previous={...f,eligible};latest=f;received=now;
    rows.push({...f,manual,observed});if(rows.length>72000)rows.shift(); // bounded one-hour export at 20 Hz
    history.push({time:now,value:eligible?f.fidelity:null,cond:f.recorded_condition||f.condition||''});history=history.filter(p=>now-p.time<60000);
    el('sham').checked=Boolean(f.sham);
    el('source').textContent={file:'PhysioNet · curated epoch replay',sim:'Synthetic · rehearsal data',live:'Live EEG · amplifier',lsl:'Live EEG · LSL stream',cnt:'Recorded eego session · replay'}[f.source]||'Unknown data source';
    el('elapsed').textContent=`${Math.floor(observed/60)}:${String(Math.floor(observed%60)).padStart(2,'0')} observed`;
    el('dose').textContent=`${dose.toFixed(1)} score·s · valid normal feedback`;
  };
}
connect();
function tick(){
  const stale=!latest||performance.now()-received>3000, f=latest;
  const valid=!stale&&f.signal_ok;
  const target=manual?Number(el('slider').value)/100:valid?f.activation:0;
  const now=performance.now(), dt=Math.min((now-lastTick)/1000,0.1);lastTick=now;
  current+=(target-current)*(1-Math.exp(-dt/0.13));
  el('grip').textContent=`${Math.round(current*100)}% grip`;
  el('grip').dataset.activation=current;
  el('grip').dataset.target=target;
  const state=manual?'engaged':valid?f.state:'rest';
  hand.applyPose(current,{state,signalOk:manual||valid});
  el('renderer-status').textContent=hand.status;
  el('mode').textContent=manual?'MANUAL · NO EEG':stale?'WAITING':!valid?'SIGNAL PAUSED':f.sham?'CONTROL · 0.5':'MODEL FEEDBACK';
  el('score').textContent=manual||!valid?'—':Math.round(f.fidelity*100);
  el('fidelity-bar').style.transform=`scaleX(${manual||!valid?0:f.fidelity})`;
  el('fidelity-bar').style.background=colors[state]||colors.rest;
  el('state').textContent=manual?'MANUAL EXPLORATION':stale?'WAITING FOR SIGNAL':!valid?'SIGNAL PAUSED':f.sham?'IDENTICAL-TEMPLATE CONTROL':`${state.toUpperCase()} PATTERN`;
  el('quality').textContent=stale?'Signal quality unavailable':f.signal_ok?'● Window passed quality checks':'● Window rejected · feedback paused';
  el('coaching').textContent=manual?'Move the slider to explore the hand. EEG does not control this pose.':stale?'Waiting for your session. You can explore the hand using the controls below.':f.sham?'Control demonstration: both reference distances are treated as equal.':f.coaching;
  el('distances').textContent=valid&&!f.sham?`d_exec ${f.d_exec} · d_rest ${f.d_rest}`:'d_exec — · d_rest —';
  el('condition').textContent=(f?.source==='file'||f?.source==='cnt')?f.recorded_condition:((f?.source==='live'||f?.source==='lsl')&&f.instruction?f.instruction:(f?.condition||'Ready when you are'));
  el('sham').disabled=stale||manual;
  document.querySelectorAll('[data-condition]').forEach(b=>{b.disabled=stale||manual||f?.source==='file'||f?.source==='cnt'||f?.source==='sim';b.classList.toggle('active',b.dataset.condition===f?.condition);});
  const source=f?.source;
  // Guided session (live/lsl): the Start button runs the on-screen protocol.
  const guided=source==='live'||source==='lsl';
  const phases=['prepare','cal_move','cal_rest','build','rest','squeeze','imagine_feel','rest2','imagine_watch','math','feel_again','done'];
  const inSession=!!f&&phases.includes(f.phase);
  el('start-session').disabled=!guided||stale;
  el('start-session').dataset.on=inSession?'1':'0';
  el('start-session').textContent=inSession?'■ Stop session':'▶ Start guided session';
  el('countdown').textContent=inSession&&f.countdown>0?`${f.countdown}s`:'';
  el('guided-hint').style.display=guided&&!inSession?'':'none';
  el('condition-note').textContent=manual?'Manual exploration is on. Cues are paused.':stale?'Connect an EEG source to choose participant cues.':source==='file'||source==='cnt'?'Cues follow the recording during replay.':source==='sim'?'Synthetic rehearsal runs automatically. Use manual exploration to try the hand.':guided?'Press Start for the guided session, or set a cue manually below.':'Choose an instruction for the participant.';
  el('state').style.color=colors[state]||colors.rest;
  el('export').disabled=rows.length===0;
  el('export-status').textContent=rows.length?`${rows.length.toLocaleString()} frames recorded`:'No frames recorded yet';
  el('trace-empty').hidden=history.some(p=>p.value!==null);
  drawTrace();requestAnimationFrame(tick);
}
function drawTrace(){
  const c=el('trace'),dpr=Math.min(devicePixelRatio||1,2),w=c.clientWidth,h=c.clientHeight;
  if(c.width!==Math.round(w*dpr)||c.height!==Math.round(h*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);}
  const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const now=performance.now();
  ctx.strokeStyle='#2a3b43';ctx.lineWidth=1;
  for(const fraction of [0,.5,1]){const y=10+fraction*(h-20);ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
  // Event markers: a labelled vertical line wherever the recorded cue changes, so the
  // fidelity wave can be read against the session's Hand-squeezing / Imagining markers.
  const condColor=s=>/squeez/i.test(s)?'#72e2c2':/imagin/i.test(s)?'#7cc0e4':/virtual/i.test(s)?'#b79ce0':'#5a6b73';
  let prev=null;ctx.font='9px -apple-system,sans-serif';ctx.textBaseline='top';
  for(const p of history){
    if(p.cond&&p.cond!==prev){
      const x=w*(1-(now-p.time)/60000),col=condColor(p.cond);
      ctx.globalAlpha=.5;ctx.strokeStyle=col;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();
      ctx.globalAlpha=1;ctx.fillStyle=col;ctx.fillText(p.cond,x+3,3);
    }
    prev=p.cond;
  }
  // Fidelity wave on top.
  ctx.strokeStyle='#72e2c2';ctx.lineWidth=2;ctx.beginPath();let pen=false;
  for(const p of history){const x=w*(1-(now-p.time)/60000),y=h-10-p.value*(h-20);if(p.value===null){pen=false;continue;}if(pen)ctx.lineTo(x,y);else ctx.moveTo(x,y);pen=true;}ctx.stroke();
}
requestAnimationFrame(tick);
el('manual').onchange=()=>{manual=el('manual').checked;el('slider').disabled=!manual;previous=null;};
el('sham').onchange=()=>{if(ws?.readyState===1)ws.send(el('sham').checked?'sham:on':'sham:off');};
document.querySelectorAll('[data-condition]').forEach(b=>b.onclick=()=>{if(ws?.readyState===1)ws.send(`condition:${b.dataset.condition}`);});
el('start-session').onclick=()=>{if(ws?.readyState!==1)return;ws.send(el('start-session').dataset.on==='1'?'session:stop':'session:start');};
el('export').onclick=()=>{
  const keys=['observed','t','source','recorded_condition','condition','fidelity','activation','signal_ok','sham','manual'];
  const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
  const csv=[keys.join(','),...rows.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download='rEEGain-session.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
