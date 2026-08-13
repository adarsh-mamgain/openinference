"""A byte-level BPE tokenizer built from scratch.

This implements the OpenAI GPT-2 / LLaMA / Qwen tokenization pipeline without a
tokenizer library:

1. ``NFC`` Unicode normalization
2. GPT-2 style pre-tokenization (a regex that cuts text into word-ish chunks)
3. ``ByteLevel``: map each byte of a chunk to a printable Unicode char (the
   classic GPT-2 byte-to-unicode table, where space becomes ``Ġ``)
4. Greedy BPE merge over a chunk's symbols using the merge ranks, then map to
   token ids

The vocab, merges and special tokens come from ``tokenizer.json``. Only the
standard library (``json``, ``re``, ``unicodedata``, ``functools``) is used.
"""

import functools
import json
import unicodedata
from pathlib import Path

import regex as re

# GPT-2 style split regex (matches the one in Qwen's tokenizer.json).
# Splits into word chunks, apostrophe contractions, numbers, run of
# non-letter/non-number symbols, newlines and whitespace.
SPLIT_RE = re.compile(
    r"(?i:'s|'t|'re|'ve|'m|'ll|'d)"
    r"|[^\r\n\p{L}\p{N}]?\p{L}+"
    r"|\p{N}"
    r"| ?[^\s\p{L}\p{N}]+[\r\n]*"
    r"|\s*[\r\n]+"
    r"|\s+(?!\S)"
    r"|\s+"
)


def _bytes_to_unicode() -> tuple[dict[int, str], dict[str, int]]:
    """GPT-2 byte -> printable Unicode mapping (and its inverse).

    Printable/mergeable bytes map to their ASCII/Latin-1 selves; all remaining
    bytes map to Unicode characters starting after ``\\u0100``. This guarantees
    every byte is a unique, displayable symbol. Space (32) ends up as ``Ġ``.
    """
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8 + n)
            n += 1
    byte_to_uni = dict(zip(bs, [chr(c) for c in cs]))
    uni_to_byte = {v: k for k, v in byte_to_uni.items()}
    return byte_to_uni, uni_to_byte


_BYTE_TO_UNI, _UNI_TO_BYTE = _bytes_to_unicode()


class BPETokenizer:
    """Encode text to token ids and decode ids back to text."""

    def __init__(self, tokenizer_json: str | Path) -> None:
        data = json.loads(Path(tokenizer_json).read_text(encoding="utf-8"))
        model = data["model"]

        self._vocab: dict[str, int] = model["vocab"]          # token -> id
        self._ids: dict[int, str] = {v: k for k, v in self._vocab.items()}

        # Special / added tokens are matched verbatim during encoding.
        self._special: dict[str, int] = {
            t["content"]: t["id"] for t in data.get("added_tokens", []) if t.get("special")
        }

        # Merge ranks: (left_symbol, right_symbol) -> priority (lower = earlier).
        self._merges: dict[tuple[str, str], int] = {}
        for rank, merge in enumerate(model["merges"]):
            a, b = merge.split(" ")
            self._merges[(a, b)] = rank

        # Match a single special token first so we split on them.
        self._special_re = re.compile("|".join(re.escape(s) for s in self._special))

    # -- public API -------------------------------------------------------

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        text = unicodedata.normalize("NFC", text)
        if add_special_tokens:
            ids = [self._special.get("<|im_start|>")]
        else:
            ids = []
        for piece in self._split_on_specials(text):
            if piece in self._special:
                ids.append(self._special[piece])
            else:
                ids.extend(self._encode_words(piece))
        if add_special_tokens:
            ids.append(self._special.get("<|im_end|>"))
        return [i for i in ids if i is not None]

    def decode(self, ids: list[int]) -> str:
        """Map ids back to text.

        Byte-level tokens concatenate to a Latin-1 string whose characters are
        the byte-encoded symbols; reversing the byte->unicode table yields the
        original UTF-8 bytes. Special tokens are emitted verbatim.
        """
        symbol_parts: list[str] = []
        for token_id in ids:
            token = self._ids.get(token_id)
            if token is None:
                continue
            if token in self._special:
                symbol_parts.append(token)  # e.g. <|im_start|>
            else:
                symbol_parts.append(token)

        # Translate the rendered symbols back into raw bytes.
        raw_bytes = bytearray()
        for symbol in "".join(symbol_parts):
            byte = _UNI_TO_BYTE.get(symbol)
            if byte is not None:
                raw_bytes.append(byte)
            else:
                # Not a byte symbol (e.g. a special token piece): append its
                # UTF-8 bytes so it survives the round-trip.
                raw_bytes.extend(symbol.encode("utf-8", errors="ignore"))
        try:
            return raw_bytes.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return raw_bytes.decode("utf-8", errors="ignore")

    # -- internals --------------------------------------------------------

    def _split_on_specials(self, text: str) -> list[str]:
        return [p for p in self._special_re.split(text) if p != ""]

    def _encode_words(self, chunk: str) -> list[int]:
        """Encode a single pre-tokenized chunk (bytes -> unicode -> merges)."""
        rendered = "".join(_BYTE_TO_UNI[b] for b in chunk.encode("utf-8"))
        tokens = self._bpe(rendered)
        return [self._vocab[t] for t in tokens]

    def _bpe(self, rendered: str) -> list[str]:
        """Greedily merge the rendered symbols of one chunk."""
        word = tuple(rendered)
        if len(word) == 1:
            return [rendered]

        while len(word) > 1:
            pairs = [(word[i], word[i + 1]) for i in range(len(word) - 1)]
            # Pick the merge with the lowest rank; skip pairs that don't exist.
            candidates = [(self._merges[p], p) for p in pairs if p in self._merges]
            if not candidates:
                break
            _, (a, b) = min(candidates, key=lambda c: c[0])

            new_word = []
            i = 0
            while i < len(word):
                if i < len(word) - 1 and word[i] == a and word[i + 1] == b:
                    new_word.append(a + b)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            word = tuple(new_word)

        return list(word)

    # convenience
    encode_text = encode
    decode_ids = decode

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)
