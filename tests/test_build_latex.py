"""Build command, committed themes folder, and the LaTeX package."""

import re
import runpy
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

import fwl_visual_language as fvl
from fwl_visual_language import __main__ as cli
from fwl_visual_language import latex

THEMES = Path(__file__).resolve().parents[1] / "themes"


def test_committed_themes_are_current():
    assert cli.check(THEMES) == [], "run: python -m fwl_visual_language build"


@pytest.mark.parametrize("rel", [r for r in cli.OUTPUTS if r.endswith(".css")])
def test_css_outputs_have_balanced_braces(rel):
    # a stray brace makes a browser drop the next rule; regex parsers skip it
    text = re.sub(r"/\*.*?\*/", "", cli.OUTPUTS[rel](), flags=re.S)
    depth = 0
    for ch in text:
        depth += {"{": 1, "}": -1}.get(ch, 0)
        assert depth >= 0, rel
    assert depth == 0, rel


def test_check_ignores_dotfiles_and_caches_but_not_under_a_hidden_parent(tmp_path):
    root = tmp_path / ".hidden" / "themes"
    cli.build(root)
    (root / ".DS_Store").write_text("finder")
    (root / "css" / "__pycache__").mkdir()
    (root / "css" / "__pycache__" / "x.pyc").write_text("cache")
    (root / "css" / "._fwl-tokens.css").write_text("apple double")
    assert cli.check(root) == []
    # real extra files are reported: below a hidden parent, with a __ or . prefix
    (root / "css" / "old-name.css").write_text("left behind")
    (root / "css" / "__old.css").write_text("left behind")
    (root / ".old").mkdir()
    (root / ".old" / "fwl.css").write_text("left behind")
    assert cli.check(root) == [".old/fwl.css", "css/__old.css", "css/old-name.css"]


def test_main_defaults_to_the_themes_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["build"]) == 0
    assert (tmp_path / "themes" / "css" / "fwl-tokens.css").is_file()
    assert cli.main(["check"]) == 0


def test_build_then_check_round_trip(tmp_path):
    written = cli.build(tmp_path)
    assert [p.relative_to(tmp_path).as_posix() for p in written] == list(cli.OUTPUTS)
    assert cli.check(tmp_path) == []


def test_check_reports_a_hand_edit_and_a_missing_file(tmp_path):
    cli.build(tmp_path)
    target = tmp_path / "css" / "fwl-tokens.css"
    target.write_text(target.read_text() + "/* edit */\n")
    (tmp_path / "latex" / "fwl.sty").unlink()
    (tmp_path / "css" / "old-name.css").write_text("left behind")
    (tmp_path / "mpl" / "fwl-dark.mplstyle").write_bytes(b"\xff\xfe not utf-8")
    assert cli.check(tmp_path) == [
        "css/fwl-tokens.css",
        "mpl/fwl-dark.mplstyle",
        "latex/fwl.sty",
        "css/old-name.css",
    ]


def test_main_build_and_check_exit_codes(tmp_path, capsys):
    assert cli.main(["build", str(tmp_path)]) == 0
    assert str(tmp_path / "latex" / "fwl.sty") in capsys.readouterr().out
    assert cli.main(["check", str(tmp_path)]) == 0
    (tmp_path / "mpl" / "fwl-dark.mplstyle").write_text("")
    assert cli.main(["check", str(tmp_path)]) == 1
    assert "stale: mpl/fwl-dark.mplstyle" in capsys.readouterr().err


def test_module_entry_point_exits_with_check_status(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language", "check", str(tmp_path)])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.__main__")
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("fwl_visual_language", run_name="__main__")
    assert exc.value.code == 1


def test_latex_name_forms():
    assert latex.latex_name("ink", "950") == "fwlInk950"
    assert latex.latex_name("link-hover") == "fwlLinkHover"
    assert latex.latex_name("warm-text") == "fwlWarmText"


def test_sty_defines_every_colour_once():
    text = latex.sty()
    names = re.findall(r"\\definecolor\{(fwl[A-Za-z0-9]+)\}\{HTML\}\{([0-9A-F]{6})\}", text)
    n_ramp = sum(len(r["steps"]) for r in fvl.tokens()["ramps"].values())
    n_roles = len(fvl.roles("paper"))
    assert len(names) == n_ramp + n_roles + len(fvl.palette("paper"))
    assert len({n for n, _ in names}) == len(names)
    assert ("fwlSignal500", "0072A1") in names
    assert ("fwlLink", fvl.role("paper", "link")[1:]) in names


def test_sty_release_date_is_stable_unless_given():
    from datetime import date

    assert latex.sty() == latex.sty()
    assert "2027/01/02" in latex.sty(date(2027, 1, 2))


def test_install_latex_copies_fonts_and_licence(tmp_path):
    out = latex.install_latex(tmp_path / "doc")
    assert out.read_text(encoding="utf-8") == latex.sty()
    for f in latex._TTF:
        assert (tmp_path / "doc" / latex.FONT_DIR / f).is_file()
    assert (tmp_path / "doc" / latex.FONT_DIR / "OFL-Geist.txt").is_file()


def test_install_latex_into_a_file_path_raises(tmp_path):
    target = tmp_path / "doc"
    target.write_text("not a folder")
    with pytest.raises(OSError):
        latex.install_latex(target)


