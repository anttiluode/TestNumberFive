import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {transfers,writeExperience,logResponseChange} from '../web/engine.mjs';
const ref=JSON.parse(readFileSync(new URL('../web/demo.json', import.meta.url),'utf8'));
const before=transfers(ref);
for(let i=0;i<8;i++)for(let j=0;j<4;j++)for(let k=0;k<2;k++){
  assert.ok(Math.abs(before[i][j][k]-ref.reference.before[i][j][k])<1e-9, 'pre-transfer parity');
}
for(let arm=0;arm<4;arm++){
  const {changed,delta}=writeExperience(ref,arm);
  assert.ok(Math.abs(delta.reduce((a,b)=>a+b)-.65)<1e-12);
  const expected=ref.reference.after[arm];
  const resp=transfers(changed);
  for(let i=0;i<8;i++)for(let j=0;j<4;j++)for(let k=0;k<2;k++){
    assert.ok(Math.abs(resp[i][j][k]-expected[i][j][k])<1e-9,`after parity ${arm} ${i} ${j} ${k}`);
  }
  const fingerprint=logResponseChange(before,resp);
  assert.ok(fingerprint.flat().some(x=>Math.abs(x)>.01));
}
console.log('Browser / NumPy complex transfer, local plasticity and sham parity: PASS');
