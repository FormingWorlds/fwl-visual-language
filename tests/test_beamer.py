"""Beamer theme: generated text, install, and a talk compiled with references."""

import re
import runpy
import shutil
import subprocess
import sys

import pytest

import fwl_visual_language as fvl
from fwl_visual_language import __main__ as cli
from fwl_visual_language import beamer, latex

TEX = shutil.which("lualatex") and shutil.which("bibtex") and shutil.which("pdftotext")

BIB = r"""
@article{one, author = {Alpha, Ann}, year = {2023}, journal = {Mon. Not. R. Astron. Soc.},
  title = {A}}
@article{two, author = {Alpha, Ann and Beta, Ben}, year = {2024}, journal = {Unlisted Journal},
  title = {B}}
@article{many, author = {Gamma, Gil and Delta, Dee and Eps, Eve}, year = {2025},
  journal = {Astrophys. J. Lett.}, title = {C}}
@incollection{book, author = {Alpha, Ann and Beta, Ben}, year = {2025},
  booktitle = {Treatise on Things}, title = {D}}
@article{prefix, author = {van Eylen, Vin}, year = {2024}, journal = {Astron. Astrophys.},
  title = {E}}
@article{others, author = {Zeta, Zoe and others}, year = {2022}, journal = {\mnras}, title = {F}}
@misc{anon, title = {G}, year = {in press}, journal = {PSJ}}
@article{s1, author = {Smith, Sam}, year = {2025}, journal = {PSJ}, title = {S1}}
@article{s2, author = {Smith, Sam}, year = {2025}, journal = {PSJ}, title = {S2}}
@article{suffix, author = {Jones, Jo}, year = {2024a}, journal = {PSJ}, title = {J}}
@misc{source, title = {K}, journal = {Only Source}}
@article{aa, author = {Eta, Eli and Theta, Tom}, year = {2021},
  journal = {Astronomy \& Astrophysics}, title = {H}}
"""

TALK = r"""\documentclass[aspectratio=169]{beamer}
\usetheme{fwl}
\addbibresource{refs.bib}
\title{Talk title}\author{Speaker Name}\date{Venue, city\\Date}
\begin{document}
\titleframe
\questionframe[Sub-question]{How do \hl{rocky worlds} form?}
\sectionframe{Part 2}{A section statement}
\figureframe{A figure frame}{Side text\slideref{one}}{fig.png}
\begin{frame}{Two corners}
  Body text with $\phi \oplus x^2$.
  \slideref{two}
  \slideref{book,many}[right]
\end{frame}
\begin{frame}{More cases}\slideref{prefix,others,aa}\slideref{anon,nokey}[right]\end{frame}
\begin{frame}[plain]{A plain frame}\slideref{one}\end{frame}
\begin{frame}{After the plain frame}Text.\slideref{s1,s2,suffix,source}\end{frame}
\begin{frame}[statement]{On ink-980}\slideref{many}\end{frame}
\statementframe{A common assumption.}
\closingframe[Positions]{A closing question?}
\end{document}
"""


def test_theme_is_an_output_and_stable():
    assert cli.OUTPUTS["beamer/beamerthemefwl.sty"] is beamer.beamer_theme
    text = beamer.beamer_theme()
    assert text == beamer.beamer_theme()
    assert "\\ProvidesPackage{beamerthemefwl}[2026/10/20" in text
    from datetime import date

    assert "2027/01/02" in beamer.beamer_theme(date(2027, 1, 2))
    for frame in (
        "\\titleframe",
        "\\questionframe",
        "\\sectionframe",
        "\\statementframe",
        "\\closingframe",
        "\\figureframe",
        "\\slideref",
    ):
        assert frame in text


def test_install_writes_theme_fonts_and_logo(tmp_path):
    out = beamer.install_beamer(tmp_path / "a")
    assert out.read_text(encoding="utf-8") == beamer.beamer_theme()
    for f in (
        "fwl.sty",
        "fwl-fonts/Geist-Light.ttf",
        "fwl-fonts/Geist-LightItalic.ttf",
        "fwl-assets/fwl-logo-white.png",
    ):
        assert (tmp_path / "a" / f).is_file(), f


def test_command_line_and_module_run(tmp_path, capsys, monkeypatch):
    beamer.main([str(tmp_path / "a")])
    assert capsys.readouterr().out.strip() == str(tmp_path / "a" / beamer.THEME_NAME)
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language.beamer", str(tmp_path / "b")])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.beamer")
    runpy.run_module("fwl_visual_language.beamer", run_name="__main__")
    assert (tmp_path / "b" / beamer.THEME_NAME).is_file()


