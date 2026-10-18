// Browser and Node use this exact same computation.
// Passive 25-compartment cable. Not a biological reconstruction.
export const FREQ = [.05, .1, .2, .4, .8, 1.6, 3.2, 6.4];
export const TIPS = [6, 12, 18, 24];
export const BUDGET = .65;

export function copyModel(original) {
  return {G: original.G.map(row => row.slice()), C: original.C.slice(),
          leak: original.leak.slice(), edges: original.edges.map(row=>row.slice())};
}

export function voltageEligibility(model, branch) {
  const n = model.C.length, v = Array(n).fill(0), e=Array(n).fill(0);
  v[TIPS[branch]] = 1 / model.C[TIPS[branch]];
  const dt=.025;
  for(let step=0;step<360;step++) {
    for(let i=0;i<n;i++) e[i]+=dt*v[i]*v[i];
    // Simultaneous update, no iteration-order artifacts.
    const next=Array(n).fill(0);
    for(let i=0;i<n;i++) {
      let sum=0;
      for(let j=0;j<n;j++) sum+=model.G[i][j]*v[j];
      next[i]=v[i]-dt*sum/model.C[i];
    }
    for(let i=0;i<n;i++) v[i]=next[i];
  }
  return e;
}

export function writeExperience(model, branch) {
  const changed=copyModel(model), elig=voltageEligibility(model,branch);
  const total=elig.reduce((a,b)=>a+b,0), delta=[];
  for(let i=0;i<elig.length;i++) {
    const d=BUDGET*elig[i]/total;
    delta.push(d);
    changed.G[i][i]+=d;
    changed.leak[i]+=d;
  }
  return {changed, delta};
}

function solveFrequency(model, w) {
  const n=model.C.length, nr=4, a=[], b=[];
  for(let i=0;i<n;i++) {
    const re=Array(n+nr).fill(0),im=Array(n+nr).fill(0);
    for(let j=0;j<n;j++) re[j]=model.G[i][j];
    im[i]=w*model.C[i];
    for(let j=0;j<nr;j++) if(i===TIPS[j]) re[n+j]=1;
    a.push(re);b.push(im);
  }
  for(let k=0;k<n;k++) {
    let best=k, bestMagnitude=-1;
    for(let i=k;i<n;i++) {
      const p=a[i][k]*a[i][k]+b[i][k]*b[i][k];
      if(p>bestMagnitude) {best=i;bestMagnitude=p;}
    }
    if(bestMagnitude<1e-28) throw new Error('Singular cable transfer matrix');
    if(best!==k) {
      [a[best],a[k]]=[a[k],a[best]];
      [b[best],b[k]]=[b[k],b[best]];
    }
    const pr=a[k][k], pi=b[k][k], denom=pr*pr+pi*pi;
    for(let j=k;j<n+nr;j++) {
      const x=a[k][j], y=b[k][j];
      a[k][j]=(x*pr+y*pi)/denom;
      b[k][j]=(y*pr-x*pi)/denom;
    }
    for(let i=0;i<n;i++) if(i!==k) {
      const fr=a[i][k],fi=b[i][k];
      for(let j=k;j<n+nr;j++) {
        const x=a[k][j],y=b[k][j];
        a[i][j]-=fr*x-fi*y;
        b[i][j]-=fr*y+fi*x;
      }
    }
  }
  return Array.from({length:nr},(_,j)=>[a[0][n+j],b[0][n+j]]);
}

export function transfers(model, freq=FREQ) {
  return freq.map(w=>solveFrequency(model,w));
}

export function logResponseChange(before, after) {
  return after.map((arr,i)=>arr.map(([re,im],j)=>{
    const a=Math.hypot(re,im), b=Math.hypot(...before[i][j]);
    return Math.log(a+1e-12)-Math.log(b+1e-12);
  }));
}
