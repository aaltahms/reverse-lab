# Stripped packet investigation — 0.2.0

Completed locally October 13, 2026. This is a real REA/Ghidra exercise on an owned C fixture, with the reference source known. It extends the native-disassembly baseline without making the demo depend on an engine installation.

## What was exercised

- Apple Clang 17.0.0 compiled packet `-O2` and the shared batch harness.
- The native `strip` tool removed the evaluate symbol and debug information. macOS ad-hoc signing was recorded as a separate transformation.
- Both the symbol-bearing twin and the stripped executable were actually run on all **638 inputs**; every reference output agreed.
- The Python candidate passed **638/638**. The deliberate endian mutant passed 419 and failed **219** on the stripped artifact, just as on both baseline builds.
- **REA CLI 6.4.0**, **Ghidra 12.1.4**, **Temurin JDK 21.0.12.1+1**, and bundled **Node 24.19.0** performed procedure inventory and decompilation of the arm64 Mach-O artifact.
- Ghidra observed anonymous **FUN_100000460** at **0x100000460**, then returned **555 lines** of actual pseudocode. The reusable `python3 -m lab.decompile` command was exercised end to end after the regression/generation steps.

The final report binds these observations to the executable SHA-256, REA Evidence ID and analysis-profile digest. Unchanged complete CLI responses are preserved as [procedure inventory](../web/data/providers/packet-O2-stripped.procedures.json) and [pseudocode Evidence](../web/data/providers/packet-O2-stripped.decompile.json); their byte hashes are stored in the report. Raw records retain producer-local paths. They do not contain client configuration or authentication tokens.

## Interpretation and boundaries

The procedure address came from the **symbol-bearing twin**, then was checked against Ghidra's actual inventory. It was not independently discovered blind. Stripping is a transformation of an owned compiled target, not evidence that the analyst lacked access to the source.

The real output has three useful landmarks, linked to its current line numbers in the explorer:

| Observation | Current line | Interpretation / corroboration |
| --- | ---: | --- |
| Short input returns 1 | 100 | Agrees with directed empty/short-header execution and the source-known validation contract |
| Invalid packet checksum returns 5 | 327 | Agrees with malformed checksum cases; earlier checks retain their precedence |
| Packed success result | 552–553 | Byte 2 shifts by 16; byte 3 by 8. This supports the authored big-endian interpretation and distinguishes the endian mutant |

The packed result contains `param_1[2] << 0x10` and `param_1[3] << 8`, alongside kind and success-bit packing. The `12 34` counterexample exposes that byte order concretely. Ghidra also emits many inferred temporaries and vector-loop expressions for optimized accumulation; those were retained, not rewritten into a clean candidate or represented as original source. The magic byte may appear as signed `-0x5b`, a decompiler type interpretation of the byte `a5`.

The behavioral oracle verifies the **Python candidate against native execution**. It does not compile the pseudocode or prove its equivalence. The batch harness bounds inputs to 64 bytes; Ghidra displays code paths beyond that tested domain. There is no universal proof, timing claim, runtime trace, cross-architecture validation or source-blind candidate evaluation here.

## Repeat on this host

Run from the project root:

```sh
python3 -m lab.pipeline generate
python3 -m lab.stripped
python3 -m lab.decompile
python3 -m lab.webbuild
```

The ignored `build/toolchains/config.json` selects the local REA launcher, Node, Java home and Ghidra installation. Generation resets derived/provider bindings; stripping and decompilation recreate them against the new hashes. Refresh the preview afterward. Tests also rebuild artifacts, so regenerate the final recording after a test run.

A case-specific replay, expected to exit 1:

```sh
python3 -m lab.pipeline verify --fixture packet --variant O2-stripped \
  --candidate faulty_endian --seed 1380720678 --count 600 --case boundary-006
```

Input `a503123400ee`: compiled output **0x83123400**, mutant **0x83341200**. Artifact hashes are recording-specific, rather than assumed stable across rebuilt binaries.

