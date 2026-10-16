"""Execute the user's Python function outside the server process."""
import contextlib
import importlib.util
import json
import sys

# Keep ordinary diagnostic prints out of the machine-readable response.
with contextlib.redirect_stdout(sys.stderr):
    spec = importlib.util.spec_from_file_location('user_candidate', sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, sys.argv[2])
    if not callable(function):
        raise TypeError('Selected Python name is not callable')
for line in sys.stdin:
    value = bytes.fromhex(line.strip()) if line.strip() != '-' else b''
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = function(value)
        if type(result) is not int or not 0 <= result <= 0xffffffff:
            raise ValueError('Return an integer from 0 to 4294967295 (not bool)')
        row = {'value': result}
    except Exception as error:
        row = {'error': (type(error).__name__ + ': ' + str(error))[:1000]}
    print(json.dumps(row), flush=True)
