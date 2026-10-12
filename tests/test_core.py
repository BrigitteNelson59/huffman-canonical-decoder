import unittest

from huffman_canonical_decoder import build_canonical_codes, decode, DecodeError


class TestBuildCanonicalCodes(unittest.TestCase):
    def test_simple_two_symbol_table(self):
        # Symbols 0 and 1 each get length 1; canonical codes are '0' and '1'.
        self.assertEqual(build_canonical_codes([1, 1]), ["0", "1"])

    def test_three_symbols_with_varying_lengths(self):
        # length 1 -> '0'; length 2 -> '10' (0<<1 + 0), '11' (0<<1 + 1).
        self.assertEqual(build_canonical_codes([1, 2, 2]), ["0", "10", "11"])

    def test_zero_length_means_unused(self):
        self.assertEqual(build_canonical_codes([0, 1, 2]), ["", "0", "10"])

    def test_empty_table(self):
        self.assertEqual(build_canonical_codes([]), [])

    def test_all_unused(self):
        self.assertEqual(build_canonical_codes([0, 0, 0]), ["", "", ""])

    def test_ordering_is_by_length_then_symbol(self):
        # Symbol 2 has length 1 so it gets '0'; symbols 0 and 1 get '10','11'.
        self.assertEqual(build_canonical_codes([2, 2, 1]), ["10", "11", "0"])


class TestDecode(unittest.TestCase):
    def test_decode_two_symbols(self):
        # Table [1,1] => 0->'0', 1->'1'. Bytes 0b01_00000 decodes to 0 then 1.
        self.assertEqual(decode([1, 1], [0b01000000], 2), [0, 1])

    def test_decode_three_symbol_canonical(self):
        # Table [1,2,2] => 0->'0', 1->'10', 2->'11'.
        # Bits: 0 1 0 1 1 0 -> 0,1,2,0
        # Byte: 0b01011000 = 0x58
        self.assertEqual(decode([1, 2, 2], [0x58], 4), [0, 1, 2, 0])

    def test_decode_spanning_byte_boundary(self):
        # Table [1,2,2]. Bits across two bytes: 1 1 0 1 1 1 0 0 | 0 0 0...
        # 11->2, 0->0, 11->2, 10->1, 0->0
        # Byte1: 0b11011100 = 0xDC, Byte2: 0b00000000 = 0x00
        self.assertEqual(
            decode([1, 2, 2], [0xDC, 0x00], 5),
            [2, 0, 2, 1, 0],
        )

    def test_decode_all_zeros_stream(self):
        # Table [1,1]. A stream of all zero bits decodes to all symbol 0.
        self.assertEqual(decode([1, 1], [0x00, 0x00], 16), [0] * 16)

    def test_decode_all_ones_stream(self):
        # Table [1,1]. All ones -> all symbol 1.
        self.assertEqual(decode([1, 1], [0xFF, 0xFF], 16), [1] * 16)

    def test_decode_single_symbol_table(self):
        # A single in-use symbol with length 1. Every bit emits the symbol.
        self.assertEqual(decode([0, 1], [0xFF], 8), [1] * 8)

    def test_decode_zero_symbols_requested(self):
        self.assertEqual(decode([1, 1], [0x00], 0), [])

    def test_decode_empty_table_raises(self):
        with self.assertRaises(DecodeError):
            decode([], [0x00], 1)

    def test_decode_all_unused_raises(self):
        with self.assertRaises(DecodeError):
            decode([0, 0, 0], [0x00], 1)

    def test_decode_truncated_stream_raises(self):
        # Table [1,2,2]: valid codes are 0, 10, 11. Request 4 symbols from
        # a single byte 0b01000000. Bits: 0 1 0 0 0 0 0 0. The first three
        # symbols (0, 1, 0) consume 4 bits, leaving 4 zero bits which decode
        # to two more symbol-0s, so 5 symbols fit. Request 9 symbols instead:
        # after 8 bits the stream ends mid-decode, before 9 symbols exist.
        with self.assertRaises(DecodeError):
            decode([1, 2, 2], [0b01000000], 9)

    def test_decode_invalid_prefix_raises(self):
        # Table [1,3]: canonical codes are 0->'0', 1->'100'. A prefix '11'
        # can never match any canonical code. Feed 0b11_000000 and request 1
        # symbol; the decoder reads '1' (no match), '11' (no match), then has
        # consumed 3 bits with no match, triggering DecodeError.
        with self.assertRaises(DecodeError):
            decode([1, 3], [0b11000000], 1)

    def test_decode_negative_count_raises(self):
        with self.assertRaises(DecodeError):
            decode([1, 1], [0x00], -1)

    def test_decode_ignores_trailing_bits(self):
        # Only the bits needed for symbol_count are consumed; trailing bits
        # in the last byte are ignored.
        self.assertEqual(decode([1, 1], [0b01_111111], 2), [0, 1])


if __name__ == "__main__":
    unittest.main()
