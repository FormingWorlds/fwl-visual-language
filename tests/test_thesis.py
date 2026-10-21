"""Thesis class ``fwlthesis.cls``, its example thesis and the Overleaf archive."""

import filecmp
import importlib.util
import re
import runpy
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from fwl_visual_language import assets_dir, thesis

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
EXAMPLE = Path(thesis.__file__).resolve().parent / "thesis_example"
TEX = all(shutil.which(t) for t in ("lualatex", "bibtex", "pdffonts", "pdftotext", "pdfinfo"))
GUIDE = ("Using this template", "Write it last", "Required. Give the GitHub repository")
SECTIONS = [
    "Abstract",
    "Samenvatting",
    "Contents",
    "1 Introduction",
    "2 Methods",
    "3 Results",
    "4 Discussion",
    "5 Conclusions",
    "Data and code availability",
    "Acknowledgments",
    "References",
]


def test_the_class_text_has_the_options_guidance_and_journal_macros():
    text = thesis.thesis_cls()
    assert text.startswith("% Forming Worlds Lab thesis class")
    assert "\\ProvidesClass{fwlthesis}[2026/10/21" in text
    assert "\\RequirePackage[math]{fwl}[2026/10/20]" in text
    assert "\\DeclareOption{final}{\\fwl@finaltrue}" in text
    assert "\\LoadClass[11pt,a4paper,oneside]{article}" in text
    assert "\\bibliographystyle{aasjournal}" in text and "authoryear" in text
    assert "\\renewcommand{\\section}{\\clearpage\\@ifstar" in text
    assert "\\newcommand{\\figuredata}[1]{ Data and script: \\url{#1}.}" in text
    assert "\\providecommand{\\apj}{ApJ}" in text and "\\providecommand{\\mnras}{MNRAS}" in text
    assert "rug-banner-ink.png" in text and "fwl-logo-ink.png" in text
    assert text.endswith("\\endinput\n") and text.count("\\endinput") == 1
    assert "2027/01/01" in thesis.thesis_cls(release=__import__("datetime").date(2027, 1, 1))


def test_install_writes_the_class_fonts_and_logos_without_the_example(tmp_path):
    out = thesis.install_thesis(tmp_path / "t")
    assert out == tmp_path / "t" / "fwlthesis.cls"
    assert out.read_text(encoding="utf-8") == thesis.thesis_cls()
    for rel in ("fwl.sty", "fwl-fonts/Geist-Light.ttf", "fwl-fonts/Geist-LightItalic.ttf"):
        assert (tmp_path / "t" / rel).is_file(), rel
    for logo in ("fwl-logo-ink.png", "rug-banner-ink.png"):
        assert (tmp_path / "t" / "fwl-assets" / logo).read_bytes() == (
            assets_dir() / logo
        ).read_bytes()
    assert not (tmp_path / "t" / "main.tex").exists()


