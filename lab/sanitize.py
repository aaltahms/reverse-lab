"""Execute the owned corpus under UBSan, optionally adding AddressSanitizer."""
import argparse
import os
import shutil
import subprocess
from lab.pipeline import ROOT, SEED, cases_for, oracle, run

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', action='store_true', help='Also use ASan; requires a functioning platform runtime')
    args = parser.parse_args()
    compiler = shutil.which(os.environ.get('CC', 'clang'))
    if not compiler:
        parser.exit(2, 'Clang is required\n')
    sanitizers = 'address,undefined' if args.address else 'undefined'
    try:
        for name in ['checksum','packet','fsm']:
            executable = ROOT / f'build/{name}-sanitized'
            executable.parent.mkdir(exist_ok=True)
            command = [compiler,'-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
                       f'-fsanitize={sanitizers}','-fno-sanitize-recover=all',
                       f'fixtures/{name}.c','fixtures/harness.c','-o',str(executable)]
            compiled = run(command)
            if compiled.returncode:
                parser.exit(2, compiled.stderr)
            cases = cases_for(name, SEED)
            oracle(executable,cases)
            print(f'{name}: {len(cases)} inputs without {sanitizers} diagnostics', flush=True)
    except subprocess.TimeoutExpired:
        parser.exit(2, f'Sanitizer runtime timed out; no success established ({sanitizers}). If using --address, rerun with UBSan only.\n')
    except (OSError, RuntimeError) as error:
        parser.exit(2, f'Sanitizer execution failed: {error}\n')

if __name__ == '__main__':
    main()
