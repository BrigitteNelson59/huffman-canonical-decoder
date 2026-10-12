# huffman-canonical-decoder

Reconstructs canonical Huffman codes from a per-symbol code-length table and decodes a packed byte stream using only the Python standard library.

```python
from huffman_canonical_decoder import build_canonical_codes, decode, DecodeError

len_table = [1, 2, 2]          # symbol 0: len 1, symbols 1,2: len 2
codes = build_canonical_codes(len_table)
# codes == ['0', '10', '11']

symbols = decode(len_table, [0x58], 4)   # bits 0 1 0 1 1 0 -> 0,1,2,0
# symbols == [0, 1, 2, 0]
```

## Why this exists

Canonical Huffman codes can be reconstructed from just the per-symbol code lengths, so a compressed format that stores lengths (as DEFLATE and JPEG do) needs no side table of actual codewords. This library does exactly that reconstruction and the inverse walk to decode symbols, with no third-party dependency and no bitarray. Bits are consumed MSB-first within each byte.

The trade-off is simplicity over throughput: input bytes are expanded into lists of 0/1 ints before decoding. That is fine for small streams and for code that must run in a locked-down environment where installing packages is not an option. For high-throughput decoding of megabyte streams, a C-backed bit reader would be a better choice; this library is not that.

## Edge cases worth knowing

- A symbol with length 0 is treated as unused and never appears in the output.
- A single in-use symbol must have length 1; a length-0 single-symbol code (which some encoders produce) is not supported, because decoding it would require an out-of-band symbol count that this library does not take.
- If the bit stream ends mid-code, or contains a bit prefix that no canonical code in the table can match, `decode` raises `DecodeError`. Trailing bits in the final byte beyond those needed for `symbol_count` are silently ignored.
- `symbol_count` is the number of symbols to decode, not the number of bytes: the decoder stops as soon as that many symbols have been produced.
