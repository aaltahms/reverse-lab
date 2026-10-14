# Next milestones

Completed in 0.2.0: real Ghidra analysis of the stripped packet fixture, target/profile-bound REA imports, exact replay identity, and an explorer with actual pseudocode landmarks. See [investigation record](ghidra-investigation.md). Completed in 0.3.0: source-known candidate freezing, a disjoint evaluation corpus, native comparison, replay guards and corpus selection in the explorer. See [evaluation procedure](held-out-evaluation.md).

1. **Failure reduction.** Minimize a failing byte sequence while retaining the divergence, original case identity and reduction steps. This would turn the comparison harness into a stronger debugging instrument.
2. **Source-blind challenge.** Freeze/evaluate is implemented for source-known candidates. Next split author/analyst contexts and packages, isolate the analyst from source and record any disclosure. UI hiding and a local freeze do not make this release blind.
3. **Broader evidence import.** The packet procedure/pseudocode carrier import is implemented and exercised. Next support a genuine full exported bundle, retaining address spaces and per-finding provenance, with explicit adapters for different installed-version contracts.
4. **Cross-host execution evidence.** Run the prepared Linux CI, then add a macOS job and compare behavior across arm64/x86-64. Treat disassembly differences as architecture observations, not semantic failures.
5. **Larger domains.** Exhaustively check short state-machine sequences; then add coverage-guided input generation and metamorphic checks for the bounded checksum. Keep sampled and exhaustive domains labeled separately.

AddressSanitizer runtime diagnosis on this macOS host is an optional toolchain follow-up. UBSan already runs on the release corpus. React/graph libraries, live execution from the UI, runtime tracing and more fixtures should be added only when they help an actual investigation.
