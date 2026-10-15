// Interpret recorded uint32 outputs for display; this does not execute a decoder.
const errors = {
  1: 'The packet is too short.',
  2: 'The first byte does not identify this packet format.',
  3: 'The message type is outside the supported range.',
  4: 'The payload length does not match the packet size.',
  5: 'The checksum does not match the packet contents.',
};

export function packetOutput(value) {
  if (!Number.isInteger(value) || value < 0 || value > 0xffffffff) {
    throw new Error('Recorded packet output must be an unsigned 32-bit integer');
  }
  if (value < 0x80000000) {
    return {accepted: false, code: value, reason: errors[value] || `Rejected with code ${value}.`, sequence: null};
  }
  return {accepted: true, sequence: (value >>> 8) & 0xffff,
    kind: (value >>> 24) & 0x7f, payloadSum: value & 0xff};
}

export function explainPacket(record, intentionalFault) {
  const original = packetOutput(record.expected);
  const replacement = packetOutput(record.actual);
  const matches = record.expected === record.actual;
  const pair = record.hex.slice(4, 8).match(/../g) || [];
  if (!matches) {
    return {original, replacement, matches, kind: 'different',
      title: original.accepted && replacement.accepted
        ? 'Both accept the packet. The message number is different.'
        : 'The two versions disagree about this packet.',
      detail: original.accepted && replacement.accepted
        ? `The replacement swaps the two sequence bytes: ${pair.join(' ')} becomes ${[...pair].reverse().join(' ')}. That changes the message number even though both versions accept the packet.`
        : 'A replacement must preserve rejection behavior as well as the values returned for valid packets.'};
  }
  if (!original.accepted) {
    return {original, replacement, matches, kind: 'rejected',
      title: 'Both versions reject this packet.',
      detail: `${original.reason} No message number is decoded. This input checks validation; it does not test the order of the sequence bytes.`};
  }
  if (intentionalFault && pair.length === 2 && pair[0] === pair[1]) {
    return {original, replacement, matches, kind: 'hidden',
      title: 'The results match, but this packet hides the bug.',
      detail: `Both sequence bytes are ${pair[0]}. Reversing them changes nothing. Try the packet with different sequence bytes to expose the byte-order mistake.`};
  }
  return {original, replacement, matches, kind: 'agreement',
    title: 'Both versions read the same values for this packet.',
    detail: 'The corrected version keeps the two sequence bytes in the same order as the original. This example now agrees. The full test set checks more inputs; one matching packet cannot establish correctness.'};
}
