import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {packetOutput, explainPacket} from '../web/packet-view.mjs';

const recording = JSON.parse(readFileSync(new URL('../web/data/report.json', import.meta.url)));
const packet = recording.fixtures.find(f => f.id === 'packet');
const build = packet.variants.find(v => v.id === 'O2');
const correct = build.reports.find(r => r.id === 'reconstruct');
const mutant = build.reports.find(r => r.id === 'faulty_endian');

test('readable message number preserves the native packed-word fields', () => {
  assert.deepEqual(packetOutput(0x83123400), {accepted: true, sequence: 4660, kind: 3, payloadSum: 0});
  assert.equal(packetOutput(0x83341200).sequence, 13330);
});

test('invalid recorded values cannot become misleading readable results', () => {
  for (const value of [-1, 2**32, 1.5, NaN, null, '1']) assert.throws(() => packetOutput(value));
});

test('every rejection code explains the error without a decoded message number', () => {
  for (let code = 1; code <= 5; code++) {
    const result = packetOutput(code);
    assert.equal(result.accepted, false);
    assert.equal(result.sequence, null);
    assert.ok(result.reason.length > 15);
  }
  assert.match(packetOutput(5).reason, /checksum/);
});

test('the real asymmetric packet explains the observed disagreement', () => {
  const row = mutant.cases.find(c => c.id === 'boundary-006');
  assert.equal(row.hex, 'a503123400ee');
  const result = explainPacket(row, true);
  assert.equal(result.kind, 'different');
  assert.equal(result.original.sequence, 4660);
  assert.equal(result.replacement.sequence, 13330);
  assert.match(result.detail, /12 34/);
});

test('symmetric bytes warn about a concealed mutant rather than claiming a fix', () => {
  const row = mutant.cases.find(c => c.label === 'valid-length-0-seq-65535');
  assert.equal(explainPacket(row, true).kind, 'hidden');
  assert.equal(explainPacket(row, false).kind, 'agreement');
});

test('checksum rejection is not presented as successful sequence decoding', () => {
  const row = mutant.cases.find(c => c.label === 'bad-checksum');
  const result = explainPacket(row, true);
  assert.equal(result.kind, 'rejected');
  assert.equal(result.original.sequence, null);
  assert.match(result.detail, /checksum/);
});

test('every recorded packet result retains its exact comparison outcome', () => {
  for (const report of [correct, mutant]) {
    for (const row of report.cases) {
      const result = explainPacket(row, report.intentionalFault);
      assert.equal(result.matches, row.passed, row.id);
      assert.equal(result.original.accepted, row.expected >= 2**31);
      assert.equal(result.replacement.accepted, row.actual >= 2**31);
    }
  }
});
