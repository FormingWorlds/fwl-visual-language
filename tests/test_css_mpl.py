"""Tests for the web stylesheets and the matplotlib style sheets."""

import copy
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


def _colour_vars(block):
    return dict(re.findall(r"(--color-[a-z]+-\d+):\s*([^;]+);", block))


def _hex(css_value):
    m = re.fullmatch(r"oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)", css_value)
    return fvl.oklch_to_hex(*map(float, m.groups())) if m else css_value


def _lightness(css_value):
    m = re.fullmatch(r"oklch\(([\d.]+) [\d.]+ [\d.]+\)", css_value)
    if m:
        return float(m.group(1))
    lin = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in fvl.hex_to_rgb(css_value)
    ]
    lms = [
        sum(w * c for w, c in zip(row, lin, strict=True)) ** (1 / 3)
        for row in (
            (0.4122214708, 0.5363325363, 0.0514459929),
            (0.2119034982, 0.6806995451, 0.1073969566),
            (0.0883024619, 0.2817188376, 0.6299787005),
        )
    ]
    return 0.2104542553 * lms[0] + 0.7936177850 * lms[1] - 0.0040720468 * lms[2]


def test_lightness_helper_reads_both_forms():
    assert _lightness("oklch(0.485 0.135 37)") == 0.485
    assert abs(_lightness("#0072A1") - 0.522) < 2e-3
    assert abs(_lightness("#FFFFFF") - 1.0) < 1e-6


def test_tailwind_light_overrides_every_theme_variable_and_on_dark_restores_it():
    text = css.tailwind_light_css()
    theme = _colour_vars(css.tailwind_theme_css())
    media = _colour_vars(_block(text, ':root:not([data-theme="dark"]) {'))
    explicit = _colour_vars(_block(text, ':root[data-theme="light"] {'))
    on_dark = _colour_vars(_block(text, ".on-dark {"))
    assert media == explicit
    n_steps = sum(len(r["steps"]) for r in fvl.tokens()["ramps"].values())
    assert set(media) == set(theme) and len(theme) == n_steps
    assert on_dark == theme
    assert "color-scheme: dark;" in _block(text, ".on-dark {")
    assert text.count("color-scheme: light;") == 2
    assert ":root {\n  color-scheme: dark;\n}" in text
    assert "@media (prefers-color-scheme: light) {" in text


def test_tailwind_light_values_follow_the_token_table():
    light = _colour_vars(_block(css.tailwind_light_css(), ':root[data-theme="light"] {'))
    assert light["--color-ink-0"] == "oklch(0.055 0.010 240)"  # a ramp reference
    assert light["--color-ink-900"] == "#FFFFFF"  # a reference to a hex step
    assert light["--color-ink-850"] == "oklch(0.940 0.007 240)"  # L, C with the ramp hue
    assert light["--color-magma-400"] == "oklch(0.485 0.135 37)"  # L, C, h
    assert light["--color-signal-300"] == "#005B87"


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_website_hover_steps_differ_and_white_text_reads_on_filled_buttons(mode):
    text = css.tailwind_light_css()
    opener = ':root[data-theme="light"] {' if mode == "light" else ".on-dark {"
    raw = {k.removeprefix("--color-"): x for k, x in _colour_vars(_block(text, opener)).items()}
    v = {k: _hex(x) for k, x in raw.items()}
    # base and hover step of the dropdown, the filled buttons and the warm ghost text
    pairs = [("ink-900", "ink-850"), ("signal-500", "signal-600"), ("magma-600", "magma-700")]
    for base, hover in [*pairs, ("magma-400", "magma-300")]:
        # a visible step: 0.03 in OKLCH lightness (the dark dropdown hover is 0.035)
        assert abs(_lightness(raw[base]) - _lightness(raw[hover])) >= 0.03, (mode, base, hover)
    for fill in ("signal-500", "signal-600", "magma-600", "magma-700"):
        assert fvl.contrast("#FFFFFF", v[fill]) >= 4.5, (mode, fill)


def test_tailwind_light_takes_a_literal_hex_in_upper_case(monkeypatch):
    table = copy.deepcopy(fvl.tokens()["website_light"])
    table["ink"]["980"] = "#fafbfc"
    monkeypatch.setitem(fvl.tokens(), "website_light", table)
    light = _colour_vars(_block(css.tailwind_light_css(), ':root[data-theme="light"] {'))
    assert light["--color-ink-980"] == "#FAFBFC"


