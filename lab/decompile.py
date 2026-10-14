"""Run or import a genuine REA/Ghidra record for the owned stripped packet target."""
import argparse
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import shutil
import shlex
import subprocess
from lab.pipeline import ROOT, digest

MAX_RECORD = 8 * 1024 * 1024


def read_record(path):
    if path.stat().st_size > MAX_RECORD:
        raise ValueError('REA record exceeds the 8 MiB import budget')
    return json.loads(path.read_bytes())


def evidence_record(carrier, operation, target_hash):
    if not isinstance(carrier,dict):
        raise ValueError('REA carrier must be a JSON object')
    record = carrier.get('data',carrier)
    if not isinstance(record,dict) or record.get('error'):
        raise ValueError('REA returned an error record, not successful Evidence')
    if not all(isinstance(record.get(key),dict) for key in ['provider','subject','analysis_profile']):
        raise ValueError('Missing structured Evidence identity')
    if record.get('operation') != operation or record['provider'].get('id') != 'ghidra':
        raise ValueError('Unexpected Evidence operation/provider')
    if (record['subject'].get('digest') or {}).get('sha256') != target_hash:
        raise ValueError('Evidence target hash does not match this artifact')
    if not record.get('evidence_id') or not record.get('analysis_profile',{}).get('digest'):
        raise ValueError('Missing Evidence/profile identity')
    return record


def select_procedure(carrier, variant):
    record = evidence_record(carrier,'search_procedures',variant['sha256'])
    address = variant['derivedFrom']['procedureAddress']
    rows = record.get('normalized_result')
    if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):
        raise ValueError('Unsupported REA procedure inventory shape')
    matches = [row for row in rows if row.get('address') == address]
    if len(matches) != 1:
        raise ValueError('Symbol-twin address is not a unique Ghidra-observed procedure')
    if not isinstance(matches[0].get('value'),str):
        raise ValueError('Observed procedure is missing its name')
    return record,matches[0]


def install_record(decompile_path, procedures_path, rea_version='unknown (imported)',
                   java_version='unknown (imported)', command='Imported REA Evidence',
                   report_path=None, output_root=None, origin='imported-record'):
    report_path = report_path or ROOT/'web/data/report.json'
    output_root = output_root or ROOT/'web'
    recording = json.loads(report_path.read_bytes())
    fixture = next(f for f in recording['fixtures'] if f['id']=='packet')
    variant = next(v for v in fixture['variants'] if v['id']=='O2-stripped')
    artifact = ROOT/variant['artifact']
    if artifact.exists() and digest(artifact.read_bytes()) != variant['sha256']:
        raise ValueError('Local artifact changed; regenerate and reanalyze')
    inventory,procedure = select_procedure(read_record(procedures_path),variant)
    decompiled = evidence_record(read_record(decompile_path),'procedure_pseudo_code',variant['sha256'])
    if decompiled['analysis_profile']['digest'] != inventory['analysis_profile']['digest']:
        raise ValueError('Procedure inventory and pseudocode have different analysis profiles')
    if decompiled.get('parameters',{}).get('procedure') not in [procedure['address'],procedure['value']]:
        raise ValueError('Pseudocode selector differs from the selected observed procedure')
    output = decompiled.get('normalized_result')
    if not isinstance(output,str) or not output.strip():
        raise ValueError('Ghidra returned no pseudocode; null is not recovered code')
    # Retain original carrier bytes, not a regenerated or abbreviated rendering.
    destination = output_root/'data/providers'
    destination.mkdir(parents=True,exist_ok=True)
    for name,path in [('packet-O2-stripped.decompile.json',decompile_path),('packet-O2-stripped.procedures.json',procedures_path)]:
        (destination/name).write_bytes(path.read_bytes())
    raw_path = 'data/providers/packet-O2-stripped.decompile.json'
    variant['evidence']['ghidra'] = {
        'status':'available','origin':origin,'command':command,'exitCode':0,'output':output,'error':'',
        'provider':'Ghidra','reaVersion':rea_version,'ghidraVersion':decompiled['provider']['version'],
        'javaVersion':java_version,'evidenceId':decompiled['evidence_id'],
        'profileDigest':decompiled['analysis_profile']['digest'],'targetSha256':variant['sha256'],
        'procedure':procedure['value'],'address':procedure['address'],
        'selection':variant['derivedFrom']['selection'],
        'rawEvidencePath':raw_path,'rawEvidenceSha256':digest(decompile_path.read_bytes()),
        'inventoryPath':'data/providers/packet-O2-stripped.procedures.json',
        'inventorySha256':digest(procedures_path.read_bytes()),
        'limitations':decompiled.get('limitations',[]),
        'highlights': [{'label':label,'line':index+1} for label,pattern in
                       [('Input validation',r'^\s*return 1;'),('Checksum rejection',r'^\s*return 5;'),('Packed result',r'^\s*return .*param_1\[1\]')]
                       for index,line in enumerate(output.split('\n')) if re.search(pattern,line)][:3],
        'recordedAt':datetime.now(timezone.utc).isoformat(),
    }
    recording['providers'] = [
        {'name':'REA','status':'exercised' if origin=='local-run' else 'recorded','detail':f'CLI {rea_version}; Ghidra procedure inventory and decompilation on packet/O2-stripped. MCP registration was not changed.'},
        {'name':'Ghidra','status':'exercised' if origin=='local-run' else 'recorded','detail':f"Version {decompiled['provider']['version']}; arm64 stripped packet function {procedure['value']}. Other artifacts have no decompiler recording."},
    ]
    temporary=report_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(recording,indent=2)+'\n');temporary.replace(report_path)
    return variant['evidence']['ghidra']


