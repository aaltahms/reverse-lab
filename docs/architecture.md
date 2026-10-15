# Architecture and evidence boundaries

ReverseLab is a compiler/verification pipeline plus a read-only evidence viewer. C, Python, HTML, CSS, and browser JavaScript fit the actual workload without third-party runtime packages. The included recording is the first meaningful view; a compiler is needed only to regenerate it.

```text
fixtures/*.c + harness.c ── Clang -O0/-O2 ──► build/native executable
                                                 │
                   ┌─────────────────────────────┴────────────────────┐
                   ▼                                                  ▼
            objdump / nm / file                         batch hex stdin → uint32 stdout
                   │                                                  │
                   ▼                                                  ▼
          observations + provenance                   compare with Python candidate
                   │                                                  │
                   └──────────────────► report.json ◄─────────────────┘
                                             │
                                      static evidence explorer
```

`lab/pipeline.py` owns a fixed fixture/candidate/variant allowlist. Compilation and tool invocations use direct argument arrays with a project-root working directory, captured output, and 60-second timeouts. The compiler can be selected through an operator-provided `CC`. The UI cannot execute commands.

Each executable links one `evaluate(const uint8_t *, size_t)` function with a shared line-protocol harness. Hex input or `-` (empty input) produces exactly one uint32 decimal output. Invalid/overlong records produce `ERR` and the next record remains usable. This keeps the oracle as an actual compiled program rather than a Python translation of the reference. Input sequences are bounded to 64 bytes by the harness. Fixtures use unsigned arithmetic and explicit shifts; packet validation prevents reads outside the declared payload.

The Python candidates express behavior through different formulations, with source-known authorship explicitly disclosed. The packet mutant reuses the correct candidate's validation and deliberately swaps the sequence bytes; it is a fault-injection experiment, not a second independently recovered model. Actual Ghidra output is retained separately from the authored candidates.

## Evidence contract

`web/data/report.json` has `schemaVersion: 1` and is atomically replaced after a complete successful generation. A top-level recording stores time, native platform, exact compiler version/path, Python version, case-generation description, seed, and optional-provider status. Fixtures contain contracts, authored interpretation/uncertainty notes, reference/candidate source text and hashes. Variants contain build arguments, artifact size/hash, harness hash, disassembler version, tool outputs/status/exit codes, and candidate reports.

A report retains **every** directed and seeded case, not only the failures. Each case has a stable ordinal ID, class, label, hex input, expected output, actual output and equality status. The case-stream digest hashes canonical JSON of the generated inputs. IDs are scoped to a fixture/seed/count; `seeded-0001` is not a universal input identity.

`verify` checks the actual executable and all relevant source hashes against the recording before executing. For the same seed/count it checks the case-stream digest, guarding against generator drift. An explicitly changed seed/count creates a new sample against the recorded executable, not a replay of the old sample. All comparisons use exact uint32 equality; there are no floating-point tolerances or timing assertions.

Tool output is scoped to one artifact. The disassembler selects `evaluate` (or Mach-O `_evaluate`) and retains the function listing. LLVM objdump is preferred; GNU uses its own symbol-selection option. Missing tools and unsupported operations retain explicit status, stderr and exit information. Debug location paths are normalized at the project root, so normalized outputs are not byte-identical tool logs. Symbol/debug builds are intentionally easier educational targets.

## Viewer

`lab/serve.py` serves only `web/` on `127.0.0.1`. There is no database, execution endpoint, account, cloud service or LLM call. `lab/webbuild.py` checks report counts/outcomes and copies the static application into `dist/`. It does not minify or bundle code; the browser runs one ES module and one stylesheet. Node is only an optional syntax check in development/CI.

The viewer loads one JSON recording. Its default screen presents a packet, readable original/replacement outputs, an explanation and a corrected-version comparison. A separate technical view selects fixture/build/candidate and exposes code, tool outputs, all tests and source reveal through one tab bar. Existing view URLs retain the technical view; `screen=workbench` selects the simple comparison. `packet-view.mjs` interprets recorded uint32 values for display; it does not execute either decoder. The source-reveal preference hides a view, not the underlying JSON. All report strings are escaped when rendered; native output remains readable, selectable text.

The verification view uses filtering, search and 50-case pages to bound DOM size while keeping the complete corpus inspectable. URLs retain fixture, build, view, candidate, filter and explicitly selected case. Source reveal resets on fixture changes. Semantic controls, visible focus, arrow-key tabs, `/` search, error recovery and a responsive stacked inspector support exploration. No accessibility certification or usability study is claimed.

The optional `lab.holdout` phase writes a candidate freeze receipt before selecting a new seed. It binds candidate text, sources, harnesses, executables, generator code and development input streams. Evaluation excludes overlapping/duplicate byte sequences and attaches separate `evaluationReports` to variants. The exporter checks these reports and the receipt hash; replay regenerates inputs and verifies local file identities. Verification URLs also retain the corpus. The procedure is source-known and locally editable, with no authenticated history or isolated analyst claim. See [evaluation details](held-out-evaluation.md).

## Reproducibility limits

Deterministic inputs and recorded commands make behavioral results rerunnable on an equipped native host. Compiler/SDK changes, debug paths, architecture and linker metadata can change binary hashes. No bit-for-bit cross-host reproducible build claim is made. Tests regenerate native binaries; keep the demo aligned by generating the full report after tests. Binaries, caches and production exports are ignored; the small source/evidence corpus and screenshots are intentional release assets.

The application includes one real native Ghidra decompilation recording. It does not establish blind source recovery, external protocol identification, universal equivalence, runtime trace coverage, performance, or cross-architecture correctness. Those need separate experiments and evidence.

## Stripped artifact and external provider boundary (0.2.0)

`lab/stripped.py` derives a packet `O2-stripped` artifact with the native strip tool and, on macOS, local ad-hoc signing. It verifies removal of the evaluate symbol, reruns the complete corpus on both twins, and preserves transformation commands and twin identity. Its disassembly range is selected from the symbol-bearing twin, an explicitly source-known aid. Binary size need not shrink after stripping/signing on Mach-O.

`lab/decompile.py` runs the public REA CLI with a Ghidra provider, first retrieving actual procedure inventory and then decompiling the matching observed address. Every invocation receives direct arguments; CLI sessions own and close ephemeral Ghidra projects. The adapter preserves complete JSON carrier bytes and rejects wrong target hashes, wrong operations/providers, different analysis profiles, unobserved/ambiguous addresses, wrong selectors and null pseudocode. It checks a present local artifact before import and before/after actual execution. A portable import can attach records to a demo without a local executable; that checks record consistency, not producer authenticity or execution on the current host.

The included exercised profile is REA 6.4.0 / Ghidra 12.1.4 / macOS arm64 / Mach-O. Other layouts/providers are not claimed compatible merely because they produce JSON. Imported records carry `origin: imported-record`; the actual CLI path records `origin: local-run`. Regenerating baseline evidence clears the derived variant/provider attachment so changed binaries cannot silently inherit stale findings. External tools are optional and excluded from the release archive.

The viewer distinguishes native assembly, actual Ghidra pseudocode, authored Python and reference C. Pseudocode landmarks are located in the real output; they are navigational annotations, not independent semantic findings. Ghidra's inferred types/names and optimized vector loops remain unedited. The behavioral report compares the Python model with the compiled executable, not with a compiled version of the pseudocode.