def _drop(table, ramp_name, step):
    del table[ramp_name][step]


@pytest.mark.parametrize(
    ("edit", "error", "match"),
    [
        (lambda t: _drop(t, "ink", "850"), KeyError, r"website_light\.ink: missing \['850'\]"),
        (lambda t: t["ink"].update({"990": "ink-0"}), KeyError, r"unknown \['990'\]"),
        (lambda t: t.pop("magma"), KeyError, "website_light ramps"),
        (lambda t: t.update({"signl": {}}), KeyError, "website_light ramps"),
        (lambda t: t["magma"].update({"500": "magma-999"}), KeyError, r"magma\.500: .*999"),
        (lambda t: t["signal"].update({"300": "#12"}), ValueError, r"signal\.300: .*#12"),
        (lambda t: t["magma"].update({"400": [0.5, 0.1]}), ValueError, r"magma\.400: expected"),
        (lambda t: t["ink"].update({"850": [0.94]}), ValueError, "expected"),
        (lambda t: t["ink"].update({"850": [0.94, 0.007, 240, 1]}), ValueError, "expected"),
        (lambda t: t["ink"].update({"850": [0.94, "0.007"]}), ValueError, "expected"),
        (lambda t: t["ink"].update({"850": [True, 0.007]}), ValueError, "expected"),
        (lambda t: t["ink"].update({"850": [float("nan"), 0.007]}), ValueError, "expected"),
        (lambda t: t["ink"].update({"850": [1.4, 0.007]}), ValueError, r"L must lie in \[0, 1\]"),
        (lambda t: t["ink"].update({"850": [0.9, -0.01]}), ValueError, "C in"),
        (lambda t: t["ink"].update({"850": None}), ValueError, "expected a ramp step"),
    ],
)
def test_tailwind_light_rejects_a_bad_token_table(monkeypatch, edit, error, match):
    table = copy.deepcopy(fvl.tokens()["website_light"])
    edit(table)
    monkeypatch.setitem(fvl.tokens(), "website_light", table)
    with pytest.raises(error, match=match):
        css.tailwind_light_css()


def test_website_light_departs_from_the_light_roles_only_where_listed():
    # the website keeps its own steps for these roles; any other difference is a drift
    t = fvl.tokens()
    differ = set()
    for role, dark_ref in t["roles"]["dark"].items():
        name, _, step = dark_ref.partition("-")
        if t["website_light"][name][step] != t["roles"]["light"][role]:
            differ.add(role)
    assert differ == {"heading", "line", "axis", "note", "warning"}


def test_web_fonts_css_loads_full_inter_for_the_math_role():
    text = css.web_fonts_css("static/fonts")
    assert "unicode-range" not in text
    assert text.count('url("static/fonts/') == len(_web.FACES)
    assert text.count('font-family: "Inter"') == 4


def test_tokens_css_names_inter_for_the_math_role():
    assert '--fwl-font-math: "Inter"' in css.tokens_css()


@pytest.mark.parametrize("bad", ["", "fonts/", 'a"b', "a)b"])
def test_font_dir_must_be_a_plain_relative_path(bad):
    with pytest.raises(ValueError, match="font_dir"):
        css.web_fonts_css(bad)


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
        # a deprecated key warns through warnings; matplotlib 3.7 also emits pyparsing
        # deprecations, so only matplotlib's own category is turned into an error
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=mpl.MatplotlibDeprecationWarning)
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
    # BlinkMacSystemFont and generic families must stay unquoted to keep their meaning
    assert _web.font_stack("text") == (
        '"Geist", "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    )
    assert _web.font_stack("math") == (
        '"Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    )
    assert _web.font_stack("mono", extra=("JuliaMono",)) == (
        '"Geist Mono", "JuliaMono", ui-monospace, "SFMono-Regular", "Menlo", monospace'
    )


def test_style_colour_map_resolves_once_cmcrameri_is_imported(tmp_path):
    import cmcrameri.cm as cmc
    import numpy as np

    rc = _load("paper", tmp_path)
    assert rc["image.cmap"] == "cmc.batlow"
    # compare colours, not names: cmcrameri 1.7 names the registered map "batlow"
    x = np.linspace(0, 1, 16)
    np.testing.assert_array_equal(mpl.colormaps[rc["image.cmap"]](x), cmc.batlow(x))
