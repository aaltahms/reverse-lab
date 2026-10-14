# ReverseLab in Aymen's project portfolio

Assessment based on the local project and publication records, October 14, 2026. Public repositories were not re-audited for this assessment.

## Useful applications

- **Learning native software analysis:** compare the same C function at `-O0`, `-O2`, and, for packets, after stripping; connect assembly and actual Ghidra pseudocode to a behavioral hypothesis.
- **Checking a reimplementation:** execute a compiled reference and a Python candidate on identical inputs, retain disagreements, and replay an exact counterexample. Useful as a small model of validating a parser or a legacy algorithm replacement.
- **Testing experimental quality:** deliberately swap packet byte order, observe why some inputs still pass, and evaluate frozen candidates on a disjoint corpus. This makes the limits of a test result visible.
- **Reviewing an investigation:** share a portable, read-only explorer containing artifact identities, tool outputs, authored interpretations, candidate code, reference source and reproducible commands.

The current tool supports three owned toy fixtures and their fixed 64-byte batch harness. It is not an arbitrary-binary analyzer, automatic source recovery service or production protocol identification tool.

## How the projects complement each other

| Project | Main evidence of ability | Role in the portfolio |
| --- | --- | --- |
| ResolveAI | A usable diagnostics product, controlled workflows, testing and delivery | Strongest end-user software project in the local publication review |
| ReverseLab | C/Python native tooling, compiler observations, real Ghidra integration, artifact provenance, differential verification and an inspectable UI | A featured systems/software verification project; adds depth beyond another web app |
| RV32I execution-unit verification | RTL behavior, directed/random checking and specification boundaries | More directly relevant to digital design and hardware verification; describe it as an execution unit, not a completed CPU |
| Hierarchical FPGA adder | Exhaustive arithmetic simulation and reproducible verification | A narrower, completed hardware example supporting the broader RTL work |
| CI incident automation and course labs | Workflow automation or specific course techniques | Supporting examples; select those relevant to the role rather than showing every lab equally |

For systems or embedded applications, a useful featured group is ResolveAI, ReverseLab and RV32I verification. For RTL-focused applications, put RV32I and the FPGA work first. This ordering is a judgment about relevance and current evidence, not a prediction of hiring outcomes.

ReverseLab's strongest story is the chain from a claim to evidence and a replayable failure. Test counts support that story, but repeated inputs across optimization builds are not independent discoveries. Its source-known and Codex-assisted authorship should remain visible.

## Concise portfolio description

**ReverseLab — native behavior verification and evidence explorer.** Built a C/Python pipeline that compiles three owned fixtures, compares independently expressed candidates against native execution, and exposes artifact-bound assembly, real REA/Ghidra pseudocode and replayable endian counterexamples. Added candidate freezing and disjoint held-out evaluation, with a dependency-free browser explorer and local regression checks. Source-known educational project built with Codex assistance.

## A two-minute demonstration

1. Open the packet's stripped build and show the Ghidra result-packing landmark: where do the sequence bytes go?
2. Switch to the intentional endian fault and inspect an asymmetric sequence; explain why symmetric sequences still pass.
3. Switch to held-out evaluation and show the frozen candidate, new seed, zero input overlap and one exact replay command.
4. Explain one limitation: sampled agreement is not universal equivalence, and source was known.

This walkthrough shows understanding of the implementation and experimental choices. It is stronger evidence than presenting the screenshot or total test count alone.
