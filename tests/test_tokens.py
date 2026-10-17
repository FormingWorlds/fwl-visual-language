"""Tests for the token file and the colour helpers."""

import math

import numpy as np
import pytest
from colorspacious import cspace_convert

import fwl_visual_language as fvl
from fwl_visual_language import _oklch_to_linear, _step_oklch

CVD = [None] + [
    {"name": "sRGB1+CVD", "cvd_type": t, "severity": 100}
    for t in ("deuteranomaly", "protanomaly", "tritanomaly")
]


def min_delta_e(hexes):
    """Smallest pairwise CAM02-UCS distance over normal vision and 3 CVD types."""
    cols = np.array([fvl.hex_to_rgb(h) for h in hexes])
    worst = math.inf
    for cvd in CVD:
        sim = cols if cvd is None else np.clip(cspace_convert(cols, cvd, "sRGB1"), 0, 1)
        ucs = cspace_convert(sim, "sRGB1", "CAM02-UCS")
        d = np.linalg.norm(ucs[:, None] - ucs[None], axis=-1)
        worst = min(worst, d[np.triu_indices(len(cols), 1)].min())
    return worst


def test_website_values_round_trip():
    # values a browser paints for the website tokens (Chrome, sRGB profile)
    assert fvl.color("signal-500") == "#0072A1"
    assert fvl.color("ink-950") == "#010305"
    assert fvl.color("ink-50") == "#F3F6F9"
    assert fvl.color("magma-600") == "#B74B21"
    assert fvl.color("signal-600") == "#005B87"


@pytest.mark.parametrize("name", ["ink", "signal", "magma"])
def test_every_oklch_step_lies_inside_srgb(name):
    # out-of-gamut steps render differently per browser and screen
    for step in fvl.tokens()["ramps"][name]["steps"]:
        lch = _step_oklch(name, step)
        if lch is None:
            continue
        lin = _oklch_to_linear(*lch)
        assert all(-1e-4 <= v <= 1 + 1e-4 for v in lin), (name, step, lin)


def test_gamut_test_catches_an_out_of_gamut_step():
    lin = _oklch_to_linear(0.44, 0.115, 233)
    assert not all(-1e-4 <= v <= 1 + 1e-4 for v in lin)


def test_oklch_to_hex_reduces_chroma_out_of_gamut():
    assert fvl.oklch_to_hex(0.44, 0.115, 233) == "#005A7C"
    assert fvl.oklch_to_hex(0.5, 0.0, 0) == fvl.oklch_to_hex(0.5, 0.0, 180)


def test_oklch_to_hex_rejects_negative_chroma():
    with pytest.raises(ValueError, match="chroma"):
        fvl.oklch_to_hex(0.5, -0.1, 0)


def test_oklch_css_matches_website_form():
    assert fvl.oklch_css("ink", "950") == "oklch(0.090 0.012 240)"
    assert fvl.oklch_css("magma", "600") == "oklch(0.550 0.150 40)"
    assert fvl.oklch_css("signal", "500") == "#0072A1"


@pytest.mark.parametrize("bad", ["#12345", "#GGGGGG", "red", ""])
def test_hex_to_rgb_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        fvl.hex_to_rgb(bad)


def test_contrast_known_values():
    assert fvl.contrast("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert fvl.contrast("#777777", "#777777") == pytest.approx(1.0)
    assert fvl.contrast("#0072A1", "#FFFFFF") == fvl.contrast("#FFFFFF", "#0072A1")


def test_color_accepts_hex_and_rejects_unknown_steps():
    assert fvl.color("#abcdef") == "#ABCDEF"
    with pytest.raises(KeyError, match="no step"):
        fvl.color("ink-123")
    with pytest.raises(KeyError):
        fvl.color("plum-500")


@pytest.mark.parametrize("mode", fvl.MODES)
def test_roles_resolve_and_text_is_readable(mode):
    r = fvl.roles(mode)
    for fg in ("heading", "text", "link", "link-hover"):
        assert fvl.contrast(r[fg], r["background"]) >= 4.5, (mode, fg)
        assert fvl.contrast(r[fg], r["surface"]) >= 4.5, (mode, fg)
    assert fvl.contrast(r["muted"], r["background"]) >= 3.0, mode
    assert fvl.role(mode, "link") == r["link"]


def test_all_modes_define_the_same_roles():
    names = {m: set(fvl.tokens()["roles"][m]) for m in fvl.MODES}
    assert names["dark"] == names["light"] == names["paper"]


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="mode"):
        fvl.roles("sepia")
    with pytest.raises(ValueError, match="mode"):
        fvl.palette("sepia")


def test_palette_order_and_anchors():
    light = fvl.palette("paper")
    dark = fvl.palette("dark")
    assert [n for n, _ in light] == [n for n, _ in dark]
    assert light[0] == ("signal", "#0172A1")
    assert light[1] == ("magma", fvl.color("magma-600"))
    assert dark[0][1] == fvl.color("signal-400")
    assert dark[1][1] == fvl.color("magma-400")
    assert fvl.palette("light") == light


@pytest.mark.parametrize(
    "mode, floor, background, min_con",
    [("paper", 14.9, "#FFFFFF", 3.0), ("dark", 10.9, "ink-950", 4.5)],
)
def test_palette_separation_and_contrast(mode, floor, background, min_con):
    hexes = [h for _, h in fvl.palette(mode)]
    assert min_delta_e(hexes) >= floor
    bg = fvl.color(background)
    assert min(fvl.contrast(h, bg) for h in hexes) >= min_con


def test_delta_e_metric_detects_red_green_confusion():
    # canary: pure red and green collapse under deuteranomaly
    assert min_delta_e(["#FF0000", "#00A000"]) < 10


def test_colormap_stops_resolve():
    cm = fvl.tokens()["colormaps"]
    for name in ("ember", "tide", "tide_dark"):
        stops = [fvl.color(s) for s in cm[name]]
        assert len(stops) >= 5
    assert cm["default"]["sequential"] == "batlow"


def test_fonts_are_bundled_with_licences():
    d = fvl.fonts_dir()
    for family in ("Geist", "GeistMono", "Inter"):
        assert list((d / "ttf").glob(f"{family}-Regular.ttf")), family
        assert list((d / "woff2").glob(f"{family}-Regular.woff2")), family
    assert (d / "OFL-Geist.txt").read_text().count("SIL Open Font License") >= 1
    assert (d / "OFL-Inter.txt").read_text().count("SIL Open Font License") >= 1
