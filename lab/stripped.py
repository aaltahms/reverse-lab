"""Derive one stripped -O2 artifact and verify it against its symbol-bearing twin."""
import argparse
import importlib
import json
import platform
import re
import shlex
from lab.pipeline import ROOT, FIXTURES, cases_for, digest, evidence, oracle


def symbol_range(output, symbol):
    entries = []
    for line in output.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+)\s+[Tt]\s+(\S+)', line.strip())
        if match:
            entries.append((int(match[1],16),match[2]))
    entries.sort()
    matches = [(address, index) for index,(address,name) in enumerate(entries) if name==symbol]
    if len(matches)!=1:
        raise ValueError('Cannot select a unique evaluate symbol in the reference twin')
    start,index = matches[0]
    if index+1 >= len(entries):
        raise ValueError('No following text symbol to bound evaluate')
    return start,entries[index+1][0]


def add_variant(name='packet', report_path=None):
    path = report_path or ROOT/'web/data/report.json'
    recording = json.loads(path.read_text())
    fixture = next(f for f in recording['fixtures'] if f['id']==name)
    base = next(v for v in fixture['variants'] if v['id']=='O2')
    original = ROOT/base['artifact']
    if digest(original.read_bytes())!=base['sha256']:
        raise ValueError('Reference artifact changed; run generate first')
    for source,sha in [(fixture['source']['path'],fixture['source']['sha256']),
                       (fixture['reconstruction']['path'],fixture['reconstruction']['sha256']),
                       ('fixtures/harness.c',base['harnessSha256'])]:
        if digest((ROOT/source).read_bytes())!=sha:
            raise ValueError('Reference or candidate source changed; run generate first')
    cases = cases_for(name,recording['seed'],recording['randomCases'])
    case_digest = digest(json.dumps(cases,sort_keys=True).encode())
    if case_digest!=base['reports'][0]['caseDigest']:
        raise ValueError('Case generator changed; run generate first')
    symbol = '_evaluate' if platform.system()=='Darwin' else 'evaluate'
    begin,end = symbol_range(base['evidence']['symbols']['output'],symbol)
    relative = f'build/{name}-O2-stripped'
    strip = evidence(['strip','-o',relative,base['artifact']])
    if strip['status']!='available':
        raise RuntimeError(f"Stripping failed: {strip['error']}")
    steps = [strip['command']]
    signing = None
    if platform.system()=='Darwin':
        signing = evidence(['codesign','--force','--sign','-',relative])
        if signing['status']!='available':
            raise RuntimeError(f"Ad-hoc signing failed: {signing['error']}")
        steps.append(signing['command'])
    executable = ROOT/relative
    symbols = evidence(['nm','-n',relative])
    if any(line.split()[-1:]==[symbol] for line in symbols['output'].splitlines()):
        raise ValueError('evaluate name remains in stripped symbol table')
    expected = oracle(executable,cases)
    twin = oracle(original,cases)
    if expected!=twin or twin!=[c['expected'] for c in base['reports'][0]['cases']]:
        raise ValueError('Stripped behavior or recorded twin outputs differ')
    module = importlib.import_module(f'reconstructions.{name}')
    reports = []
    for report in base['reports']:
        function = getattr(module,report['id'])
        rows = []
        for case,reference in zip(cases,expected):
            actual = function(bytes.fromhex(case['hex']))
            rows.append({**case,'expected':reference,'actual':actual,'passed':reference==actual})
        failed = sum(not row['passed'] for row in rows)
        reports.append({**report,'passed':len(rows)-failed,'failed':failed,'cases':rows,
                        'rerun':report['rerun'].replace('--variant O2 ','--variant O2-stripped ')})
    disassembler = base['evidence']['disassembly'].get('toolPath','objdump')
    variant = {**base,'id':'O2-stripped','label':'-O2 / stripped','stripped':True,
               'artifact':relative,'sha256':digest(executable.read_bytes()),'size':executable.stat().st_size,
               'command':'\n'.join([base['command'],*steps]),'reports':reports,
               'derivedFrom':{'artifact':base['artifact'],'sha256':base['sha256'],
                              'procedureAddress':hex(begin),'procedureEnd':hex(end),'symbol':symbol,
                              'selection':'Address selected from the symbol-bearing twin; source-known investigation, not blind discovery.'},
               'transformations':{'strip':strip,'signing':signing},
               'evidence':{'disassembly':evidence([disassembler,'-d','--no-show-raw-insn',f'--start-address={hex(begin)}',f'--stop-address={hex(end)}',relative]),
                           'symbols':symbols,'artifact':evidence(['file',relative]),
                           'locations':{'command':'No debug-location query','status':'unavailable','output':'',
                                        'error':'Debug information was stripped. The procedure range came from the symbol-bearing twin, not recovered source locations.','exitCode':None}}}
    fixture['variants']=[v for v in fixture['variants'] if v['id']!='O2-stripped']+[variant]
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(recording,indent=2)+'\n');temporary.replace(path)
    return variant


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',choices=list(FIXTURES),default='packet')
    args=parser.parse_args()
    try:
        variant=add_variant(args.fixture)
    except (ValueError,RuntimeError,OSError,StopIteration) as error:
        parser.exit(2,f'Cannot derive stripped artifact: {error}\n')
    print(f"{variant['artifact']}: {variant['size']} bytes; evaluate symbol removed; twin outputs agree on {variant['reports'][0]['total']} cases")
    for report in variant['reports']:
        print(f"{report['id']}: {report['passed']} passed / {report['failed']} failed")

if __name__=='__main__':
    main()
