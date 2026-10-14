# Local verification record

Current 0.3.0 milestone, October 14, 2026: **34 tests pass**, including eight new freeze/evaluation checks using actual native compilation and execution. The development corpus still produces **4,438 valid-candidate agreements**, with **219 deliberate endian mismatches per packet build**. Real REA 6.4.0/Ghidra 12.1.4 analysis was rerun on the rebuilt stripped packet and again produced 555 lines of pseudocode; target SHA-256 `80190840ca56b948d703cf404685bfaa4d138c1482390bc38d5f326dccc5cf12` matches the executable and evaluation freeze.

## 0.3.0 held-out evaluation

The candidate freeze was recorded at `2026-10-14T06:39:45.132181+00:00`; seed **3425116644** was selected using system randomness at `06:39:45.264968+00:00`. Evaluation completed at `06:39:45.411477+00:00`. These are locally recorded times, not an authenticated independent history.

Each fixture contributes 1,000 unique evaluation inputs with zero byte-for-byte development overlap. All seven valid candidate/build pairs pass: **7,000 / 7,000 comparisons** over **3,000 new fixture/input pairs**. The packet mutant fails **333 / 1,000** inputs in each of three builds. Directed cases are excluded; the same seeded generator is reused with the new seed.

The regression checks reject changed binary bytes, changed frozen candidate text, changed generator identity, the development seed, repeated evaluation without a new freeze, corrupted summaries, overlap, changed receipt bytes, recording identity changes and absent case IDs. They also check deterministic/bounded inputs and real failing/correct native replay. `lab.webbuild` validates the evaluation and freeze asset before export. See [procedure and limits](held-out-evaluation.md).

A focused replay of `packet / O2-stripped / faulty_endian / heldout-0001` exited **1** as expected: reference `0x82521006`, candidate `0x82105206`. The reference source was known during authorship; this is not a source-blind challenge. The [0.2.0 investigation record](ghidra-investigation.md) retains the earlier milestone as history.

Browser checks exercised the real loopback app in Chrome: unavailable evaluation controls before recording, corpus switching, 1,000 passing results, 333 mutant failures, exact selected-case replay copying, pagination, empty filters/search, reload persistence and expanded freeze metadata. At **390 × 844**, document width stayed 390 pixels with the freeze details expanded. The viewport override was reset. Browser error/warning logs were empty. Screenshots: [evaluation](screenshots/evaluation.jpg), [mobile freeze record](screenshots/evaluation-mobile.jpg).

The 0.3.0 source archive contains 47 scoped files and a SHA-256 manifest, excluding native binaries and toolchains. A fresh extraction validated the shipped freeze/Ghidra assets, passed all **34 tests**, regenerated native and stripped artifacts, created a new local freeze, reproduced **7,000 agreements / 999 repeated deliberate failures** with seed 3425116644, exported the explorer and replayed the selected mismatch with exit 1. The provider-only import test fixture was updated to discard an inapplicable evaluation binding when replacing the full experiment. The original host's final artifact, candidate, generator, freeze and raw provider hashes were checked again after packaging.

## Historical 0.1.0 baseline

Verified October 13, 2026 on macOS arm64 with Apple Clang 17.0.0, Python 3.9.6, Apple LLVM objdump 17.0.0, and Node 24.19.0 for JavaScript syntax. The sections below record the original 0.1.0 local baseline, before the 0.2.0 provider milestone. That baseline did not exercise REA/Ghidra. Public deployment and hosted CI remain unverified.

## Pipeline

`python3 -m unittest discover -s tests -v` passed **14 tests**. They compile and execute actual native targets, compare optimization variants, check independent golden checksum/packet/state-machine outcomes, exercise malformed/overlong/embedded-NUL protocol recovery, detect the endian mutant, verify deterministic bounded case streams, preserve unavailable/unsupported evidence, reject inconsistent summaries, reject stale artifact/case-stream identity, validate fixture allowlisting, and detect truncated oracle output.

`python3 -m lab.pipeline generate` produced the complete recording:

| Fixture | Variant | Candidate | Passed | Failed |
| --- | --- | --- | ---: | ---: |
| checksum | O0 | reconstruct | 626 | 0 |
| checksum | O2 | reconstruct | 626 | 0 |
| packet | O0 | reconstruct | 638 | 0 |
| packet | O0 | faulty_endian | 419 | 219 |
| packet | O2 | reconstruct | 638 | 0 |
| packet | O2 | faulty_endian | 419 | 219 |
| fsm | O0 | reconstruct | 636 | 0 |
| fsm | O2 | reconstruct | 636 | 0 |

Seed **1380720678**; 600 seeded cases per fixture. There are 1,900 fixture/case IDs and 3,800 valid-candidate comparisons across the two variants. Some cases repeat the same bytes; these are not 1,900 unique byte sequences. The mutant adds 1,276 comparisons and 438 mismatches. Counts describe the recorded corpus, not total behavioral coverage.

`python3 -m lab.sanitize` executed all 626 + 638 + 636 inputs under UndefinedBehaviorSanitizer with no diagnostics. The combined AddressSanitizer/UBSan runtime timed out on the checksum target after 60 seconds both inside and outside the sandbox; a single-input ASan check with leak detection disabled also timed out. No ASan success or root-cause diagnosis is claimed. ASan is optional through `--address`; Linux CI is configured to exercise it but is unrun.

`node --check web/app.js` (bundled Node executable) passed. `python3 -m lab.webbuild` validated the three-fixture report contract and exported `dist/`. It checks summary/case consistency and expected candidate outcomes; it is a static copy/export, not a JavaScript bundler.

A real focused replay of packet O2 / faulty_endian / boundary-006 exited **1**, as expected. Input `a503123400ee`; expected `2199008256` (`0x83123400`), actual `2201227776` (`0x83341200`). Executable identity is retained in the replay output and the included recording. Binary hashes are recording-specific and can change when rebuilt.

## Browser

Exercised the actual running app in Chrome with the supported browser-control tool:

- All three fixture selectors, both optimization controls, and native evidence/build provenance views.
- Disassembly search (`ldrb`), symbol inventory, and source-location output.
- Correct/faulty candidate switching, failure/boundary filters, case search and empty results.
- A real selected counterexample, its sequence-byte interpretation, exact identity disclosure and visible rerun command; the copy control reported success.
- Pagination beyond the first 50 cases and a deep-linked case after reload.
- Keyboard tab navigation (Right arrow), `/` search focus, and browser history.
- Explicit reference reveal/hide and reset on fixture selection.
- Missing-recording HTTP 404 recovery: temporarily withheld the owned report, observed the error view, restored it, and used Retry loading successfully.
- A **390 × 844** viewport, with document width equal to viewport width (no page-level horizontal overflow), and a selected state-machine fault/reset case.
- Final Chrome developer error/warning log query returned an empty list.

Screenshots: [overview](screenshots/overview.jpg), [counterexample](screenshots/counterexample.jpg), [narrow verification](screenshots/mobile.jpg). No formal accessibility audit or usability research was performed.

The Codex browser panel was queued with the live counterexample URL; direct in-app browser attachment was unavailable during automation, so browser verification used Chrome. The loopback preview is left running for review.

## Packaging

The source archive excludes `build/`, `dist/`, Python caches and unrelated workspace files. It includes a SHA-256 manifest and the redistributable report/screenshots. A clean extraction passed full native evidence generation, static export, and the expected failing case replay; every packaged file matched its manifest hash. The prepared GitHub workflow is scoped to this project as a standalone repository, with Ubuntu/Python 3.9 and 3.13. Its hosted execution and Linux behavior remain unverified.
