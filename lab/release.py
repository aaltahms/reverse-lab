"""Package only ReverseLab source, documentation and redistributable recordings."""
import hashlib
import json
from pathlib import Path
import zipfile
from lab.webbuild import ROOT, validate, validate_assets

VERSION = '0.5.0'
DIRECTORIES = ['fixtures','reconstructions','lab','tests','web','docs','.github']
FILES = ['README.md','LICENSE','.gitignore']

def main():
    data=validate(json.loads((ROOT / 'web/data/report.json').read_text()))
    validate_assets(data,ROOT/'web')
    files = [ROOT / name for name in FILES]
    for name in DIRECTORIES:
        files.extend(path for path in (ROOT / name).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix != '.pyc' and path.name != '.DS_Store')
    files = sorted(set(files))
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    output = ROOT / 'dist' / f'reverse-lab-{VERSION}.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'reverse-lab/' + str(path.relative_to(ROOT)))
        archive.writestr('reverse-lab/RELEASE-MANIFEST.json', json.dumps({'version':VERSION,'sha256':manifest},indent=2)+'\n')
    print(f'{output}\n{len(files)} scoped files; source, demo evidence and screenshots; no native binaries/caches.')

if __name__ == '__main__':
    main()
