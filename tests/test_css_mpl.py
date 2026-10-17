"""Tests for the web stylesheets and the matplotlib style sheets."""

import logging
import re
import runpy
import sys
import warnings

import matplotlib as mpl
import pytest
from matplotlib import font_manager

import fwl_visual_language as fvl
from fwl_visual_language import _web, css
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
    text = css.web_fonts_css()
    files = re.findall(r'url\("fwl-fonts/([^"]+)"\)', text)
    assert len(files) == len(_web.FACES)
    assert all((fvl.fonts_dir() / "woff2" / f).is_file() for f in files)


def test_install_web_fonts_writes_css_fonts_and_licences(tmp_path, capsys):
    out = css.install_web_fonts(tmp_path / "static")
    assert out.read_text(encoding="utf-8") == css.web_fonts_css()
    for _, file, _, _ in _web.FACES:
        assert (tmp_path / "static" / _web.FONT_DIR / file).is_file()
    for lic in _web.LICENCES:
        assert (tmp_path / "static" / _web.FONT_DIR / lic).is_file()
    css.main([str(tmp_path / "cli")])
    assert capsys.readouterr().out.strip() == str(tmp_path / "cli" / css.FONTS_CSS_NAME)


def test_css_module_runs_as_a_script(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language.css", str(tmp_path)])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.css")
    runpy.run_module("fwl_visual_language.css", run_name="__main__")
    assert (tmp_path / css.FONTS_CSS_NAME).is_file()


def test_font_stacks_follow_the_token_roles(monkeypatch):
    fonts = dict(fvl.tokens()["fonts"], text="Other Sans", mono="Other Mono")
    monkeypatch.setitem(fvl.tokens(), "fonts", fonts)
    assert _web.font_stack("text").startswith('"Other Sans", "Inter"')
    assert _web.font_stack("mono").startswith('"Other Mono"')
    faces = _web.font_faces_css()
    assert '"Other Sans"' in faces and '"Geist"' not in faces


@pytest.fixture(scope="module", autouse=True)
def _fonts():
    for f in (fvl.fonts_dir() / "ttf").glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))


def _load(mode, tmp_path):
    p = tmp_path / f"fwl-{mode}.mplstyle"
    p.write_text(fmpl.mplstyle(mode))
    # fail_on_error raises on a bad value; a bad key is only logged, so collect the log too
    records = []
    handler = logging.Handler(logging.WARNING)
    handler.emit = records.append
    log = logging.getLogger("matplotlib")
    log.addHandler(handler)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            rc = mpl.rc_params_from_file(str(p), fail_on_error=True, use_default_template=False)
    finally:
        log.removeHandler(handler)
    assert not records, [r.getMessage() for r in records]
    return rc


@pytest.mark.parametrize("mode", fmpl.MPL_MODES)
def test_mplstyle_parses_with_token_colours(mode, tmp_path):
    rc = _load(mode, tmp_path)
    r = fvl.roles(mode)
    assert mpl.colors.to_hex(rc["figure.facecolor"]).upper() == r["background"]
    assert mpl.colors.to_hex(rc["axes.edgecolor"]).upper() == r["axis"]
    assert mpl.colors.to_hex(rc["text.color"]).upper() == r["heading"]
    colour_keys = {
        "figure.facecolor": "background",
        "savefig.facecolor": "background",
        "axes.facecolor": "background",
        "axes.edgecolor": "axis",
        "xtick.color": "axis",
        "ytick.color": "axis",
        "axes.labelcolor": "heading",
        "text.color": "heading",
        "xtick.labelcolor": "heading",
        "ytick.labelcolor": "heading",
        "legend.labelcolor": "heading",
        "grid.color": "line",
    }
    for key, role in colour_keys.items():
        assert mpl.colors.to_hex(rc[key]).upper() == r[role], key
    cycle = [mpl.colors.to_hex(c).upper() for c in rc["axes.prop_cycle"].by_key()["color"]]
    assert cycle == [h for _, h in fvl.palette(mode)]
    assert rc["font.family"][:2] == ["Geist", "Inter"]
    assert rc["mathtext.it"] == "Inter:italic"


@pytest.mark.parametrize("family", ["Geist", "Inter", "Geist Mono"])
def test_style_fonts_resolve_to_bundled_files(family):
    path = font_manager.findfont(family, fallback_to_default=False)
    assert str(fvl.fonts_dir()) in path


def test_style_loader_catches_a_misspelled_key(tmp_path, monkeypatch):
    bad = fmpl.mplstyle("paper").replace("axes.titlelocation", "axes.titlelocatoin")
    monkeypatch.setattr(fmpl, "mplstyle", lambda mode: bad)
    with pytest.raises(AssertionError, match="titlelocatoin"):
        _load("paper", tmp_path)


def test_mplstyle_rejects_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        fmpl.mplstyle("light")


def test_font_stack_quotes_names_and_drops_duplicates():
    assert _web.font_stack("math").startswith('"Inter", system-ui, -apple-system, ')
    assert _web.font_stack("math").count('"Inter"') == 1
    assert _web.font_stack("mono", extra=("JuliaMono",)).startswith('"Geist Mono", "JuliaMono"')


def test_style_colour_map_resolves_once_cmcrameri_is_imported(tmp_path):
    import cmcrameri  # noqa: F401

    rc = _load("paper", tmp_path)
    assert mpl.colormaps[rc["image.cmap"]].name == rc["image.cmap"] == "cmc.batlow"
