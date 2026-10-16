# Compare your own programs — 0.5.0

The primary task is checking a C byte-processing function against a Python rewrite, using your own source files and inputs. This is useful when replacing a small parser, checksum, or deterministic state machine. The result is a concrete input with two differing integer outputs, or agreement on the supplied test set.

## Browser workflow

1. Install the project prerequisites: Python 3.9+ and Clang on macOS or Linux. From the project root, run `python3 -m lab.serve --execute`.
2. Open the printed loopback URL, ending in `/compare.html`. The banner must say **Local runner connected**. Execution is disabled by default in ordinary `lab.serve` mode.
3. Select a C file exporting `uint32_t evaluate(const uint8_t *, size_t)` and a Python file exporting `evaluate(data: bytes) -> int`. C has no `main()`; its function must not print to stdout. Change the Python entry name if needed. Both return 0..4294967295, with input length 0..64. Python booleans, floats, negative and oversized integers are errors.
4. Provide one hex byte sequence per line. Spaces are allowed; blank lines are ignored; `-` tests an empty input. Up to 256 inputs total. Optional random inputs are generated reproducibly from the chosen seed and included verbatim in the report.
5. Confirm you trust the programs, then run. C is compiled with C11 and `-O2`, linked with the byte-input harness, and executed separately from the Python interpreter.
6. The first difference is selected automatically. Choose any input row; filter to differences; inspect decimal and hex values. Python exceptions are attached to their input, with later inputs still tested. A C crash or process-level failure aborts the run rather than fabricating per-case values.
7. Download the JSON report and exact input text. The report records source and artifact SHA-256, function names, compiler/version/flags, environment, generation settings, input digest, diagnostics and every output. It excludes source text. A replay uses the original files and the downloaded exact inputs, with random count 0.
8. **Open a report** works on both local and hosted pages. It validates shape, input/output bounds and summary consistency before rendering. Imported data is explicitly labeled as imported, not rerun or authenticated. Hashes identify content; a producer can still forge a report.

The starter is a one-byte checksum: the C sum wraps at 255; the deliberately faulty Python sum does not. `ff ff` exposes 254 versus 510. Load the corrected Python and rerun for agreement. This starter is separate from the historical packet/Ghidra recording.

## Terminal workflow

```sh
python3 -m lab.compare --reference my_reference.c --candidate my_rewrite.py \
  --function evaluate --inputs inputs.txt --random-count 100 --seed 42 \
  --output comparison.json
```

Exit 0: all selected inputs agree. Exit 1: at least one difference or Python case error, with report saved. Exit 2: invalid input, compiler/setup problem, native failure, import failure or timeout; no success report is emitted. Open the output through **Open a report**. The console prints a short count summary. Reports can contain private input data or diagnostic text; inspect them before sharing.

## Failure handling and boundaries

- Compilation errors and diagnostics are shown without clearing the selected programs or inputs. Fix and select the file again, then rerun. Missing Clang is a setup error with installation guidance; `CC` may select an installed compiler executable, without shell expansion.
- C compilation has a 15-second wall timeout. Compiler identification, C execution and Python execution each have a 5-second wall timeout. Timeouts kill the process group; successful exits also clean up remaining children in that group. Output files are capped at 1 MiB per process; CPU, descriptor and core-dump limits are set. Linux also limits virtual address space to 512 MiB. These bounds can reject expensive valid programs.
- The runner accepts one comparison at a time. Its API requires the exact loopback Host/Origin, JSON content, a per-session token, request size at most 1 MiB and explicit trusted-code intent. It does not enable CORS or listen on an external interface. The API is disabled unless `--execute` was passed.
- Programs run with the user's account permissions and can access files or the network. Limits are best-effort safeguards, **not a security sandbox**. Do not run untrusted downloads. The project does not accept remote execution requests on GitHub Pages.
- Inputs and temporary source files are held only for the run; temporary files are removed afterward. No run history or source-code storage is added. The browser retains selected content only until refresh/navigation.
- Each program processes the corpus sequentially in one fresh process per run. Stateful or nondeterministic functions can depend on earlier cases or environmental state; this version does not establish purity or determinism. A successful sample comparison is not an equivalence proof.
- Standard libraries are supported. Local module dependencies, custom headers, package installation, custom compiler flags, Windows, arbitrary binary signatures, strings/structures as outputs, firmware peripherals and ABI adaptation need additional adapters.
- Random bytes may spend all their time in a parser's rejection paths. Provide directed valid packets and meaningful edge cases; volume alone does not establish coverage.

## Verification

Integration checks compile and execute real C, exercise correct and faulty candidates, Python exceptions and invalid returns, print redirection, custom entry points, compiler errors, a native abort, a runaway process and output bounds. Loopback HTTP tests cover a real API comparison and rejection of wrong host/origin/token, missing trusted intent, disabled execution, oversized requests and concurrent runs. JavaScript tests reject inconsistent reports and invalid input text. Browser QA covers the complete starter correction flow, actual file selection, recoverable errors, export/import, filtering and narrow layouts.