def test_install_with_the_example_copies_every_example_file(tmp_path):
    thesis.install_thesis(tmp_path / "t", example=True)
    files = sorted(
        p.relative_to(EXAMPLE).as_posix()
        for p in EXAMPLE.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    assert files == [
        "data/cooling.csv",
        "figures/cooling.pdf",
        "latexmkrc",
        "main.tex",
        "references.bib",
        "scripts/plot_cooling.py",
    ]
    for rel in files:
        assert filecmp.cmp(EXAMPLE / rel, tmp_path / "t" / rel, shallow=False), rel


def test_install_refuses_to_overwrite_a_thesis(tmp_path):
    dest = tmp_path / "t"
    dest.mkdir()
    (dest / "main.tex").write_text("my thesis")
    with pytest.raises(FileExistsError, match="main.tex exists"):
        thesis.install_thesis(dest, example=True)
    assert [p.name for p in dest.iterdir()] == ["main.tex"]
    assert (dest / "main.tex").read_text() == "my thesis"


def test_the_ink_banner_is_the_university_banner_in_ink():
    import numpy as np
    from PIL import Image

    red = np.asarray(Image.open(assets_dir() / "rug-banner.png").convert("RGB")).astype(int)
    ink = np.asarray(Image.open(assets_dir() / "rug-banner-ink.png"))
    assert ink.shape == (*red.shape[:2], 4)
    full = 255 - 29  # the university red (232, 29, 40) becomes full ink
    want = np.minimum(255, np.round((255 - red[..., 1:].min(axis=2)) * 255 / full))
    assert np.array_equal(ink[..., 3], want)
    assert {tuple(px) for px in ink[ink[..., 3] > 0][:, :3]} == {(1, 3, 5)}  # ink-950
    assert (ink[..., 3] == 255).sum() > 10_000 and (ink[..., 3] == 0).sum() > 100_000


def test_the_example_data_holds_the_3_cases_of_the_figure():
    lines = (EXAMPLE / "data" / "cooling.csv").read_text().splitlines()
    assert lines[0].startswith("# Example data, made up")
    assert lines[1] == "time_myr,case_1,case_2,case_3"
    rows = [[float(v) for v in line.split(",")] for line in lines[2:]]
    assert len(rows) == 41 and rows[0] == [0.0, 3000.0, 3000.0, 3000.0]
    assert rows[-1][0] == 4.0 and rows[-1][1] < rows[-1][2] < rows[-1][3]


@pytest.mark.skipif(importlib.util.find_spec("fwl_mpl") is None, reason="no fwl-mpl")
def test_the_script_replots_the_committed_figure_from_the_data(tmp_path):
    work = tmp_path / "t"
    shutil.copytree(EXAMPLE, work, ignore=shutil.ignore_patterns("__pycache__"))
    (work / "figures" / "cooling.pdf").unlink()
    run = subprocess.run(
        [sys.executable, "scripts/plot_cooling.py"], cwd=work, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    assert (work / "figures" / "cooling.pdf").read_bytes() == (
        EXAMPLE / "figures" / "cooling.pdf"
    ).read_bytes()


def zip_parts(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename: (i.date_time, z.read(i)) for i in z.infolist()}


def test_the_zip_holds_the_example_at_its_root_with_fixed_times(tmp_path):
    out = thesis.build_thesis_zip(tmp_path / "a.zip")
    parts = zip_parts(out)
    assert "main.tex" in parts and "fwlthesis.cls" in parts and "figures/cooling.pdf" in parts
    assert "fwl-fonts/Geist-Light.ttf" in parts and "fwl-assets/rug-banner-ink.png" in parts
    assert {t for t, _ in parts.values()} == {(2026, 10, 21, 0, 0, 0)}
    assert not any(n.startswith(("/", "..")) or "__pycache__" in n for n in parts)
    assert parts["fwlthesis.cls"][1].decode() == thesis.thesis_cls()
    again = thesis.build_thesis_zip(tmp_path / "b.zip")
    assert out.read_bytes() == again.read_bytes()


def test_the_committed_zip_matches_a_fresh_build(tmp_path):
    fresh = thesis.build_thesis_zip(tmp_path / thesis.ZIP_NAME)
    committed = TEMPLATES / thesis.ZIP_NAME
    rebuild = (
        f'rebuild with: python -m fwl_visual_language.thesis "templates/{thesis.ZIP_NAME}" --zip'
    )
    assert committed.is_file(), rebuild
    old, new = zip_parts(committed), zip_parts(fresh)
    differ = sorted(n for n in old.keys() | new.keys() if old.get(n) != new.get(n))
    assert differ == [], f"{differ} differ; {rebuild}"


def test_the_command_line_installs_writes_the_zip_or_refuses_both(tmp_path, capsys, monkeypatch):
    thesis.main([str(tmp_path / "a")])
    assert (tmp_path / "a" / "fwlthesis.cls").is_file() and not (
        tmp_path / "a" / "main.tex"
    ).exists()
    thesis.main([str(tmp_path / "b"), "--example"])
    assert (tmp_path / "b" / "main.tex").is_file()
    thesis.main([str(tmp_path / "c.zip"), "--zip"])
    assert zipfile.is_zipfile(tmp_path / "c.zip")
    out = capsys.readouterr().out.split()
    assert out == [str(tmp_path / p) for p in ("a/fwlthesis.cls", "b/fwlthesis.cls", "c.zip")]
    with pytest.raises(SystemExit) as err:
        thesis.main([str(tmp_path / "d"), "--example", "--zip"])
    assert err.value.code == 2 and "not allowed with" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["thesis", str(tmp_path / "e")])
    runpy.run_module("fwl_visual_language.thesis", run_name="__main__")
    assert (tmp_path / "e" / "fwlthesis.cls").is_file()


def test_the_theme_build_holds_the_class():
    from fwl_visual_language import __main__ as cli

    assert cli.OUTPUTS["latex/fwlthesis.cls"] is thesis.thesis_cls


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    """Compile the example with and without the final option."""
    folder = tmp_path_factory.mktemp("thesis")
    thesis.install_thesis(folder, example=True)
    main = (folder / "main.tex").read_text()
    (folder / "final.tex").write_text(
        main.replace("\\documentclass{fwlthesis}", "\\documentclass[final]{fwlthesis}", 1)
    )
    logs = {}
    for name in ("main", "final"):
        steps = (["lualatex"], ["bibtex"], ["lualatex"], ["lualatex"])
        for step in steps:
            args = (
                [*step, name] if step == ["bibtex"] else [*step, "-interaction=nonstopmode", name]
            )
            run = subprocess.run(args, cwd=folder, capture_output=True, text=True, timeout=300)
            assert run.returncode == 0, (step, run.stdout[-2000:])
        logs[name] = (folder / f"{name}.log").read_text(errors="replace")
    return folder, logs


def pages(folder, name):
    text = subprocess.run(
        ["pdftotext", "-layout", f"{name}.pdf", "-"], cwd=folder, capture_output=True, text=True
    ).stdout
    return [p for p in text.split("\f") if p.strip()]


def heading(page):
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in page.splitlines() if ln.strip()]
    first = lines[1]  # line 0 is the running head
    return f"{first} {lines[2]}" if first.isdigit() else first


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_example_compiles_with_each_section_on_its_own_page(compiled):
    folder, logs = compiled
    for name, log in logs.items():
        assert not re.search(r"^!|Overfull|undefined|Missing character", log, re.M), name
    draft, final = pages(folder, "main"), pages(folder, "final")
    assert [heading(p) for p in final[1:]] == SECTIONS
    assert [heading(p) for p in draft[1:]] == ["Using this template", *SECTIONS]
    title = re.sub(r"\s+", " ", final[0])
    for words in ("BSC THESIS ASTRONOMY", "KAPTEYN ASTRONOMICAL INSTITUTE", "Title of the thesis",
                  "s1234567", "Second examiner", "Groningen, Month Year"):  # fmt: skip
        assert words in title, words


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_final_option_hides_every_guide(compiled):
    folder, _ = compiled
    draft = " ".join(pages(folder, "main"))
    final = " ".join(pages(folder, "final"))
    for words in GUIDE:
        assert words in draft and words not in final, words
    for words in ("Context.", "Stefan", "Data and script: https://doi.org/10.5281/zenodo.0000000"):
        assert words in re.sub(r"\s+", " ", final), words


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_citations_are_author_year_and_the_fonts_are_the_lab_fonts(compiled):
    folder, _ = compiled
    text = re.sub(r"\s+", " ", " ".join(pages(folder, "main")))
    assert "Lichtenberg et al. (2021)" in text and "(Lichtenberg et al. 2021)" in text
    assert "Journal of Geophysical Research (Planets), 126" in text
    fonts = subprocess.run(["pdffonts", "main.pdf"], cwd=folder, capture_output=True, text=True)
    names = {ln.split()[0].split("+")[-1] for ln in fonts.stdout.splitlines()[2:]}
    assert names == {
        "Geist-Light", "Geist-Medium", "Geist-Regular", "Geist-SemiBold", "GeistMono-Regular",
        "Inter-Italic", "Inter-Regular", "STIXTwoMath-Regular",
    }  # fmt: skip
