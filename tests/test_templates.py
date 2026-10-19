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
KEYNOTE_SOURCE_HASH = TEMPLATES / "keynote-source.sha256"
REBUILD = (
    'python -m fwl_visual_language.slides "templates/Forming Worlds.pptx" '
    "--figure templates/sample-figure.png"
)


def parts(path):
    """Return every part of a zip package by name; zip time stamps are left out."""
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def content_hash(path):
    """Return the SHA-256 of the part names and contents of a zip package."""
    h = hashlib.sha256()
    for name, data in sorted(parts(path).items()):
        h.update(name.encode() + b"\0" + data)
    return h.hexdigest()


def test_the_built_pptx_matches_a_fresh_build(tmp_path):
    pytest.importorskip("pptx")
    fresh = slides.build_slides(tmp_path / "fresh.pptx", figure=FIGURE)
    built, new = parts(PPTX), parts(fresh)
    assert sorted(built) == sorted(new), f"rebuild it: {REBUILD}"
    differ = [n for n in new if built[n] != new[n]]
    assert differ == [], f"{differ} differ; rebuild it: {REBUILD}"


def test_the_keynote_theme_was_made_from_the_current_keynote_source(tmp_path):
    pytest.importorskip("pptx")
    fresh = slides.build_slides(tmp_path / "k.pptx", keynote=True, figure=FIGURE)
    new = content_hash(fresh)
    assert new == KEYNOTE_SOURCE_HASH.read_text().split()[0], (
        "the Keynote source changed: make Forming Worlds.kth again in Keynote "
        f"and write {new} to templates/keynote-source.sha256 (see README)"
    )


def test_the_keynote_theme_holds_one_master_per_layout_and_the_sample_figure():
    with zipfile.ZipFile(KTH) as z:
        names = z.namelist()
        masters = [
            z.read(n) for n in names if re.fullmatch(r"Index/TemplateSlide(-\d+-\d+)?\.iwa", n)
        ]
        media = [z.read(n) for n in names if n.startswith("Data/")]
    # Keynote stores each master name as a length-prefixed string.
    found = [[n for n in slides.LAYOUTS if bytes([len(n)]) + n.encode() in m] for m in masters]
    assert sorted(found) == sorted([n] for n in slides.LAYOUTS)
    assert "preview.jpg" in names
    assert any(m == FIGURE.read_bytes() for m in media)
