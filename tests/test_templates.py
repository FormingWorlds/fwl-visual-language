"""Built slide templates in ``templates/`` (the .pptx and the Keynote theme)."""

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("pptx")
from fwl_visual_language import slides  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
PPTX = TEMPLATES / "Forming Worlds.pptx"
KTH = TEMPLATES / "Forming Worlds.kth"
FIGURE = TEMPLATES / "sample-figure.png"


def parts(path):
    """Return every part of a zip package by name; zip time stamps are left out."""
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def test_the_built_pptx_matches_a_fresh_build(tmp_path):
    fresh = slides.build_slides(tmp_path / "fresh.pptx", figure=FIGURE)
    built, new = parts(PPTX), parts(fresh)
    assert sorted(built) == sorted(new)
    assert [n for n in new if built[n] != new[n]] == []


def test_the_keynote_theme_holds_every_master_and_the_sample_figure():
    with zipfile.ZipFile(KTH) as z:
        names = z.namelist()
        index = b"".join(z.read(n) for n in names if n.startswith("Index/"))
        media = [z.read(n) for n in names if n.startswith("Data/")]
    assert "preview.jpg" in names
    missing = [name for name in slides.LAYOUTS if name.encode() not in index]
    assert missing == []
    assert FIGURE.read_bytes() in media
