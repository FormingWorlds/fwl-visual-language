"""Jupyter Book theme: variable names, contrast, structure and installation."""

import re
import runpy
import sys
from pathlib import Path

import pytest

import fwl_visual_language as fvl
from fwl_visual_language import jupyterbook as jb

# Every --pst-color-* and --pst-font-family-* name in pydata-sphinx-theme 0.16.1.
PST_NAMES = set(Path(__file__).with_name("pst_0_16_names.txt").read_text().split())
MODES = ("light", "dark")


def _block(css, selector):
    return css.split(f"{selector} {{\n", 1)[1].split("}\n", 1)[0]


def test_every_variable_set_exists_in_pydata_sphinx_theme():
    css = jb.jupyterbook_css()
    names = set(re.findall(r"(--pst-[a-z-]+):", css))
    assert names and names <= PST_NAMES, sorted(names - PST_NAMES)


def test_canary_name_list_rejects_a_made_up_variable():
    assert "--pst-color-made-up" not in PST_NAMES
    assert "--pst-color-primary" in PST_NAMES


@pytest.mark.parametrize("mode", MODES)
def test_text_colours_read_on_every_surface(mode):
    v = jb._variables(mode)
    surfaces = [
        v["--pst-color-background"],
        v["--pst-color-on-background"],
        v["--pst-color-surface"],
    ]
    text = [
        "--pst-color-text-base",
        "--pst-color-text-muted",
        "--pst-color-heading",
        "--pst-color-link",
        "--pst-color-link-hover",
        "--pst-color-inline-code",
        "--pst-color-accent",
    ]
    for name in text:
        for s in surfaces:
            assert fvl.contrast(v[name], s) >= 4.5, (mode, name, s)
    for kind in jb._KINDS:
        assert fvl.contrast(v[f"--pst-color-{kind}"], v[f"--pst-color-{kind}-bg"]) >= 4.5


@pytest.mark.parametrize("mode", MODES)
def test_both_modes_set_the_same_variables_and_follow_the_roles(mode):
    css = jb.jupyterbook_css()
    light = set(re.findall(r"(--pst-[a-z-]+):", _block(css, "html[data-theme=light]")))
    dark = set(re.findall(r"(--pst-[a-z-]+):", _block(css, "html[data-theme=dark]")))
    assert light == dark
    v = jb._variables(mode)
    assert v["--pst-color-background"] == fvl.role(mode, "background")
    assert v["--pst-color-link"] == fvl.role(mode, "link")


def test_fonts_and_greek_range():
    css = jb.jupyterbook_css()
    root = _block(css, ":root")
    assert f"--pst-font-family-base: {jb.SANS};" in root
    assert f"--pst-font-family-monospace: {jb.MONO};" in root
    faces = re.findall(r"@font-face \{([^}]*)\}", css)
    assert len(faces) == len(jb._FONT_FACES)
    inter = [f for f in faces if '"Inter"' in f]
    assert inter and all("unicode-range: U+0370-03FF, U+1F00-1FFF;" in f for f in inter)


def test_header_names_versions():
    head = jb.jupyterbook_css().splitlines()[0]
    assert f"fwl-visual-language {fvl.__version__}" in head
    assert "pydata-sphinx-theme 0.16" in head


def test_install_writes_stylesheet_fonts_and_licences(tmp_path):
    out = jb.install_jupyterbook_theme(tmp_path / "_static")
    assert out == tmp_path / "_static" / jb.CSS_NAME
    assert out.read_text(encoding="utf-8") == jb.jupyterbook_css()
    fonts = tmp_path / "_static" / jb.FONT_DIR
    for _, file, _, _, _ in jb._FONT_FACES:
        assert (fonts / file).read_bytes() == (fvl.fonts_dir() / "woff2" / file).read_bytes()
    for lic in jb._LICENCES:
        assert (fonts / lic).is_file()


def test_install_into_a_file_path_raises(tmp_path):
    target = tmp_path / "_static"
    target.write_text("not a folder")
    with pytest.raises(OSError):
        jb.install_jupyterbook_theme(target)


def test_command_line_and_module_run(tmp_path, capsys, monkeypatch):
    jb.main([str(tmp_path / "a")])
    assert capsys.readouterr().out.strip() == str(tmp_path / "a" / jb.CSS_NAME)
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language.jupyterbook", str(tmp_path / "b")])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.jupyterbook")
    runpy.run_module("fwl_visual_language.jupyterbook", run_name="__main__")
    assert (tmp_path / "b" / jb.CSS_NAME).is_file()
