# Public release verification — October 14, 2026

- Source: https://github.com/aaltahms/reverse-lab
- Browser demo: https://aaltahms.github.io/reverse-lab/
- Portfolio entry: https://aaltahms.github.io/#reverse-lab

## Source and CI

The initial public source was downloaded through Git and all 48 scoped source/documentation/recording files matched the reviewed release manifest byte-for-byte. This publication record is a subsequent documentation addition. Native binaries, optional toolchains, Python caches, resume files and unrelated workspace projects are not included in the ReverseLab repository.

[GitHub Actions run 38621612572](https://github.com/aaltahms/reverse-lab/actions/runs/38621612572) succeeded in 52 seconds on code commit `652058e`. Both Ubuntu 24.04 matrix jobs, Python 3.9 and 3.13, completed successfully. The workflow runs the 34-test suite, full baseline generation, source-known freeze/evaluation, AddressSanitizer + UndefinedBehaviorSanitizer corpus execution, JavaScript syntax validation and static export. Later documentation and screenshot commits do not change the code checked by that run.

Hosted success does not establish working ASan on the local macOS toolchain. The retained Ghidra evidence was generated locally on macOS arm64; the hosted job exercises provider-record import boundaries rather than installing or running Ghidra. The shipped seven-build recording and its 7,000 held-out agreements are the macOS demonstration; the CI's full baseline generation uses six optimization builds.

## Portfolio and demo

The existing portfolio gained a ReverseLab card, actual screenshot, source link and direct demo link. Existing project content and resume downloads were preserved. Its prior public HTML/CSS were compared against the local edits before upload.

[Pages build/deployment 38621900157](https://github.com/aaltahms/aaltahms.github.io/actions/runs/38621900157) succeeded in 55 seconds. The live HTML, CSS, screenshot, portfolio README and eight explorer/evidence assets all returned HTTP 200 and matched the reviewed local files byte-for-byte: 12 assets in total. Only these new or edited website assets were uploaded; existing resume PDFs were not reuploaded.

The live portfolio's demo link opened the six-byte `boundary-006` packet mismatch: reference `0x83123400`, deliberate mutant `0x83341200`. Corpus switching showed the separately recorded held-out result, 667 passing / 333 failing mutant inputs. The browser serves recorded evidence; it has no native execution service. Local native replay retains its original hash guards and build prerequisites.

The project remains an educational comparison lab with three owned fixtures and source-known authorship. An actual firmware adapter/case study and automatic failure reduction are the next practical improvements.
