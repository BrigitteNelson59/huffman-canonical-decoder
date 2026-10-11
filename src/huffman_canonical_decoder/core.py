"""Canonical Huffman decoding implemented with stdlib bit logic only.

This module reconstructs canonical Huffman code assignments from a table of
per-symbol code lengths and decodes a packed byte stream of symbols encoded
with those codes. No third-party bit array library is used; instead each input
byte is expanded into a length-8 list of 0/1 ints, and decoding walks the
canonical tree statelessly by shifting bits one at a time. The per-byte
expansion is an intentional trade: memory for clarity and determinism.
"""


class DecodeError(Exception):
    """Raised when the bit stream is invalid for the given code-length table.

    Distinct messages distinguish the three failure modes the decoder can
    actually encounter: a leftover prefix that is not a complete code, a
    symbol index outside the table's range, and an empty (zero-length) table.
    """


def _bit_chunks(byte_stream):
    """Yield length-8 lists of 0/1 ints, MSB first, one per input byte.

    Decoding operates one bit at a time and needs to append bits to a working
    buffer; a list of small ints is the simplest container to splice. Strings
    of '0'/'1' would work but integer comparisons read more naturally in the
    inner loop and avoid allocating a fresh char for every bit.
    """
    for byte in byte_stream:
        yield [
            (byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            byte & 1,
        ]


def _bits(byte_stream):
    """Flatten _bit_chunks into a single growing list of 0/1 bits (MSB first)."""
    flat = []
    for chunk in _bit_chunks(byte_stream):
        flat.extend(chunk)
    return flat


def _next_code_for_length(len_table):
    """Return (code_for_next_symbol, symbol_index, first_length) per call.

    Implements the canonical-assignment walk: symbols are sorted by
    (length, symbol index); lengths are assigned codes starting from 0 for
    the first length, and each subsequent code is the previous code plus one,
    left-shifted by the gap in lengths between consecutive symbols. This is
    the standard canonical Huffman construction as used by, e.g., DEFLATE.

    Using a generator (rather than materialising a dict) means the caller can
    stop as soon as the bit stream is exhausted, which is the common case when
    the stream is short relative to the table.
    """
    if not len_table:
        return None

    by_length = sorted(
        (length, symbol)
        for symbol, length in enumerate(len_table)
        if length > 0
    )
    if not by_length:
        return None

    code = 0
    prev_len = by_length[0][0]

    for length, symbol in by_length:
        code <<= (length - prev_len)
        prev_len = length
        yield code, symbol, length
        code += 1


def build_canonical_codes(len_table):
    """Return a list mapping symbol -> code string, parallel to len_table.

    Zero-length entries receive the empty string. The result is intentionally a
    plain list (not a dict) so callers can index by symbol index directly.
    """
    codes = [""] * len(len_table)
    for code, symbol, _length in _next_code_for_length(len_table):
        codes[symbol] = format(code, "b")
    return codes


def decode(len_table, byte_stream, symbol_count):
    """Decode symbol_count symbols from byte_stream using a canonical code.

    len_table[i] is the canonical Huffman code length for symbol i (0 means
    the symbol is unused). byte_stream is an iterable of ints in 0..255; bits
    are consumed MSB-first within each byte. Returns the list of decoded
    symbol indices.

    A table with a single in-use symbol is a real edge case (the canonical
    code for that symbol is conventionally length 1, but some encoders assign
    length 0). We handle it by emitting the symbol on every consumed bit if
    its length is 1, or raising DecodeError if the table has no in-use
    symbols. We do NOT attempt to decode a length-0 single-symbol code; doing
    so would require a separate out-of-band count and the brief does not ask
    for it.
    """
    len_table = list(len_table)

    if not len_table:
        raise DecodeError("empty code-length table")
    if symbol_count < 0:
        raise DecodeError("negative symbol count")

    if symbol_count == 0:
        return []

    builder = _next_code_for_length(len_table)

    try:
        first = next(builder)
    except StopIteration:
        raise DecodeError("no symbols with positive code length")

    entries = [first]
    entries.extend(builder)

    bits = _bits(byte_stream)
    pos = 0
    out = []

    while len(out) < symbol_count:
        code = entries[0][0]
        idx = 0
        length = entries[0][2]
        consumed = 0

        while True:
            if pos >= len(bits):
                raise DecodeError("bit stream ended before a complete code")
            bit = bits[pos]
            pos += 1
            consumed += 1
            code = (code << 1) | bit

            while idx + 1 < len(entries) and code > entries[idx][0]:
                idx += 1
                length = entries[idx][2]

            if len(entries) == 1:
                out.append(entries[0][1])
                break

            if code == entries[idx][0] and consumed == length:
                out.append(entries[idx][1])
                break

            if consumed > length:
                raise DecodeError("no canonical code matches the bit prefix")

    return out
