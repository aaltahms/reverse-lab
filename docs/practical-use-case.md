# Catch a packet-decoder regression

**User:** a firmware or host-tool developer comparing two implementations of one binary packet contract.

**Task:** replace or reconstruct a decoder without silently changing byte order, validation order or checksum behavior.

Imagine firmware uses a C decoder while a new Python host tool needs equivalent behavior. The reference executable remains the behavioral oracle. A replacement that reads the sequence bytes in the wrong order can accept a valid packet and return the wrong sequence number. A checksum test alone would miss this error.

## The working example

The owned packet format is `A5 | kind | sequence-high | sequence-low | payload-length | payload | sum8`. This is an educational contract, not an identified device protocol.

For input `a503123400ee`:

| Field or output | Correct interpretation | Deliberate endian fault |
| --- | --- | --- |
| Sequence bytes | `12 34` | `12 34` |
| Sequence value | `0x1234` / 4660 | `0x3412` / 13330 |
| Returned packed word | `0x83123400` | `0x83341200` |
| Packet validation | Accepted | Accepted |

The failure is observable even though both implementations accept the packet. Symmetric sequence bytes such as `11 11` conceal the fault, which explains why a few passing tests are insufficient.

Open **Binary packet decoder → Verification → Development corpus → Endian fault (deliberate) → Failures only**, then select **boundary-006**. The explorer links the input, both outputs, candidate source, artifact identity and replay command. The stripped build also has actual Ghidra pseudocode: its packed-result landmark shows where the two sequence bytes are shifted.

After generating native artifacts locally, replay the example:

```sh
python3 -m lab.pipeline verify --fixture packet --variant O2 \
  --candidate faulty_endian --seed 1380720678 --count 600 --case boundary-006
```

Exit 1 is the expected, detected mismatch. Switch to the correct candidate and the same input agrees. Held-out evaluation checks the frozen candidate on 1,000 further byte sequences absent from the development corpus. The included packet mutant fails 333 of those inputs per build.

## Practical value and remaining scope

The project is useful today as a reproducible comparison lab and teaching example: someone can inspect a concrete endian regression and rerun the native comparison. It is also a small foundation for validating an actual decoder replacement.

An actual firmware parser needs its own reference/candidate adapter and captured or specified test inputs. The current release does not provide a generic binary-import interface, physical-device tests, universal equivalence, or a blind reconstruction claim. Its fixtures and candidates were authored with source known. An external parser case study and automatic failure reduction are the next improvements that would add the most practical value.