The sandboxed provider launch failed; the same scoped owned-target analysis succeeded outside the sandbox through the approved terminal execution flow. This did not modify the user's MCP registration, disable client protections, install a commercial engine, or change Gatekeeper configuration. Each REA CLI operation owns an ephemeral Ghidra project and closes its session.

## Optional toolchain on another host

The exercised profile is macOS arm64. The [REA provider installation contract](https://github.com/morluto/rea/blob/main/docs/installation.md#ghidra) describes host/version boundaries; match those to the **installed** CLI version rather than assuming main is the npm release.

This host used the [official Ghidra 12.1.4 release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build) and [Adoptium Temurin](https://adoptium.net/temurin/releases/). The archives were downloaded into `build/toolchains`, checked before extraction, and retained there with their release metadata:

| Tool | Archive / recorded SHA-256 |
| --- | --- |
| Ghidra | `ghidra_12.1.4_PUBLIC_20260921.zip` · `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db` |
| JDK | `OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz` · `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998` |

Ghidra's release lacked a macOS native decompiler. With the existing Clang, make and bison toolchain, the source included in that release was built using the [documented Apple Silicon override](https://github.com/morluto/rea/blob/main/docs/installation.md#macos-arm64-native-decompiler):

```sh
cd "$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/src/decompile/cpp"
make -j4 ghidra_opt ARCH_TYPE="-arch arm64" OSDIR=mac_arm_64
mkdir -p "$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/os/mac_arm_64"
install -m 755 ghidra_opt "$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/os/mac_arm_64/decompile"
```

A native `file` check reported Mach-O arm64. `rea doctor --provider ghidra --format json --full-output` then reported healthy version, JDK, architecture and native-decompiler checks. Readiness alone was not used as proof of decompilation; the actual target operations above supplied that evidence.

On an equipped host with Node 24+ and pnpm, a local CLI installation can use:

```sh
mkdir -p build/toolchains/rea-cli
pnpm --dir build/toolchains/rea-cli add rea-agents@6.4.0 --ignore-scripts \
  --store-dir "$PWD/build/toolchains/pnpm-store"
export PATH="$PWD/build/toolchains/rea-cli/node_modules/.bin:$PATH"
export GHIDRA_INSTALL_DIR="/absolute/path/to/ghidra_12.1.4_PUBLIC"
export JAVA_HOME="/absolute/path/to/your/jdk-21/Contents/Home"
```

Set those paths to the unpacked installations. A full 64-bit JDK includes javac. No `rea setup` is required for this CLI path. The pinned package and dependency lock/store stay inside the ignored toolchain directory; no provider implementation or external executable enters the source release ZIP.

## Import genuine retained records

For a compatible record matching the current stripped artifact:

```sh
python3 -m lab.decompile import --input /path/to/decompile.json \
  --procedures /path/to/procedures.json --rea-version 6.4.0
```

The parser supports the actual REA 6.4.0 complete JSON carrier (`ok/data/meta`) and its inner Evidence object, within an 8 MiB per-record budget. It rejects wrong targets/providers/operations, differing profiles, absent or ambiguous inventory matches, wrong procedure selectors, null pseudocode and a changed present local executable. It preserves full carrier bytes and labels this as **imported-record**, not local provider execution. These checks establish identity consistency; they do not cryptographically authenticate the producer.

## Verification of this milestone

**26 tests passed:** 14 baseline pipeline checks, 3 real stripped-artifact checks, and 9 provider-record import/export checks using the retained real provider outputs. Import tests are parser/identity checks and do not pretend to be live provider tests. The separately executed `lab.decompile` path is the real-provider evidence.

The browser exercised stripped selection, real pseudocode display, landmarks and search jumps, provider limitations, missing-provider states on other builds, deep-link reload, fixture fallback, the existing failing-case inspector, and a 390-pixel layout. See [Ghidra screenshot](screenshots/ghidra.jpg). UBSan remains successful; ASan and hosted CI limitations remain as documented in the [verification record](verification.md).
