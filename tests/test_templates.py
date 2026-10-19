"""Built slide templates in ``templates/`` (the .pptx and the Keynote theme)."""

import hashlib
import re
import zipfile
from pathlib import Path

import pytest

from fwl_visual_language import slides

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
PPTX = TEMPLATES / "Forming Worlds.pptx"
KTH = TEMPLATES / "Forming Worlds.kth"
FIGURE = TEMPLATES / "sample-figure.png"
HASHES = TEMPLATES / "keynote-source.sha256"
REBUILD = (
    'python -m fwl_visual_language.slides "templates/Forming Worlds.pptx" '
    "--figure templates/sample-figure.png"
)
REMAKE_KTH = "make Forming Worlds.kth again in Keynote (README, Slides)"


def parts(path):
    """Return every part of a zip package by name; zip time stamps are left out."""
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def content_hash(path):
    """Return the SHA-256 over the part names and the SHA-256 of each part's contents."""
    h = hashlib.sha256()
    for name, data in sorted(parts(path).items()):
        h.update(name.encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


def recorded_hashes():
    """Return the hashes in ``keynote-source.sha256`` by label (``source``, ``kth``)."""
    rows = {}
    for line in filter(str.strip, HASHES.read_text().splitlines()):
        fields = line.split()
        assert len(fields) == 2 and fields[1] not in rows, f"{HASHES.name}: bad line {line!r}"
        rows[fields[1]] = fields[0]
    assert sorted(rows) == ["kth", "source"], f"{HASHES.name} needs a source and a kth line"
    assert all(re.fullmatch("[0-9a-f]{64}", h) for h in rows.values()), rows
    return rows


def _varint(n):
    out = bytearray()
    while True:
        out.append(n & 0x7F | (0x80 if n > 0x7F else 0))
        n >>= 7
        if not n:
            return bytes(out)


def _snappy(b):
    """Decompress one raw Snappy block."""
    i, size, shift = 0, 0, 0
    while True:
        size |= (b[i] & 0x7F) << shift
        shift += 7
        i += 1
        if b[i - 1] < 0x80:
            break
    out = bytearray()
    while i < len(b):
        tag, kind = b[i], b[i] & 3
        i += 1
        if kind == 0:  # literal; lengths above 60 follow in 1 to 4 bytes
            n = tag >> 2
            if n >= 60:
                n, i = int.from_bytes(b[i : i + n - 59], "little"), i + n - 59
            out += b[i : i + n + 1]
            i += n + 1
            continue
        if kind == 1:
            n, off, i = (tag >> 2 & 7) + 4, (tag >> 5) << 8 | b[i], i + 1
        else:
            w = 2 if kind == 2 else 4
            n, off, i = (tag >> 2) + 1, int.from_bytes(b[i : i + w], "little"), i + w
        assert 0 < off <= len(out), "bad snappy offset"
        for _ in range(n):  # a copy may overlap its own output
            out.append(out[-off])
    assert len(out) == size
    return bytes(out)


def iwa(data):
    """Decompress a Keynote ``.iwa`` part: chunks of a 0 byte, a 3-byte length, raw Snappy."""
    out, i = b"", 0
    while i < len(data):
        assert data[i] == 0, "not an iwa chunk"
        n = int.from_bytes(data[i + 1 : i + 4], "little")
        out += _snappy(data[i + 4 : i + 4 + n])
        i += 4 + n
    return out


def test_the_built_pptx_matches_a_fresh_build(tmp_path):
    pptx = pytest.importorskip("pptx")
    fresh = slides.build_slides(tmp_path / "fresh.pptx", figure=FIGURE)
    built, new = parts(PPTX), parts(fresh)
    hint = f"rebuild it (python-pptx {pptx.__version__}): {REBUILD}"
    assert sorted(built) == sorted(new), hint
    differ = [n for n in new if built[n] != new[n]]
    assert differ == [], f"{differ} differ; {hint}"


def test_the_builder_still_writes_the_keynote_source_of_the_theme(tmp_path):
    pptx = pytest.importorskip("pptx")
    fresh = slides.build_slides(tmp_path / "k.pptx", keynote=True, figure=FIGURE)
    new = content_hash(fresh)
    assert new == recorded_hashes()["source"], (
        f"the Keynote source changed (python-pptx {pptx.__version__}): {REMAKE_KTH}, "
        f"then write source {new} to {HASHES.name}"
    )


def test_the_keynote_theme_is_the_one_recorded_with_its_source():
    new = hashlib.sha256(KTH.read_bytes()).hexdigest()
    assert new == recorded_hashes()["kth"], (
        f"{KTH.name} is not the theme recorded in {HASHES.name}: {REMAKE_KTH}, "
        f"then write kth {new} there"
    )


def test_the_keynote_theme_holds_one_master_per_layout_and_the_sample_figure():
    with zipfile.ZipFile(KTH) as z:
        names = z.namelist()
        masters = [
            iwa(z.read(n)) for n in names if re.fullmatch(r"Index/TemplateSlide(-\d+-\d+)?\.iwa", n)
        ]
        media = [z.read(n) for n in names if n.startswith("Data/")]
    # Each master stores its name as a length-prefixed protobuf string.
    keys = {n: _varint(len(n.encode())) + n.encode() for n in slides.LAYOUTS}
    found = [[n for n, key in keys.items() if key in m] for m in masters]
    assert sorted(found) == sorted([n] for n in slides.LAYOUTS), f"masters: {found}; {REMAKE_KTH}"
    assert "preview.jpg" in names, f"no preview.jpg; {REMAKE_KTH}"
    has_figure = any(m == FIGURE.read_bytes() for m in media)
    assert has_figure, f"{FIGURE.name} is not in {KTH.name}; {REMAKE_KTH}"


def test_the_iwa_reader_decodes_literals_and_overlapping_copies():
    # "abcabcabca": literal "abc", then a 1-byte-offset copy of 7 bytes at offset 3.
    block = bytes([10, 2 << 2]) + b"abc" + bytes([(7 - 4) << 2 | 1, 3])
    chunk = b"\0" + len(block).to_bytes(3, "little") + block
    assert iwa(chunk) == b"abcabcabca"
    assert iwa(chunk + chunk) == b"abcabcabca" * 2
    # A copy with a 2-byte offset.
    assert _snappy(bytes([5, 0 << 2]) + b"x" + bytes([(4 - 1) << 2 | 2, 1, 0])) == b"xxxxx"
    # A 300-byte literal (length in 2 bytes), then 5 bytes copied from offset 260.
    text = bytes(range(256)) + bytes(range(44))
    block = _varint(305) + bytes([61 << 2]) + (299).to_bytes(2, "little") + text
    block += bytes([(5 - 4) << 2 | 1 | (260 >> 8) << 5, 260 & 0xFF])
    assert _snappy(block) == text + text[40:45]
    assert _varint(5) == b"\x05" and _varint(300) == b"\xac\x02"
    with pytest.raises(AssertionError, match="not an iwa chunk"):
        iwa(b"\1abc")
    with pytest.raises(AssertionError, match="bad snappy offset"):
        _snappy(bytes([5, 0 << 2]) + b"a" + bytes([0 << 2 | 1, 0]))