def test_latex_command_line_and_module_run(tmp_path, capsys, monkeypatch):
    latex.main([str(tmp_path / "a")])
    assert capsys.readouterr().out.strip() == str(tmp_path / "a" / "fwl.sty")
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language.latex", str(tmp_path / "b")])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.latex")
    runpy.run_module("fwl_visual_language.latex", run_name="__main__")
    assert (tmp_path / "b" / "fwl.sty").is_file()


@pytest.mark.skipif(not (shutil.which("lualatex") and shutil.which("pdffonts")), reason="no TeX")
def test_document_compiles_and_embeds_only_geist(tmp_path):
    latex.install_latex(tmp_path)
    (tmp_path / "doc.tex").write_text(
        "\\documentclass{article}\\usepackage{fwl}\\begin{document}"
        "Text \\textit{italic} {\\fwlmedium medium {\\itshape italic}} \\textbf{bold} "
        "\\textbf{\\textit{bold italic}} \\textsf{\\fwlmedium sans} \\texttt{mono "
        "{\\fwlmedium medium}} \\textcolor{fwlLink}{link}\\end{document}\n"
    )
    run = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, run.stdout[-2000:]
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert "Missing character" not in log
    assert "LaTeX Font Warning" not in log, re.findall(r"LaTeX Font Warning.*", log)
    fonts = subprocess.run(
        ["pdffonts", "doc.pdf"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    names = [line.split()[0].split("+")[-1] for line in fonts.splitlines()[2:]]
    assert set(names) == {
        "Geist-Regular",
        "Geist-Italic",
        "Geist-Medium",
        "Geist-MediumItalic",
        "Geist-SemiBold",
        "Geist-SemiBoldItalic",
        "GeistMono-Regular",
        "GeistMono-Medium",
    }


def test_proposal_style_is_an_output_and_loads_the_math_option():
    assert cli.OUTPUTS["latex/fwlproposal.sty"] is latex.proposal_sty
    text = latex.proposal_sty()
    assert text == latex.proposal_sty()
    assert "\\ProvidesPackage{fwlproposal}" in text
    assert "\\RequirePackage[math]{fwl}" in text
    assert "2027/01/02" in latex.proposal_sty(date(2027, 1, 2))


def test_math_option_is_off_unless_asked():
    text = latex.sty()
    assert "\\DeclareOption{math}{\\fwl@mathtrue}" in text
    assert text.index("\\iffwl@math") < text.index("\\RequirePackage{unicode-math}")


def test_install_latex_copies_the_math_fonts_and_proposal_style(tmp_path):
    latex.install_latex(tmp_path)
    fonts = tmp_path / latex.FONT_DIR
    for f in (
        "Inter-Regular.ttf",
        "Inter-Italic.ttf",
        latex.MATH_FONT,
        "OFL-Inter.txt",
        "OFL-STIX.txt",
    ):
        assert (fonts / f).is_file(), f
    assert (tmp_path / latex.PROPOSAL_NAME).read_text(encoding="utf-8") == latex.proposal_sty()


def _lualatex(folder, name):
    run = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
        cwd=folder,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, run.stdout[-2000:]
    log = (folder / f"{name}.log").read_text(errors="replace")
    assert "Missing character" not in log
    fonts = subprocess.run(
        ["pdffonts", f"{name}.pdf"], cwd=folder, capture_output=True, text=True
    ).stdout
    return {line.split()[0].split("+")[-1] for line in fonts.splitlines()[2:]}


@pytest.mark.skipif(not (shutil.which("lualatex") and shutil.which("pdffonts")), reason="no TeX")
def test_proposal_compiles_with_inter_and_stix_math(tmp_path):
    latex.install_latex(tmp_path)
    # fwl loaded first, as a letter would do: the proposal style adds the math to it
    (tmp_path / "p.tex").write_text(
        "\\documentclass[11pt]{article}\\usepackage{fwl}\\usepackage{fwlproposal}"
        "\\usepackage{amsmath}\\renewcommand{\\fwlfooter}{Lab footer}\\title{T}\\author{A}"
        "\\begin{document}\\maketitle\\fwltitle{Title line}{Subtitle line}"
        "\\section{Section}\\subsection{Sub}\\subsubsection{Subsub}\\paragraph{Run-in} "
        "Text $\\phi \\approx 0.4$, $\\Delta\\log f\\mathrm{O_2}$, $1\\,M_\\oplus$, "
        "$\\symbf{x}\\,\\symbf{\\alpha}\\,\\symbfit{\\beta}$ and "
        "\\[ \\frac{\\partial S}{\\partial t} = \\sum_i \\alpha_i \\int_0^R \\Phi(r)\\,dr \\]"
        "\\begin{figure}[h]\\caption{Caption.}\\end{figure}\\end{document}\n"
    )
    names = _lualatex(tmp_path, "p")
    assert {
        "Inter-Regular",
        "Inter-Italic",
        "Inter-Medium",
        "Inter-MediumItalic",
        "STIXTwoMath-Regular",
        "Geist-Regular",
        "Geist-Medium",
        "GeistMono-Regular",
    } <= names
    assert not {n for n in names if not n.startswith(("Geist", "Inter", "STIXTwoMath"))}
    text = subprocess.run(
        ["pdftotext", "-layout", "p.pdf", "-"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    for expected in (
        "Title line",
        "Subtitle line",
        "1 Section",
        "1.1 Sub",
        "1.1.1 Subsub",
        "Run-in.",
        "Figure 1. Caption.",
    ):
        assert expected in text, expected
    # the footer is on every page, also on the \\maketitle page in the plain style
    pages = [p for p in text.split("\f") if p.strip()]
    assert all("Lab footer" in p for p in pages), len(pages)
