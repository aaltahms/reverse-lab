# Comparison-first interface — v0.4, October 15, 2026

The previous opening screen presented a checksum, compiler variants, an investigation path, six tabs, interpretation notes and test counts. It did not first establish what someone could do or what result mattered. A technically inspectable implementation was described too confidently as a polished user experience.

The user requested a mix of a simple workbench and a guided explanation. The new default screen follows one concrete example:

1. Choose a recorded packet. The input bytes are shared by both implementations.
2. Read the original C and replacement Python message numbers side by side: 4,660 versus 13,330 for the default packet.
3. Read a short explanation, then compare the corrected version without leaving the page.

The matching-bytes example warns that an equal result can conceal the deliberate bug. Damaged-checksum and empty-input examples show rejection reasons and no decoded message number. This avoids presenting rejected input as a successful decode.

Code, build identities, full test tables, original source and actual Ghidra output remain in the technical view. It has one tab bar; the duplicate five-part path was removed. Existing explicit view/case URLs still open that view. The return control opens the simple comparison. The portfolio and README now link to the new default rather than directly to a dense test table.

## Verification and limits

Seven JavaScript checks cover uint32 interpretation, invalid-record rejection, all rejection reasons, the actual asymmetric packet, concealed symmetric-byte faults, checksum rejection and consistency with every recorded packet comparison in the baseline report. Browser checks exercised all four input choices, version switching, technical drill-down, retained case selection, Ghidra access, reload persistence and browser history. A 390-pixel viewport showed no page-level horizontal overflow; both message numbers fit their columns.

The UI reads recorded native outputs. It does not run either decoder in the browser, accept arbitrary uploaded programs, or add actual-device validation. The existing native artifacts, models, freeze receipt and Ghidra recordings remain unchanged. This is an interface revision, not additional behavioral evidence or proof of a new practical integration.

This review and browser QA are not an independent usability study. The first revision still needs feedback from the person who reported the confusion. For future project work, start with one identifiable user task, its input and its useful output; expose implementation detail when it helps that task.
