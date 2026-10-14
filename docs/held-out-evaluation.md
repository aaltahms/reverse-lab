# Frozen candidate evaluation

ReverseLab 0.3 adds an evaluation phase to the existing source-known experiments. It records the candidate before selecting a new seed, then tests previously unused byte sequences. This addresses one practical weakness of the original demo: all its behavioral results came from the development corpus.

## Procedure

Run from the project root after native generation and any optional stripped/provider steps:

```sh
python3 -m lab.holdout freeze
python3 -m lab.holdout evaluate
python3 -m lab.webbuild
```

`freeze` records candidate text, candidate/source/harness/artifact hashes, the complete development input streams, generator identity and UTC time in `web/data/evaluation-freeze.json`. It selects no evaluation seed. A new freeze removes the earlier evaluation from the report.

`evaluate` checks the freeze against the current recording and files, then chooses a 32-bit seed using system randomness. `--seed N` selects an explicit reproducible seed; that choice is disclosed as operator-specified. The seed must differ from the development seed. `--count N` defaults to 1,000 unique inputs per fixture and accepts 1–10,000.

Inputs use the existing seeded generator with the new seed. Directed development cases are omitted. Every byte sequence already in the development corpus, and every duplicate within the new corpus, is excluded. Each fixture's retained input stream is shared across optimization variants and candidates. The evaluation runs the actual compiled executables and the checked frozen Python text; it does not rely on cached Python imports. File hashes are checked again after execution. The report is replaced only after a complete evaluation.

The exporter checks input uniqueness, zero overlap, case-stream digests, identical reference outputs across variants, consistent result counts, the freeze receipt's byte hash and its bindings to the recording. The explorer adds **Development corpus / Held-out evaluation** controls inside Verification. Both corpora have case inspection, filters, pagination, shareable URLs and separate replay commands. Freeze metadata is downloadable.

## Replay

```sh
python3 -m lab.holdout replay --fixture packet --variant O2-stripped \
  --candidate faulty_endian --case heldout-0001
```

Choose a case ID from the included report; this example is not guaranteed to be a failure. Replay verifies frozen files and the receipt, regenerates the exact evaluation corpus, checks it against the recording, and runs the selected candidate and native executable. Exit 1 means a mismatch, 0 means agreement, and 2 means rejected input or stale identity. Repeated evaluation is rejected until a new freeze is made; replay remains available.

Running the regression suite recompiles development artifacts. Run generation, optional stripping/decompilation, freeze and evaluation again afterward. A clean checkout can browse the shipped report without native binaries; rebuilding creates a new local evaluation with a new artifact identity. It cannot replay the original host's binary from source alone.

## What this establishes

The included October 14 run selected seed **3425116644** after freezing. It retained 1,000 unique new inputs per fixture: **3,000 fixture/input pairs**, reused across seven native builds. Correct candidates achieved **7,000 / 7,000 agreements**. The deliberate endian mutant disagreed on **333 inputs per packet build** (999 repeated detections across three variants). Duplicate or development-overlapping candidates excluded before reaching the quota: checksum 14, packet 7, state machine 52. These counts exclude the omitted directed cases.

The unchanged candidates can be challenged on disjoint sampled inputs, and the controlled endian fault remains detectable. Input uniqueness is byte-for-byte, within each fixture. Different inputs can still exercise the same behavior, especially malformed packets or bytes beyond the checksum's 32-byte bound. This is not a new independent generator, coverage measurement, exhaustive analysis or an equivalence proof.

Reference source was known during authorship. The freeze is a local procedural record: an operator with file access can replace it. Timestamps and hashes detect inconsistent files but do not authenticate historical order or a third-party producer. No analyst was isolated from source, and the evaluation becomes visible after execution. A genuine source-blind challenge remains a separate milestone.
