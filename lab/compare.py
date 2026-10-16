"""Compare trusted local C and Python byte-processing functions on supplied inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE = 256 * 1024
MAX_CASES = 256
MAX_BYTES = 64

class CompareError(ValueError):
    def __init__(self, message, stage='input'):
        super().__init__(message)
        self.stage = stage


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_inputs(text, count=0, seed=42):
    if type(count) is not int or not 0 <= count <= 200:
        raise CompareError('Random input count must be an integer from 0 to 200.')
    if type(seed) is not int or not 0 <= seed <= 0xffffffff:
        raise CompareError('Seed must be an integer from 0 to 4294967295.')
    if not isinstance(text, str) or len(text) > 50000:
        raise CompareError('Inputs must be text, up to 50,000 characters.')
    cases = []
    for number, line in enumerate(text.splitlines(), 1):
        value = ''.join(line.split())
        if not value:
            continue
        if value == '-':
            value = ''
        elif not re.fullmatch(r'(?:[0-9a-fA-F]{2})+', value):
            raise CompareError('Input line %s: use complete hex bytes, or - for empty input.' % number)
        if len(value) > MAX_BYTES * 2:
            raise CompareError('Input line %s exceeds 64 bytes.' % number)
        cases.append({'id': 'input-%s' % number, 'label': 'Input line %s' % number,
                      'hex': value.lower(), 'group': 'supplied'})
    rng = random.Random(seed)
    for index in range(count):
        length = rng.randrange(MAX_BYTES + 1)
        value = bytes(rng.randrange(256) for _ in range(length))
        cases.append({'id': 'random-%s' % (index + 1), 'label': 'Random input %s' % (index + 1),
                      'hex': value.hex(), 'group': 'random'})
    if not 1 <= len(cases) <= MAX_CASES:
        raise CompareError('Provide between 1 and 256 total inputs, including generated inputs.')
    return cases


def run_limited(command, directory, stage, input_text='', timeout=5):
    """File-backed output avoids unbounded capture; timeouts kill the process group."""
    with tempfile.TemporaryFile() as incoming, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        incoming.write(input_text.encode()); incoming.seek(0)
        wrapper = [sys.executable, '-I', str(ROOT / 'lab/process_worker.py'), str(timeout), *command]
        process = subprocess.Popen(wrapper, cwd=str(directory), stdin=incoming, stdout=out,
                                   stderr=err, start_new_session=True)
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Also reap background children when the direct process exits early.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        out.seek(0); err.seek(0)
        stdout = out.read(1024 * 1024).decode('utf-8', errors='replace')
        stderr = err.read(1024 * 1024).decode('utf-8', errors='replace')
        if timed_out:
            raise CompareError('%s timed out after %s seconds. Check for an infinite loop.' % (stage, timeout), stage)
        if process.returncode:
            detail = stderr[-6000:].strip() or 'Process exited with code %s.' % process.returncode
            raise CompareError('%s failed. %s' % (stage, detail), stage)
        return stdout, stderr[-6000:]


def compare(reference, candidate, inputs, function='evaluate', count=0, seed=42,
            reference_name='reference.c', candidate_name='candidate.py'):
    if platform.system() not in ('Darwin', 'Linux'):
        raise CompareError('The local runner supports macOS and Linux.', 'setup')
    for name, value in [('C reference', reference), ('Python rewrite', candidate)]:
        if not isinstance(value, str) or not value.strip() or len(value.encode()) > MAX_SOURCE:
            raise CompareError('%s must contain source code, up to 256 KiB.' % name)
    if not isinstance(function, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,63}', function):
        raise CompareError('Python function must be a simple name, such as evaluate or reconstruct.')
    cases = parse_inputs(inputs, count, seed)
    compiler = shutil.which(os.environ.get('CC', 'clang'))
    if not compiler:
        raise CompareError('Clang was not found. Install your platform’s command-line developer tools, or set CC.', 'setup')
    with tempfile.TemporaryDirectory(prefix='reverselab-') as temporary:
        directory = Path(temporary)
        (directory / 'reference.c').write_text(reference)
        (directory / 'candidate.py').write_text(candidate)
        harness = (ROOT / 'fixtures/harness.c').read_bytes()
        (directory / 'harness.c').write_bytes(harness)
        executable = str(directory / 'reference')
        flags = ['-std=c11', '-Wall', '-Wextra', '-O2', 'reference.c', 'harness.c', '-o', 'reference']
        _, warnings = run_limited([compiler, *flags], directory, 'C compilation', timeout=15)
        version, _ = run_limited([compiler, '--version'], directory, 'Compiler identification')
        stream = ''.join((case['hex'] or '-') + '\n' for case in cases)
        output, native_stderr = run_limited([executable], directory, 'C execution', stream)
        lines = output.splitlines()
        if len(lines) != len(cases) or any(not re.fullmatch(r'[0-9]+', line) or len(line) > 10 or int(line) > 0xffffffff for line in lines):
            raise CompareError('C output did not match the harness protocol. evaluate() must return uint32_t and must not print to stdout.', 'C execution')
        output, python_stderr = run_limited([sys.executable, '-I', str(ROOT / 'lab/candidate_worker.py'),
                                           str(directory / 'candidate.py'), function], directory, 'Python execution', stream)
        try:
            outcomes = [json.loads(line) for line in output.splitlines()]
            if len(outcomes) != len(cases):
                raise ValueError('Wrong output count')
            for result in outcomes:
                if not isinstance(result, dict) or set(result) not in ({'value'}, {'error'}):
                    raise ValueError('Invalid candidate response')
                if 'value' in result and (type(result['value']) is not int or not 0 <= result['value'] <= 0xffffffff):
                    raise ValueError('Invalid candidate value')
                if 'error' in result and (not isinstance(result['error'], str) or len(result['error']) > 1000):
                    raise ValueError('Invalid candidate error')
        except (ValueError, TypeError):
            raise CompareError('Python output did not match the runner protocol. Avoid writing directly to stdout.', 'Python execution')
        rows = []
        for case, line, result in zip(cases, lines, outcomes):
            expected = int(line)
            actual = result.get('value')
            rows.append(dict(case, expected=expected, actual=actual, error=result.get('error'),
                             passed=actual == expected and 'error' not in result))
        failed = sum(not row['passed'] for row in rows)
        return {'format': 'reverselab-comparison', 'schemaVersion': 1,
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'contract': 'bytes[0..64] -> uint32; sampled comparison, not a proof of equivalence',
                'reference': {'name': Path(reference_name).name[:120], 'sha256': sha(reference.encode()),
                              'entryPoint': 'evaluate', 'artifactSha256': sha(Path(executable).read_bytes())},
                'candidate': {'name': Path(candidate_name).name[:120], 'sha256': sha(candidate.encode()), 'entryPoint': function},
                'harnessSha256': sha(harness),
                'environment': {'system': platform.system(), 'architecture': platform.machine(),
                                'python': platform.python_version(), 'compiler': version.strip()[:2000],
                                'compilerFlags': flags},
                'generation': {'randomCount': count, 'seed': seed, 'maxBytes': MAX_BYTES,
                               'algorithm': 'Python random.Random; length and bytes with randrange'},
                'caseDigest': sha(json.dumps(cases, sort_keys=True).encode()),
                'diagnostics': {'compiler': warnings, 'reference': native_stderr, 'candidate': python_stderr},
                'total': len(rows), 'passed': len(rows) - failed, 'failed': failed,
                'errors': sum(row['error'] is not None for row in rows), 'cases': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog='Runs trusted code with your account permissions. Resource limits are not a security sandbox.')
    parser.add_argument('--reference', type=Path, required=True, help='C source exporting uint32_t evaluate(const uint8_t *, size_t)')
    parser.add_argument('--candidate', type=Path, required=True, help='Python file exporting evaluate(data: bytes) -> int')
    parser.add_argument('--inputs', type=Path, required=True, help='One hex byte sequence per line; - for empty')
    parser.add_argument('--function', default='evaluate')
    parser.add_argument('--random-count', type=int, default=0)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('comparison.json'))
    args = parser.parse_args()
    try:
        # Check size before reading files into memory.
        for path in (args.reference, args.candidate):
            if path.stat().st_size > MAX_SOURCE:
                raise CompareError('Source file exceeds 256 KiB.')
        if args.inputs.stat().st_size > 50000:
            raise CompareError('Input file exceeds 50,000 bytes.')
        result = compare(args.reference.read_text(), args.candidate.read_text(), args.inputs.read_text(),
                         args.function, args.random_count, args.seed, args.reference.name, args.candidate.name)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    except (OSError, ValueError) as error:
        print('Cannot compare: %s' % error, file=sys.stderr)
        raise SystemExit(2)
    print('%s inputs: %s agree, %s differ (%s Python errors). Report: %s' %
          (result['total'], result['passed'], result['failed'], result['errors'], args.output))
    raise SystemExit(1 if result['failed'] else 0)

if __name__ == '__main__':
    main()
