"""Validate the evidence contract and create a portable static explorer export."""
import json
import hashlib
from pathlib import Path
import shutil
from lab.holdout import validate_evaluation

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def validate(data):
    require(data['schemaVersion'] == 1, 'Unsupported schema')
    require(len(data['fixtures']) == 3, 'Release needs three fixtures')
    ids = set()
    for fixture in data['fixtures']:
        require(fixture['id'] not in ids, 'Duplicate fixture')
        ids.add(fixture['id'])
        variant_ids = [v['id'] for v in fixture['variants']]
        require(len(variant_ids)==len(set(variant_ids)), 'Duplicate variant')
        require({'O0','O2'} <= set(variant_ids) <= {'O0','O2','O2-stripped'}, 'Expected native optimization variants')
        for variant in fixture['variants']:
            require(len(variant['sha256']) == 64, 'Invalid artifact hash')
            ghidra=variant['evidence'].get('ghidra')
            if ghidra and ghidra['status']=='available':
                require(ghidra['targetSha256']==variant['sha256'], 'Ghidra target hash mismatch')
                require(ghidra['output'].strip() and ghidra['provider']=='Ghidra', 'Missing Ghidra output/provider')
                require(ghidra['address']==variant['derivedFrom']['procedureAddress'], 'Ghidra procedure mismatch')
            for report in variant['reports']:
                cases = report['cases']
                require(len(cases) == report['total'] > 0, 'Case count mismatch')
                require(len({c['id'] for c in cases}) == len(cases), 'Duplicate case ID')
                require(all(c['passed'] == (c['expected'] == c['actual']) for c in cases), 'Result status mismatch')
                require(sum(not c['passed'] for c in cases) == report['failed'], 'Failure count mismatch')
                require(report['passed'] + report['failed'] == report['total'], 'Summary count mismatch')
                require(report['failed'] > 0 if report['intentionalFault'] else report['failed'] == 0,
                        'Unexpected candidate outcome')
            require(any(e['status'] == 'available' and e['output'].strip() for e in variant['evidence'].values()),
                    'No native evidence available')
    validate_evaluation(data)
    return data

def validate_assets(data, directory):
    evaluation = data.get('evaluation')
    if evaluation:
        path = (directory / evaluation['freezePath']).resolve()
        path.relative_to(directory.resolve())
        require(hashlib.sha256(path.read_bytes()).hexdigest() == evaluation['freezeSha256'],
                'Freeze receipt hash mismatch')
        validate_evaluation(data, json.loads(path.read_text()))
    for fixture in data['fixtures']:
        for variant in fixture['variants']:
            ghidra=variant['evidence'].get('ghidra')
            if not ghidra or ghidra['status']!='available':
                continue
            for path_key,hash_key in [('rawEvidencePath','rawEvidenceSha256'),('inventoryPath','inventorySha256')]:
                path=(directory/ghidra[path_key]).resolve()
                path.relative_to(directory.resolve())
                require(hashlib.sha256(path.read_bytes()).hexdigest()==ghidra[hash_key], 'Provider asset hash mismatch')
    return data

def main():
    try:
        data=validate(json.loads((ROOT / 'web/data/report.json').read_text()))
        validate_assets(data,ROOT/'web')
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise SystemExit(f'Cannot export evidence: {error}')
    shutil.copytree(ROOT / 'web', ROOT / 'dist', dirs_exist_ok=True)
    print('Validated and exported dist/ (no runtime dependencies).')

if __name__ == '__main__':
    main()
