"""Compile owned targets, retain native evidence, and compare independent models."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import random
import shlex
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SEED = 0x524C2026
FIXTURES = {
    'checksum': {
        'title': 'Bounded checksum', 'subtitle': 'Two accumulators. One hidden bound.',
        'contract': 'Fletcher-16 over the first 32 bytes. Two sums modulo 255; high byte is the cumulative sum. Returns zero for empty input.',
        'question': 'Where does accumulation stop, and which modulus governs overflow?',
        'claims': [
            {'title': 'The window ends at 32 bytes', 'detail': 'The reference applies min(length, 32). Directed cases at 31, 32, 33 and 64 bytes test the boundary.', 'basis': 'Source-derived contract + differential cases'},
            {'title': 'A weighted sum reconstructs the second accumulator', 'detail': 'Each byte contributes once to the first sum and once for each remaining position to the second. The candidate uses a weighted sum instead of the C loop.', 'basis': 'Agent-authored algebraic interpretation'},
        ],
        'uncertainty': 'Sampled agreement does not establish equivalence for every byte sequence. No decompiler was exercised for this fixture.',
        'candidates': ['reconstruct'],
    },
    'packet': {
        'title': 'Binary packet decoder', 'subtitle': 'Byte order leaves a fingerprint.',
        'contract': 'A5 | kind (0..7) | sequence (big endian, 16 bits) | payload length | payload | sum8. Errors 1..5 follow validation order. Success packs bit31, kind, sequence and payload sum.',
        'question': 'Which byte order reconstructs sequence identity without breaking validation?',
        'claims': [
            {'title': 'Sequence is big endian', 'detail': 'Asymmetric sequences such as 0x1234 distinguish byte orders. The deliberate little-endian mutant passes symmetric values but fails these cases.', 'basis': 'Source-derived contract + observed counterexamples'},
            {'title': 'Validation order is observable', 'detail': 'Short inputs fail before magic, kind, length and checksum checks. Malformed seeded packets exercise the error paths.', 'basis': 'Source-derived contract + differential cases'},
        ],
        'uncertainty': 'The wire contract is authored for this lab. This does not identify a real-world protocol or prove behavior outside the 64-byte harness domain.',
        'candidates': ['reconstruct', 'faulty_endian'],
    },
    'fsm': {
        'title': 'Lock state machine', 'subtitle': 'History matters more than the last byte.',
        'contract': 'States: locked, armed, open, fault. Events: timeout=0, arm=1, unlock=2, reset=3. Unknown events fault; only reset exits fault. Packs invalid count, state-change count and final state.',
        'question': 'Is fault sticky, and can a transition-table candidate reproduce the history?',
        'claims': [
            {'title': 'Fault is sticky until reset', 'detail': 'An unlock from locked faults. Later arm/unlock events do not recover; reset restores locked. Directed traces distinguish this from a last-event classifier.', 'basis': 'Source-derived contract + directed traces'},
            {'title': 'Transitions and invalid inputs are separate counts', 'detail': 'Repeated unknown events increment the invalid counter without necessarily changing state. A table model reproduces the branch-based reference.', 'basis': 'Agent-authored table interpretation + differential cases'},
        ],
        'uncertainty': 'Only sequences up to 64 bytes are tested. There is no runtime tracing, timing analysis, or exhaustive state-space proof.',
        'candidates': ['reconstruct'],
    },
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True,
                          timeout=60, **kwargs)


def packet(kind, sequence, payload):
    header = bytes([0xA5, kind, sequence >> 8, sequence & 255, len(payload)])
    body = header + payload
    return body + bytes([sum(body) & 255])


def cases_for(name, seed=SEED, count=600):
    rng = random.Random(seed)
    if name == 'checksum':
        directed = [('empty', b'')]
        for length in [1, 2, 31, 32, 33, 64]:
            for value in [0, 1, 254, 255]:
                directed.append((f'length-{length}-byte-{value}', bytes([value]) * length))
        directed.append(('ramp', bytes(range(64))))
    elif name == 'packet':
        directed = [('empty', b''), ('short-header', b'\xa5\x01')]
        for length in [0, 1, 2, 31, 58]:
            for seq in [0, 1, 255, 256, 0x1234, 65535]:
                directed.append((f'valid-length-{length}-seq-{seq}', packet(3, seq, bytes([255]) * length)))
        good = packet(7, 0x1234, b'\x00\xff')
        for index, value, label in [(0, 0, 'bad-magic'), (1, 8, 'bad-kind'), (4, 3, 'bad-length'), (len(good)-1, 0, 'bad-checksum')]:
            modified = bytearray(good); modified[index] = value
            directed.append((label, bytes(modified)))
        directed += [('trailing-byte', good + b'\x00'), ('truncated', good[:-1])]
    elif name == 'fsm':
        directed = [('empty', b''), ('unlock-path', bytes([1, 2])),
                    ('sticky-fault', bytes([2, 1, 2])), ('fault-reset', bytes([2, 3, 1, 2])),
                    ('timeout', bytes([1, 0, 2])), ('long-invalid', bytes([255]) * 64)]
        directed += [(f'pair-{a}-{b}', bytes([a, b])) for a in range(5) for b in range(5)]
        directed += [(f'length-{n}', bytes([1, 2, 3, 0]) * (n // 4) + bytes([1] * (n % 4))) for n in [31, 32, 33, 63, 64]]
    else:
        raise ValueError('Unknown fixture')
    result = [{'id': f'boundary-{i:03d}', 'label': label, 'hex': value.hex(), 'group': 'boundary'} for i, (label, value) in enumerate(directed)]
    for i in range(count):
        if name == 'packet' and i % 3 != 0:
            data = packet(rng.randrange(8), rng.randrange(65536), bytes(rng.randrange(256) for _ in range(rng.randrange(59))))
            if i % 3 == 2:
                data = bytearray(data); data[rng.randrange(len(data))] ^= 1; data = bytes(data)
        elif name == 'fsm':
            data = bytes(rng.randrange(5) for _ in range(rng.randrange(65)))
        else:
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(65)))
        result.append({'id': f'seeded-{i:04d}', 'label': f'Seeded input {i + 1}', 'hex': data.hex(), 'group': 'seeded'})
    return result


def oracle(executable, cases):
    response = run([str(executable)], input=''.join((case['hex'] or '-') + '\n' for case in cases))
    if response.returncode:
        raise RuntimeError(f'Reference exited {response.returncode}: {response.stderr}')
    lines = response.stdout.splitlines()
    if len(lines) != len(cases) or any(not line.isdecimal() for line in lines):
        raise RuntimeError('Invalid oracle response: expected one unsigned integer per case')
    values = [int(line) for line in lines]
    if any(value > 0xFFFFFFFF for value in values):
        raise RuntimeError('Oracle output outside uint32 range')
    return values


def evidence(args):
    tool = shutil.which(args[0])
    if not tool:
        return {'command': shlex.join(args), 'status': 'unavailable', 'output': '', 'error': 'Tool not found on PATH', 'exitCode': None}
    response = run([tool, *args[1:]])
    return {'command': shlex.join(args), 'toolPath': tool,
            'status': 'available' if response.returncode == 0 else 'unsupported',
            'output': response.stdout.replace(str(ROOT), '.'),
            'error': response.stderr.replace(str(ROOT), '.'), 'exitCode': response.returncode}


def generate(names=None, seed=SEED, count=600, output=None):
    compiler = shutil.which(os.environ.get('CC', 'clang'))
    if not compiler:
        raise RuntimeError('Clang not found. Install command-line developer tools or set CC.')
    version = run([compiler, '--version'])
    if version.returncode:
        raise RuntimeError('Cannot read compiler version')
    build = ROOT / 'build'; build.mkdir(exist_ok=True)
    dataset = {'schemaVersion': 1, 'recording': 'Locally generated evidence recording',
               'generatedAt': datetime.now(timezone.utc).isoformat(),
               'platform': {'system': platform.system(), 'architecture': platform.machine(), 'release': platform.release()},
               'compiler': {'path': compiler, 'version': version.stdout.strip()},
               'pythonVersion': platform.python_version(), 'caseGenerator': 'Python random.Random; randrange byte generation; directed cases precede seeded cases',
               'seed': seed, 'randomCases': count, 'fixtures': [],
               'providers': [{'name': 'REA', 'status': 'unexercised', 'detail': 'No REA provider execution in this baseline recording. Optional CLI analysis can attach a version-bound record.'},
                             {'name': 'Ghidra', 'status': 'unexercised', 'detail': 'No Ghidra recording in this baseline generation. Run the optional decompiler adapter for the stripped packet.'}]}
    for name in names or FIXTURES:
        spec = FIXTURES[name]
        source = ROOT / 'fixtures' / f'{name}.c'
        model = ROOT / 'reconstructions' / f'{name}.py'
        harness = ROOT / 'fixtures' / 'harness.c'
        module = importlib.import_module(f'reconstructions.{name}')
        cases = cases_for(name, seed, count)
        fixture = {'id': name, **spec, 'source': {'path': f'fixtures/{name}.c', 'text': source.read_text(), 'sha256': digest(source.read_bytes())},
                   'reconstruction': {'path': f'reconstructions/{name}.py', 'text': model.read_text(), 'sha256': digest(model.read_bytes()), 'authorship': 'Agent-authored Python; reference source known. Not decompiler output.'},
                   'variants': []}
        for optimization in ['O0', 'O2']:
            relative = f'build/{name}-{optimization}'
            command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-g', f'-{optimization}', f'fixtures/{name}.c', 'fixtures/harness.c', '-o', relative]
            compiled = run(command)
            if compiled.returncode:
                raise RuntimeError(f'Compilation failed: {compiled.stderr}')
            executable = ROOT / relative
            expected = oracle(executable, cases)
            reports = []
            for candidate in spec['candidates']:
                function = getattr(module, candidate)
                rows = []
                for case, reference in zip(cases, expected):
                    actual = function(bytes.fromhex(case['hex']))
                    rows.append({**case, 'expected': reference, 'actual': actual, 'passed': reference == actual})
                failed = sum(not case['passed'] for case in rows)
                reports.append({'id': candidate, 'title': 'Recovered candidate' if candidate == 'reconstruct' else 'Endian fault (deliberate)',
                                'intentionalFault': candidate != 'reconstruct', 'passed': len(rows)-failed, 'failed': failed,
                                'total': len(rows), 'cases': rows, 'seed': seed,
                                'caseDigest': digest(json.dumps(cases, sort_keys=True).encode()),
                                'rerun': f'python3 -m lab.pipeline verify --fixture {name} --variant {optimization} --candidate {candidate} --seed {seed} --count {count}'})
            disassembler = shutil.which('llvm-objdump') or shutil.which('objdump') or 'objdump'
            version_output = run([disassembler, '--version']) if shutil.which(disassembler) else None
            is_llvm = version_output and 'llvm' in version_output.stdout.lower()
            symbol = '_evaluate' if platform.system() == 'Darwin' else 'evaluate'
            symbol_flag = f'--disassemble-symbols={symbol}' if is_llvm else f'--disassemble={symbol}'
            static = {'disassembly': evidence([disassembler, '-d', '--no-show-raw-insn', symbol_flag, relative]),
                      'symbols': evidence(['nm', '-n', relative]),
                      'artifact': evidence(['file', relative]),
                      'locations': evidence([disassembler, '-d', '--line-numbers', symbol_flag, relative])}
            fixture['variants'].append({'id': optimization, 'artifact': relative, 'sha256': digest(executable.read_bytes()), 'size': executable.stat().st_size,
                                       'command': shlex.join(command), 'disassemblerVersion': version_output.stdout.strip() if version_output else 'Unavailable', 'flags': command[1:7], 'harnessSha256': digest(harness.read_bytes()), 'evidence': static, 'reports': reports})
        dataset['fixtures'].append(fixture)
    destination = Path(output) if output else ROOT / 'web/data/report.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(dataset, indent=2) + '\n')
    temporary.replace(destination)
    return dataset


def verify(fixture, variant, candidate, seed, count, case_id=None):
    if fixture not in FIXTURES or candidate not in FIXTURES[fixture]['candidates'] or variant not in ['O0', 'O2', 'O2-stripped']:
        raise ValueError('Unknown fixture, variant, or candidate')
    recording = json.loads((ROOT / 'web/data/report.json').read_text())
    found = next((f for f in recording['fixtures'] if f['id'] == fixture), None)
    if found is None:
        raise ValueError('Fixture absent from recording; run generate first')
    compiled = next(v for v in found['variants'] if v['id'] == variant)
    executable = ROOT / compiled['artifact']
    if not executable.exists() or digest(executable.read_bytes()) != compiled['sha256']:
        raise ValueError('Executable missing or changed; run generate first')
    for path, expected_hash in [(ROOT / found['reconstruction']['path'], found['reconstruction']['sha256']),
                                (ROOT / found['source']['path'], found['source']['sha256']),
                                (ROOT / 'fixtures/harness.c', compiled['harnessSha256'])]:
        if digest(path.read_bytes()) != expected_hash:
            raise ValueError('Source or candidate changed; run generate first')
    cases = cases_for(fixture, seed, count)
    stored_report = next(r for r in compiled['reports'] if r['id'] == candidate)
    if seed == stored_report['seed'] and count == recording['randomCases']:
        if digest(json.dumps(cases, sort_keys=True).encode()) != stored_report['caseDigest']:
            raise ValueError('Case generator changed; run generate first')
    if case_id:
        cases = [case for case in cases if case['id'] == case_id]
        if not cases:
            raise ValueError('Case ID absent from this seed/count')
    function = getattr(importlib.import_module(f'reconstructions.{fixture}'), candidate)
    values = oracle(executable, cases)
    failures = [{**case, 'expected': expected, 'actual': function(bytes.fromhex(case['hex']))}
                for case, expected in zip(cases, values) if expected != function(bytes.fromhex(case['hex']))]
    return {'total': len(cases), 'passed': len(cases) - len(failures), 'failed': len(failures), 'failures': failures,
            'seed': seed, 'artifactSha256': compiled['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['generate', 'verify'])
    parser.add_argument('--fixture', choices=list(FIXTURES))
    parser.add_argument('--variant', choices=['O0', 'O2', 'O2-stripped'], default='O2')
    parser.add_argument('--candidate', default='reconstruct')
    parser.add_argument('--case')
    parser.add_argument('--seed', type=lambda x: int(x, 0), default=SEED)
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--output')
    args = parser.parse_args()
    if not 0 <= args.count <= 100000:
        parser.error('--count must be 0..100000')
    try:
        if args.action == 'generate':
            data = generate([args.fixture] if args.fixture else None, args.seed, args.count, args.output)
            for fixture in data['fixtures']:
                for variant in fixture['variants']:
                    for report in variant['reports']:
                        print(f"{fixture['id']} {variant['id']} {report['id']}: {report['passed']}/{report['total']} passed, {report['failed']} failed")
            unexpected = any((r['failed'] == 0 if r['intentionalFault'] else r['failed'] > 0)
                             for f in data['fixtures'] for v in f['variants'] for r in v['reports'])
            return 1 if unexpected else 0
        else:
            if not args.fixture:
                parser.error('verify requires --fixture')
            result = verify(args.fixture, args.variant, args.candidate, args.seed, args.count, args.case)
            print(json.dumps(result, indent=2))
            return 1 if result['failed'] else 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f'Error: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
