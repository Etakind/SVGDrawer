/* Test worker-start fallback without a network/runtime dependency.
 * Run: node tests/runtime_fallback.js
 * This does not test the actual CDN or Pyodide package.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../app/runtime.js'), 'utf8');

async function check(Worker) {
  const sandbox = {Worker, location:{protocol:'file:'}, Blob,
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}}, setTimeout,clearTimeout,console};
  vm.createContext(sandbox);
  vm.runInContext(source + '\nthis.EngineUnderTest=PythonEngine;', sandbox);
  const engine = new sandbox.EngineUnderTest({files:{},gallery:{settings:{pyodide_base:'https://invalid.example/'}}},()=>{});
  let fallback = 0;
  engine.initializeMainThread = async function(){fallback++;this.mode='pyodide-main';};
  await engine.initialize();
  assert.equal(fallback, 1);
  assert.equal(engine.ready, true);
  assert.equal(engine.worker, null);
  assert.equal(engine.mode, 'pyodide-main');
  assert.equal(engine.pending.size, 0);
}
(async()=>{
  await check(class {constructor(){throw new Error('Module worker blocked synchronously');}});
  await check(class {
    postMessage(){setTimeout(()=>this.onerror({message:'Module worker startup blocked'}),0);}
    terminate(){}
  });
  console.log('PASS: synchronous and asynchronous module-worker failures use the same-Python compatibility path.');
})().catch(error=>{console.error(error);process.exitCode=1;});
