import {FREQ,TIPS,copyModel,writeExperience,transfers,logResponseChange} from './engine.mjs';
const NS='http://www.w3.org/2000/svg';
const el=id=>document.getElementById(id);
const element=(tag, attrs={})=>{const s=document.createElementNS(NS,tag);for(const [key,v] of Object.entries(attrs))s.setAttribute(key,v);return s;};
const textSvg=(parent, x,y, text, attrs={})=>{const t=element('text',{x,y,fill:'#9db1c4','font-size':12,...attrs});t.textContent=text;parent.appendChild(t);return t;};
const angle=[-Math.PI/2,0,Math.PI/2,Math.PI];
const colors=['#66d4eb','#b6a4ef','#86d7ba','#f0b66d'];
const coords=[[260,195]];
for(let arm=0;arm<4;arm++)for(let d=1;d<=6;d++){
  const a=angle[arm],s=d*28;
  coords.push([260+Math.cos(a)*s+Math.sin(a)*Math.sin(d/2)*4,
               195+Math.sin(a)*s+Math.cos(a)*Math.sin(d/2)*4]);
}
let original=null, current=null, before=null, after=null, delta=Array(25).fill(0), branch=null, probe=0, view='change';
function setStatus(msg){el('status').textContent=msg;}
function makeButtons(id,onSelect){for(let arm=0;arm<4;arm++){
  const btn=document.createElement('button');btn.textContent=`Branch ${arm+1}`;btn.addEventListener('click',()=>onSelect(arm));el(id).appendChild(btn);
}}
function updateButtons(){
  [...el('experience-buttons').children].forEach((b,i)=>b.classList.toggle('active',i===branch));
  [...el('probe-buttons').children].forEach((b,i)=>b.classList.toggle('active',i===probe));
  el('state').textContent=branch===null?'UNWRITTEN':'OPERATOR CHANGED';el('state').classList.toggle('written',branch!==null);
}
function drawTree(){const s=el('tree');s.replaceChildren();
  for(const [a,b] of original.edges){
    s.appendChild(element('line',{x1:coords[a][0],y1:coords[a][1],x2:coords[b][0],y2:coords[b][1],stroke:'#466277','stroke-width':3,'stroke-linecap':'round'}));
  }
  for(let i=1;i<coords.length;i++){
    const level=Math.min(1, delta[i]/.37);
    if(level>.005)s.appendChild(element('circle',{cx:coords[i][0],cy:coords[i][1],r:6+level*15,fill:'#f0b66d',opacity:.09+.3*level}));
    s.appendChild(element('circle',{cx:coords[i][0],cy:coords[i][1],r:4+level*5,fill:level>.06?'#efb56d':'#66d4eb',stroke:'#142538','stroke-width':1.5}));
  }
  s.appendChild(element('circle',{cx:260,cy:195,r:14,fill:'#203e55',stroke:'#8bdcf0','stroke-width':2}));
  textSvg(s,260,199,'S',{fill:'#dcf5fb','text-anchor':'middle','font-weight':'bold'});
  textSvg(s,260,220,'SOMA',{fill:'#dcf5fb','font-size':10,'text-anchor':'middle'});
  for(let i=0;i<4;i++){
    const [x,y]=coords[TIPS[i]];
    s.appendChild(element('circle',{cx:x,cy:y,r:13,fill:'none',stroke:i===probe?'#fff':colors[i],'stroke-width':i===probe?3:1.5}));
    textSvg(s,x+(x<260?-19: x>260?19:0),y+(y<195?-19:y>195?25:0),String(i+1),{fill:colors[i],'font-size':15,'font-weight':'bold','text-anchor':'middle'});
  }
}
function path(points){return points.map((pt,i)=>`${i?'L':'M'}${pt[0].toFixed(2)},${pt[1].toFixed(2)}`).join(' ');}
function drawPlot(){const svg=el('plot');svg.replaceChildren();const bx=52,by=20,width=566,height=230;
  let old=before.map(x=>Math.hypot(...x[probe]));
  let now=after.map(x=>Math.hypot(...x[probe]));
  let first=view==='change'?logResponseChange(before,after).map(x=>x[probe]):old;
  let second=view==='change'?null:now;
  const values=second?first.concat(second):first;
  let min=Math.min(...values,0),max=Math.max(...values,0);
  if(Math.abs(max-min)<1e-8){min-=.1;max+=.1;}
  const pad=.08*(max-min);min-=pad;max+=pad;
  const toY=v=>by+height-(v-min)/(max-min)*height;
  const toX=i=>bx+i*width/(FREQ.length-1);
  for(let k=0;k<=4;k++){
    const v=min+(max-min)*k/4,y=toY(v);
    svg.appendChild(element('line',{x1:bx,y1:y,x2:bx+width,y2:y,stroke:'#29384a','stroke-width':1}));
    textSvg(svg,bx-9,y+4,v.toFixed(Math.abs(max-min)<.3?3:2),{'text-anchor':'end','font-size':11});
  }
  FREQ.forEach((f,i)=>textSvg(svg,toX(i),by+height+21,String(f),{'text-anchor':'middle','font-size':11}));
  textSvg(svg,bx+width/2,291,'ANGULAR FREQUENCY ω (rad/s)',{'text-anchor':'middle','font-size':10,'letter-spacing':'1'});
  if(min<0 && max>0) svg.appendChild(element('line',{x1:bx,y1:toY(0),x2:bx+width,y2:toY(0),stroke:'#7f94a9','stroke-dasharray':'5 5'}));
  function line(data,color,dash){
    const points=data.map((v,i)=>[toX(i),toY(v)]);
    svg.appendChild(element('path',{d:path(points),fill:'none',stroke:color,'stroke-width':2.6,'stroke-dasharray':dash||''}));
    points.forEach(([x,y])=>svg.appendChild(element('circle',{cx:x,cy:y,r:3.4,fill:color})));
  }
  line(first,view==='change'?'#f0b66d':'#66d4eb',view==='absolute'?'6 5':'');
  if(second)line(second,'#f0b66d');
  if(view==='absolute'){
    textSvg(svg,460,15,'– – BEFORE', {fill:'#66d4eb','font-size':11});
    textSvg(svg,555,15,'— AFTER', {fill:'#f0b66d','font-size':11});
  }else{textSvg(svg,615,15,'Δ log|H|', {fill:'#f0b66d','font-size':12,'text-anchor':'end'});}
}
function rerender(){updateButtons();drawTree();drawPlot();
  const d=logResponseChange(before,after);const rms=Math.sqrt(d.reduce((s,row)=>s+row.reduce((v,x)=>v+x*x,0),0)/32);
  el('rms').textContent=rms.toFixed(4);
  el('budget').textContent=delta.reduce((s,x)=>s+x,0).toFixed(4);
}
function write(arm){branch=arm;const r=writeExperience(original,arm);current=r.changed;delta=r.delta;after=transfers(current);
  setStatus(`Experience: unit impulse at branch ${arm+1}. The voltage has been fully reset; only conductance changed. Compare the same probes at the same soma.`);
  rerender();}
function reset(){branch=null;current=copyModel(original);after=before;delta=Array(25).fill(0);
  setStatus('Original operator restored. No experience-dependent difference remains.');rerender();}
function noWrite(){reset();setStatus('Sham: a pulse occurred but plasticity was disabled. After voltage reset, the operator and its probe response are identical.');}
async function init(){
  try{
    const response=await fetch('demo.json');if(!response.ok)throw new Error('Missing demo model');
    original=await response.json();current=copyModel(original);before=transfers(original);after=before;
    makeButtons('experience-buttons',write);makeButtons('probe-buttons',i=>{probe=i;rerender();});
    document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{
      view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));drawPlot();}));
    el('no-write').addEventListener('click',noWrite);el('reset').addEventListener('click',reset);
    rerender();
  }catch(error){setStatus(`Unable to load model: ${error.message}. Serve web/ over HTTP, rather than opening a local file directly.`);}
}
init();
