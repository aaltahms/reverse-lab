import test from 'node:test';
import assert from 'node:assert/strict';
import {validateReport, parseInputText} from '../web/comparison-report.mjs';
const hash = 'a'.repeat(64);
function report() {
  return {format:'reverselab-comparison',schemaVersion:1,createdAt:'2026-10-15T12:00:00Z',contract:'bytes -> uint32',
    reference:{name:'ref.c',sha256:hash,artifactSha256:hash,entryPoint:'evaluate'},
    candidate:{name:'candidate.py',sha256:hash,entryPoint:'evaluate'},harnessSha256:hash,caseDigest:hash,
    environment:{system:'Linux',architecture:'x86_64',python:'3.13',compiler:'clang',compilerFlags:['-O2']},
    generation:{seed:42,randomCount:0,maxBytes:64,algorithm:'test'},diagnostics:{compiler:'',reference:'',candidate:''},
    total:2,passed:1,failed:1,errors:0,cases:[
      {id:'input-1',label:'Input line 1',hex:'',group:'supplied',expected:0,actual:0,error:null,passed:true},
      {id:'input-2',label:'Input line 2',hex:'ffff',group:'supplied',expected:254,actual:510,error:null,passed:false}]};
}
test('accepts a complete comparison report', () => assert.equal(validateReport(report()).failed, 1));
test('accepts per-case Python errors', () => { const r=report(); r.cases[1].actual=null; r.cases[1].error='ValueError: bad'; r.errors=1; assert.equal(validateReport(r).errors,1); });
test('rejects forged agreement and summary counts', () => {
  for (const mutate of [r=>r.cases[1].passed=true,r=>r.failed=0,r=>r.total=3,r=>r.passed=2,r=>r.errors=1]) {
    const r=report(); mutate(r); assert.throws(()=>validateReport(r));
  }
});
test('rejects invalid bytes, outputs, IDs and null/error combinations', () => {
  for (const mutate of [r=>r.cases[1].hex='x',r=>r.cases[1].hex='aa'.repeat(65),r=>r.cases[1].actual=-1,
    r=>r.cases[1].actual=true,r=>r.cases[1].actual=null,r=>r.cases[1].error='bad',r=>r.cases[1].id='input-1']) {
    const r=report(); mutate(r); assert.throws(()=>validateReport(r));
  }
});
test('rejects incompatible formats and incomplete metadata', () => {
  for (const mutate of [r=>r.schemaVersion=2,r=>delete r.reference,r=>r.candidate.sha256='bad',r=>delete r.environment,
    r=>r.generation.randomCount=2,r=>r.diagnostics.candidate='x'.repeat(6001)]) {
    const r=report(); mutate(r); assert.throws(()=>validateReport(r));
  }
});
test('parses spaced hex, blank lines and empty input markers', () => assert.equal(parseInputText('-\n\nFF ff\n01 02'),3));
test('identifies invalid input line and byte limit', () => {
  assert.throws(()=>parseInputText('-\na'),/line 2/);
  assert.throws(()=>parseInputText('aa'.repeat(65)),/64/);
});
