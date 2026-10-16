// Validate external report data before rendering; importing never executes code.
export function validateReport(data) {
  const fail = () => { throw new Error('This is not a valid ReverseLab comparison report. Use the JSON downloaded by the local runner.'); };
  const uint = value => Number.isInteger(value) && value >= 0 && value <= 0xffffffff;
  const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
  const text = (value, max) => typeof value === 'string' && value.length <= max;
  if (!data || data.format !== 'reverselab-comparison' || data.schemaVersion !== 1 ||
      !Array.isArray(data.cases) || data.cases.length < 1 || data.cases.length > 256 ||
      !text(data.createdAt, 80) || !Number.isFinite(Date.parse(data.createdAt)) ||
      !text(data.contract, 200) || !hash(data.harnessSha256) || !hash(data.caseDigest)) fail();
  for (const source of [data.reference, data.candidate]) {
    if (!source || !text(source.name, 120) || !hash(source.sha256) || !text(source.entryPoint, 64)) fail();
  }
  if (!hash(data.reference.artifactSha256)) fail();
  const ids = new Set();
  for (const row of data.cases) {
    if (!row || !text(row.id, 80) || ids.has(row.id) || !text(row.label, 120) ||
        !['supplied','random'].includes(row.group) || typeof row.hex !== 'string' || !/^(?:[0-9a-f]{2}){0,64}$/.test(row.hex) ||
        !uint(row.expected) || !(row.actual === null || uint(row.actual)) ||
        !(row.error === null || (text(row.error, 1000) && row.error.length > 0)) ||
        (row.error === null) !== (row.actual !== null) ||
        row.passed !== (row.error === null && row.expected === row.actual)) fail();
    ids.add(row.id);
  }
  if (data.total !== data.cases.length || data.failed !== data.cases.filter(row => !row.passed).length ||
      data.passed !== data.total - data.failed || data.errors !== data.cases.filter(row => row.error !== null).length) fail();
  if (!data.environment || !text(data.environment.system, 50) || !text(data.environment.architecture, 50) ||
      !text(data.environment.python, 50) || !text(data.environment.compiler, 2000) ||
      !Array.isArray(data.environment.compilerFlags) || data.environment.compilerFlags.length > 30 ||
      !data.environment.compilerFlags.every(flag => text(flag, 200))) fail();
  if (!data.generation || !uint(data.generation.seed) || !Number.isInteger(data.generation.randomCount) ||
      data.generation.randomCount < 0 || data.generation.randomCount > 200 || data.generation.maxBytes !== 64 ||
      !text(data.generation.algorithm, 200) ||
      data.cases.filter(row => row.group === 'random').length !== data.generation.randomCount) fail();
  if (!data.diagnostics || !['compiler','reference','candidate'].every(key => text(data.diagnostics[key], 6000))) fail();
  return data;
}
export function parseInputText(text) {
  const lines = text.split(/\r?\n/);
  let count = 0;
  lines.forEach((line, index) => {
    const value = line.replace(/\s/g, '');
    if (!value) return;
    if (value !== '-' && !/^(?:[a-f0-9]{2}){1,64}$/i.test(value))
      throw new Error(`Input line ${index + 1}: use up to 64 complete hex bytes, or - for empty input.`);
    count++;
  });
  return count;
}