def _compile(folder):
    def run(*cmd):
        r = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, (cmd, r.stdout[-3000:])

    tex = ("lualatex", "-interaction=nonstopmode", "-halt-on-error", "talk.tex")
    run(*tex)
    run("bibtex", "talk")
    run(*tex)
    run(*tex)
    log = (folder / "talk.log").read_text(errors="replace")
    assert "Missing character" not in log
    pages = subprocess.run(
        ["pdftotext", "-layout", "talk.pdf", "-"], cwd=folder, capture_output=True, text=True
    ).stdout.split("\f")
    return log, pages


def _ground(folder, page):
    """Return the RGB colour of an empty point at the right edge of a page."""
    from PIL import Image

    subprocess.run(
        [
            "pdftoppm",
            "-r",
            "30",
            "-png",
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "talk.pdf",
            "ground",
        ],
        cwd=folder,
        check=True,
    )
    with Image.open(folder / "ground.png") as im:
        return im.convert("RGB").getpixel((im.width - 3, im.height // 3))


@pytest.mark.skipif(not (TEX and shutil.which("pdftoppm")), reason="no TeX")
def test_talk_compiles_with_references_in_both_corners(tmp_path):
    from PIL import Image

    beamer.install_beamer(tmp_path)
    Image.new("RGB", (142, 92), (255, 255, 255)).save(tmp_path / "fig.png")
    (tmp_path / "refs.bib").write_text(BIB)
    (tmp_path / "talk.tex").write_text(TALK)
    log, pages = _compile(tmp_path)
    assert len([p for p in pages if p.strip()]) == 11
    # 1 name, 2 names with "&", many names as "First+"; 2-digit year; journal names mapped
    assert "Alpha 23 MNRAS" in pages[3]
    corners = re.sub(r"\s+", " ", pages[4])
    assert "Alpha & Beta 24 Unlisted Journal" in corners
    assert "Alpha & Beta 25 Treatise on Things" in corners
    assert "Gamma+ 25 ApJL" in corners
    # the left corner and the right stack are on the same base line
    lines = [ln for ln in pages[4].splitlines() if ln.strip()]
    assert "Alpha & Beta 24" in lines[-1] and "Gamma+ 25 ApJL" in lines[-1]
    more = re.sub(r"\s+", " ", pages[5])
    assert "van Eylen 24 A&A" in more  # the prefix stays; journal mapped
    assert "Zeta+ 22 MNRAS" in more  # "and others" gives "+"; ADS macro
    assert "in press PSJ" in more and "+ in press" not in more  # no author, year kept
    assert "nokey" in more  # an unknown key shows, not silently dropped
    assert "Eta & Theta 21 A&A" in more  # a long journal name with \\& is mapped
    # a reference in a plain frame does not move to the next frame
    assert "Alpha 23" not in pages[7]
    after = [ln.strip() for ln in pages[7].splitlines() if ln.strip()]
    # one author, one year: the letter tells the papers apart; a suffixed year keeps it
    for line in ("Smith 25a PSJ", "Smith 25b PSJ", "Jones 24a PSJ", "Only Source"):
        assert line in after, (line, after)
    # ink-950 on every frame, ink-980 only on the statement frames
    ink = fvl.ramp("ink")
    ink950, ink980 = (tuple(int(ink[s][i : i + 2], 16) for i in (1, 3, 5)) for s in ("950", "980"))
    expected = [ink950] * 8 + [ink980] * 2 + [ink950]
    assert [_ground(tmp_path, n) for n in range(1, 12)] == expected


@pytest.mark.skipif(not (TEX and shutil.which("pdffonts")), reason="no TeX")
def test_talk_embeds_the_lab_fonts(tmp_path):
    from PIL import Image

    beamer.install_beamer(tmp_path)
    Image.new("RGB", (10, 10)).save(tmp_path / "fig.png")
    (tmp_path / "refs.bib").write_text(BIB)
    # fwl loaded before the theme: the theme adds the math without an option clash
    (tmp_path / "talk.tex").write_text(
        TALK.replace("\\usetheme{fwl}", "\\usepackage{fwl}\n\\usetheme{fwl}")
    )
    _compile(tmp_path)
    fonts = subprocess.run(
        ["pdffonts", "talk.pdf"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    names = {line.split()[0].split("+")[-1] for line in fonts.splitlines()[2:]}
    assert {"Geist-Light", "Geist-Regular", "GeistMono-Regular"} <= names
    # math (the formula and the list bullet) in Inter and STIX Two, as in the proposal style
    assert {"Inter-Regular", "Inter-Italic", "STIXTwoMath-Regular"} <= names
    assert not {n for n in names if not n.startswith(("Geist", "Inter", "STIXTwoMath"))}


def test_theme_file_names_match_the_latex_install():
    assert beamer.ASSET_DIR == "fwl-assets"
    assert "\\providecommand{\\fwlassetpath}{fwl-assets/}" in beamer.beamer_theme()
    assert latex.FONT_DIR == "fwl-fonts"
