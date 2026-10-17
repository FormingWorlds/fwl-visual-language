"""Tests for the web stylesheets and the matplotlib style sheets."""

import re

import matplotlib as mpl
import pytest
from matplotlib import font_manager

import fwl_visual_language as fvl
from fwl_visual_language import css
from fwl_visual_language import mpl as fmpl


def _block(text, opener):
    start = text.index(opener) + len(opener)
    return text[start : text.index("}", start)]


def _vars(block):
    return dict(re.findall(r"(--fwl-[a-z0-9-]+):\s*([^;]+);", block))


def test_tokens_css_dark_root_and_both_light_overrides():
    text = css.tokens_css()
    root = _vars(_block(text, ":root {"))
    media = _vars(_block(text, ':root:not([data-theme="dark"]) {'))
    explicit = _vars(_block(text, ':root[data-theme="light"] {'))
    assert root["--fwl-background"] == fvl.role("dark", "background")
    assert media == explicit
    assert media["--fwl-background"] == fvl.role("light", "background")
    # every themed variable is defined on :root before an override changes it
    assert set(media) <= set(root)
    assert "@media (prefers-color-scheme: light)" in text


def test_tokens_css_lists_every_ramp_step_and_figure_colour():
    root = _vars(_block(css.tokens_css(), ":root {"))
    for name in ("ink", "signal", "magma"):
        for step, hexv in fvl.ramp(name).items():
            assert root[f"--fwl-{name}-{step}"] == hexv
    for i, (_, hexv) in enumerate(fvl.palette("dark"), start=1):
        assert root[f"--fwl-figure-{i}"].startswith(hexv)
    assert root["--fwl-font-text"].startswith('"Geist", "Inter"')
    assert root["--fwl-font-mono"].startswith('"Geist Mono"')


def test_tailwind_theme_has_every_step_once_in_website_form():
    text = css.tailwind_theme_css()
    entries = re.findall(r"--color-([a-z]+)-(\d+): ([^;]+);", text)
    n_steps = sum(len(r["steps"]) for r in fvl.tokens()["ramps"].values())
    assert len(entries) == n_steps == len({(a, b) for a, b, _ in entries})
    assert "--color-ink-950: oklch(0.090 0.012 240);" in text
    assert "--color-signal-500: #0072A1;" in text
    assert text.count("@theme {") == 1


def test_web_fonts_css_names_only_bundled_files():
    text = css.web_fonts_css("assets/fonts")
    files = re.findall(r'url\("assets/fonts/([^"]+)"\)', text)
    assert len(files) == len(css._WEB_FACES)
    assert all((fvl.fonts_dir() / "woff2" / f).is_file() for f in files)


def test_web_fonts_css_reports_a_missing_file(monkeypatch):
    monkeypatch.setattr(css, "_WEB_FACES", (("Geist", "Missing.woff2", "normal", 400, None),))
    with pytest.raises(FileNotFoundError, match="Missing.woff2"):
        css.web_fonts_css()


@pytest.fixture(scope="module", autouse=True)
def _fonts():
    for f in (fvl.fonts_dir() / "ttf").glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))


def _load(mode, tmp_path):
    p = tmp_path / f"fwl-{mode}.mplstyle"
    p.write_text(fmpl.mplstyle(mode))
    return mpl.rc_params_from_file(str(p), use_default_template=False)


@pytest.mark.parametrize("mode", fmpl.MPL_MODES)
def test_mplstyle_parses_with_token_colours(mode, tmp_path):
    rc = _load(mode, tmp_path)
    r = fvl.roles(mode)
    assert mpl.colors.to_hex(rc["figure.facecolor"]).upper() == r["background"]
    assert mpl.colors.to_hex(rc["axes.edgecolor"]).upper() == r["axis"]
    assert mpl.colors.to_hex(rc["text.color"]).upper() == r["heading"]
    cycle = [mpl.colors.to_hex(c).upper() for c in rc["axes.prop_cycle"].by_key()["color"]]
    assert cycle == [h for _, h in fvl.palette(mode)]
    assert rc["font.family"][:2] == ["Geist", "Inter"]
    assert rc["mathtext.it"] == "Inter:italic"


@pytest.mark.parametrize("family", ["Geist", "Inter", "Geist Mono"])
def test_style_fonts_resolve_to_bundled_files(family):
    path = font_manager.findfont(family, fallback_to_default=False)
    assert str(fvl.fonts_dir()) in path


def test_mplstyle_rejects_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        fmpl.mplstyle("light")


def test_font_stack_quotes_names_and_drops_duplicates():
    assert css._font_stack("Inter", ["Inter", "system-ui", "-apple-system", "Segoe UI"]) == (
        '"Inter", system-ui, -apple-system, "Segoe UI"'
    )