def toolchain():
    local = ROOT/'build/toolchains/config.json'
    config = json.loads(local.read_text()) if local.exists() else {}
    executable = config.get('rea') or shutil.which('rea')
    if not executable:
        raise ValueError('REA CLI missing. Put rea on PATH or configure build/toolchains/config.json; see docs/ghidra-investigation.md')
    environment = dict(os.environ)
    for key,name in [('JAVA_HOME','javaHome'),('GHIDRA_INSTALL_DIR','ghidraHome')]:
        if config.get(name) and not environment.get(key):
            environment[key] = config[name]
    if config.get('node'):
        environment['PATH'] = str(Path(config['node']).parent)+os.pathsep+environment.get('PATH','')
    return executable,environment


def capture(command, environment, destination=None):
    result = subprocess.run(command,cwd=ROOT,env=environment,text=True,capture_output=True,timeout=300)
    if destination:
        destination.write_text(result.stdout)
        destination.with_suffix('.stderr').write_text(result.stderr)
    if result.returncode:
        try:
            record=json.loads(result.stdout).get('data',{})
            message=record.get('message') or record.get('error') or result.stderr
        except ValueError:
            message=result.stderr or result.stdout[:500]
        raise RuntimeError(f'REA/provider command exited {result.returncode}: {message}')
    return result.stdout


def run_analysis():
    recording = json.loads((ROOT/'web/data/report.json').read_bytes())
    variant=next(v for f in recording['fixtures'] if f['id']=='packet' for v in f['variants'] if v['id']=='O2-stripped')
    artifact=ROOT/variant['artifact']
    if digest(artifact.read_bytes())!=variant['sha256']:
        raise ValueError('Artifact changed; regenerate and derive stripped variant first')
    executable,environment=toolchain()
    rea_version=capture([executable,'--version'],environment).strip()
    java_home=environment.get('JAVA_HOME')
    java=str(Path(java_home)/'bin/java') if java_home else shutil.which('java')
    java_version=capture([java,'--version'],environment).strip() if java else 'Unavailable'
    working=ROOT/'build/analysis';working.mkdir(parents=True,exist_ok=True)
    search=working/'procedures.json'
    common=['--provider','ghidra','--format','json','--full-output']
    capture([executable,'search',str(artifact),'.','--kind','procedures','--mode','regex',*common],environment,search)
    _,procedure=select_procedure(read_record(search),variant)
    decompile=working/'decompile.json'
    command=[executable,'decompile',str(artifact),procedure['address'],*common]
    capture(command,environment,decompile)
    if digest(artifact.read_bytes())!=variant['sha256']:
        raise ValueError('Artifact changed during analysis; rejecting Evidence')
    return install_record(decompile,search,rea_version,java_version,shlex.join(command),origin='local-run')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',choices=['run','import'],default='run')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--procedures',type=Path)
    parser.add_argument('--rea-version',default='unknown (imported)')
    args=parser.parse_args()
    try:
        if args.action=='import':
            if not args.input or not args.procedures:
                parser.error('import requires --input and --procedures')
            item=install_record(args.input,args.procedures,args.rea_version)
        else:
            item=run_analysis()
    except (ValueError,RuntimeError,OSError,StopIteration,KeyError,subprocess.TimeoutExpired) as error:
        parser.exit(2,f'Cannot attach Ghidra Evidence: {error}\n')
    print(f"Ghidra {item['ghidraVersion']} / REA {item['reaVersion']}: {item['procedure']}, {len(item['output'].splitlines())} lines, target {item['targetSha256']}")

if __name__=='__main__':
    main()
