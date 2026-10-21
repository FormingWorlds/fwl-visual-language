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
GUIDE = ("Using this template", "Write the abstract last", "Required. Give the GitHub repository")
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
    "A Appendix",
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
    for command in ("\\thesistype", "\\shorttitle", "\\listoffigures", "\\listoftables"):
        assert f"\\newcommand{{{command}}}" in text or f"\\renewcommand{{{command}}}" in text
    assert "\\iffwl@listed\\addcontentsline{toc}{section}{#1}\\fi" in text
    assert "\\MakeUppercase" not in text and "\\degree" not in text
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
        if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith(".")
    )
    assert (
        files
        == sorted(thesis.EXAMPLE_FILES)
        == [
            "data/cooling.csv",
            "figures/cooling.pdf",
            "latexmkrc",
            "main.tex",
            "references.bib",
            "scripts/plot_cooling.py",
        ]
    )
    for rel in files:
        assert filecmp.cmp(EXAMPLE / rel, tmp_path / "t" / rel, shallow=False), rel


def test_install_copies_no_stray_file_of_the_package(tmp_path, monkeypatch):
    package = tmp_path / "package"
    shutil.copytree(
        EXAMPLE, package / "thesis_example", ignore=shutil.ignore_patterns("__pycache__")
    )
    (package / "thesis_example" / ".DS_Store").write_text("finder")
    (package / "thesis_example" / "data" / "notes.txt").write_text("not in the example")
    monkeypatch.setattr(thesis, "__file__", str(package / "thesis.py"))
    thesis.install_thesis(tmp_path / "u", example=True)
    copied = sorted(
        p.relative_to(tmp_path / "u").as_posix()
        for p in (tmp_path / "u").rglob("*")
        if p.is_file() and not p.relative_to(tmp_path / "u").parts[0].startswith("fwl")
    )
    assert copied == sorted(thesis.EXAMPLE_FILES)


@pytest.mark.parametrize("rel", ["main.tex", "references.bib", "data/cooling.csv"])
def test_install_refuses_to_overwrite_any_file_of_a_thesis(tmp_path, rel):
    dest = tmp_path / "t"
    (dest / rel).parent.mkdir(parents=True)
    (dest / rel).write_text("mine")
    with pytest.raises(FileExistsError, match=f"already in {re.escape(str(dest))}: {rel};"):
        thesis.install_thesis(dest, example=True)
    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()) == [rel]
    assert (dest / rel).read_text() == "mine"
    thesis.install_thesis(dest)  # without the example nothing of the thesis is touched
    assert (dest / rel).read_text() == "mine"


def test_install_refuses_a_dangling_link_and_takes_existing_folders(tmp_path):
    dest = tmp_path / "t"
    dest.mkdir()
    (dest / "main.tex").symlink_to(tmp_path / "nowhere.tex")
    with pytest.raises(FileExistsError, match=r"already in .*: main.tex;"):
        thesis.install_thesis(dest, example=True)
    assert not (tmp_path / "nowhere.tex").exists()
    (dest / "main.tex").unlink()
    (dest / "data").mkdir()
    (tmp_path / "scripts").mkdir()
    (dest / "scripts").symlink_to(tmp_path / "scripts")  # a link to a folder is a folder
    thesis.install_thesis(dest, example=True)
    assert all((dest / rel).is_file() for rel in thesis.EXAMPLE_FILES)


def test_install_refuses_a_file_where_the_example_needs_a_folder(tmp_path, capsys):
    dest = tmp_path / "t"
    dest.mkdir()
    (dest / "data").write_text("a file named data")
    with pytest.raises(FileExistsError, match=r"already in .*: data;"):
        thesis.install_thesis(dest, example=True)
    assert [p.name for p in dest.iterdir()] == ["data"]
    with pytest.raises(SystemExit) as err:
        thesis.main([str(dest), "--example"])
    assert err.value.code == 2 and "already in" in capsys.readouterr().err


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
@pytest.mark.skipif(
    not shutil.which("pdftoppm") or not shutil.which("pdftotext"), reason="no poppler"
)
def test_the_script_replots_the_committed_figure_from_the_data(tmp_path):
    work = tmp_path / "t"
    shutil.copytree(EXAMPLE, work, ignore=shutil.ignore_patterns("__pycache__"))
    (work / "figures" / "cooling.pdf").unlink()
    run = subprocess.run(
        [sys.executable, "scripts/plot_cooling.py"], cwd=work, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    import numpy as np
    from PIL import Image

    def pixels(pdf, name):
        subprocess.run(
            ["pdftoppm", "-r", "100", "-png", "-singlefile", pdf, tmp_path / name], check=True
        )
        return np.asarray(Image.open(tmp_path / f"{name}.png").convert("L")).astype(int)

    new = pixels(work / "figures" / "cooling.pdf", "new")
    old = pixels(EXAMPLE / "figures" / "cooling.pdf", "old")
    assert new.shape == old.shape
    assert (np.abs(new - old) > 64).mean() < 0.002  # the same plot, up to anti-aliasing
    assert (old < 128).mean() > 0.01 and (new < 128).mean() > 0.01  # neither is blank

    def text(pdf):
        out = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True)
        return out.stdout.split()

    labels = {"Time", "(Myr)", "Surface", "temperature", "(K)", "case"}
    for pdf in (work / "figures" / "cooling.pdf", EXAMPLE / "figures" / "cooling.pdf"):
        words = text(pdf)
        assert labels <= set(words), pdf
        assert " ".join(words).count("case") == 3  # the legend: case 1, case 2, case 3


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


EXTRA_BIB = (
    "@ARTICLE{Test2020, author = {{Test}, Ann}, title = {A test entry},"
    " journal = {\\apj}, year = 2020}\n"
)
TABLE = (
    "\\begin{table}[h]\\caption{Parameters.}\\centering"
    "\\begin{tabular}{ll}a & b\\end{tabular}\\end{table}\n"
)
LONG = "A long thesis title that runs over more than one line of the title page and the head"


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    """Compile the example as shipped, and a final version with more of the class."""
    folder = tmp_path_factory.mktemp("thesis")
    thesis.install_thesis(folder, example=True)
    main = (folder / "main.tex").read_text()
    final = main
    for old, new in (
        ("\\documentclass{fwlthesis}", "\\documentclass[final]{fwlthesis}"),
        ("\\title{Title of the thesis}", f"\\title{{{LONG}}}\\shorttitle{{Short title}}"),
        ("% \\listoffigures\n", "\\listoffigures\n\\listoftables\n"),
        ("Figure~\\ref{fig:cooling} shows", TABLE + "Figure~\\ref{fig:cooling} shows"),
        ("The surface radiates", "\\subsection{Model}\nThe surface radiates"),
        ("\\bibliography{references}", "\\nocite{Test2020}\\bibliography{references,extra}"),
    ):
        assert final.count(old) == 1, old
        final = final.replace(old, new)
    (folder / "final.tex").write_text(final)
    (folder / "extra.bib").write_text(EXTRA_BIB)
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


def page_count(folder, name):
    info = subprocess.run(["pdfinfo", f"{name}.pdf"], cwd=folder, capture_output=True, text=True)
    return int(re.search(r"^Pages:\s+(\d+)", info.stdout, re.M).group(1))


def pages(folder, name):
    text = subprocess.run(
        ["pdftotext", "-layout", f"{name}.pdf", "-"], cwd=folder, capture_output=True, text=True
    ).stdout
    return [p for p in text.split("\f") if p.strip()]


def heading(page):
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in page.splitlines() if ln.strip()]
    first = lines[1]  # line 0 is the running head
    numbered = first.isdigit() or re.fullmatch("[A-Z]", first)  # 1 Introduction, A Extra
    return f"{first} {lines[2]}" if numbered else first


FINAL = [
    "Abstract",
    "Samenvatting",
    "Contents",
    "List of Figures",
    "List of Tables",
    "1 Introduction",
    "2 Methods",
    "3 Results",
    "4 Discussion",
    "5 Conclusions",
    "Data and code availability",
    "Acknowledgments",
    "References",
    "A Appendix",
]
LOG_FAULTS = r"^!|Overfull|undefined|Missing character|Package fancyhdr Warning"


def head(page):
    return re.sub(r"\s+", " ", next(ln for ln in page.splitlines() if ln.strip())).strip()


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_example_compiles_with_each_section_on_its_own_page(compiled):
    folder, logs = compiled
    for name, log in logs.items():
        assert not re.search(LOG_FAULTS, log, re.M), name
    draft, final = pages(folder, "main"), pages(folder, "final")
    known = {"Using this template", *SECTIONS}
    assert [heading(p) for p in draft[1:] if heading(p) in known] == [
        "Using this template",
        *SECTIONS,
    ]
    assert len(draft) == page_count(folder, "main")  # the tips may fill 2 pages, none is blank
    assert [heading(p) for p in final[1:]] == FINAL
    # no page is blank: every page of the PDF holds one of these headings
    assert page_count(folder, "final") == len(FINAL) + 1
    title = re.sub(r"\s+", " ", final[0])
    assert "formingworlds.space" in title
    assert "kapteyn" not in title.lower()  # the banner, an image, already names the institute
    for words in (
        LONG,
        "BSc/MSc thesis Astronomy",
        "s1234567",
        "Second examiner",
        "Groningen, Month Year",
    ):
        assert words in title, words


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_running_head_and_the_contents(compiled):
    folder, _ = compiled
    final = pages(folder, "final")
    by_heading = {heading(p): p for p in final[1:]}
    assert head(by_heading["2 Methods"]).startswith("Short title")
    assert head(by_heading["2 Methods"]).endswith("2 Methods")
    assert head(by_heading["References"]).endswith("References")
    assert head(by_heading["A Appendix"]).endswith("A Appendix")
    assert LONG not in head(by_heading["2 Methods"])
    draft = {heading(p): p for p in pages(folder, "main")[1:]}
    assert head(draft["2 Methods"]).startswith("Title of the thesis")
    contents = re.sub(r"\s+", " ", by_heading["Contents"])
    for entry in ("1 Introduction", "2.1 Model", "5 Conclusions", "Data and code availability",
                  "Acknowledgments", "References", "A Appendix"):  # fmt: skip
        assert entry in contents, entry
    for entry in ("Abstract", "Samenvatting"):
        assert entry not in contents.replace("Contents", ""), entry
    tables = re.sub(r"\s+", " ", by_heading["List of Tables"])
    assert "1 Parameters." in tables
    anchors = re.findall(r"\{([a-z]+\*?\.[0-9A-Za-z.]+)\}%", (folder / "final.toc").read_text())
    assert len(anchors) == len(set(anchors)) == 12, anchors  # every entry has its own anchor
    methods = re.sub(r"\s+", " ", by_heading["2 Methods"])
    assert "starts at 3000 K" in methods and "F the emitted flux" in methods
    assert "Lichtenberg" not in methods
    figures = re.sub(r"\s+", " ", by_heading["List of Figures"])
    assert "1 Surface temperature against time" in figures and "zenodo" not in figures


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_final_option_hides_every_guide(compiled):
    folder, _ = compiled
    draft = " ".join(pages(folder, "main"))
    final = " ".join(pages(folder, "final"))
    for words in GUIDE:
        assert words in draft and words not in final, words
    for words in (
        "Context.",
        "Stefan-Boltzmann",
        "Data and script: https://doi.org/10.5281/zenodo.0000000",
    ):
        assert words in re.sub(r"\s+", " ", final), words


@pytest.mark.skipif(not TEX or not shutil.which("pdftoppm"), reason="no TeX")
def test_guides_are_grey_and_section_numbers_signal_blue(compiled):
    import numpy as np
    from PIL import Image

    folder, _ = compiled

    def near(name, page, rgb):
        stem = folder / f"{name}-p{page}"
        pick = ["-f", str(page), "-l", str(page)]
        args = ["pdftoppm", "-r", "100", "-png", "-singlefile", *pick, f"{name}.pdf", str(stem)]
        subprocess.run(args, cwd=folder, check=True)
        px = np.asarray(Image.open(f"{stem}.png").convert("RGB")).astype(int)
        return int((np.abs(px - rgb).sum(axis=2) < 4).sum())  # exact colour, not edges

    grey, blue = (107, 116, 124), (0, 114, 161)  # ink-500 and signal-500
    intro = 1 + [heading(p) for p in pages(folder, "main")].index("1 Introduction")
    assert near("main", intro, grey) > 200
    assert near("main", intro, blue) > 100
    final_intro = 1 + FINAL.index("1 Introduction") + 1
    assert near("final", final_intro, grey) < 30
    assert near("final", final_intro, blue) > 100


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_citations_are_author_year_and_the_fonts_are_the_lab_fonts(compiled):
    folder, _ = compiled
    text = re.sub(r"\s+", " ", " ".join(pages(folder, "main")))
    assert "Lichtenberg et al. (2021)" in text and "(Lichtenberg et al. 2021)" in text
    assert "Journal of Geophysical Research (Planets), 126" in text
    assert "Hamano, K., Abe, Y., & Genda, H. 2013, Nature, 497, 607" in text  # the \\nat macro
    for cite in (
        "(Hamano et al. 2013; Lichtenberg et al. 2021)",  # the order of the keys
        "(e.g., Hamano et al. 2013)",
        "(see Lichtenberg et al. 2021, Fig. 3)",
        "(Hamano et al. 2013, Sect. 2)",
    ):
        assert cite in text, cite
    final = re.sub(r"\s+", " ", " ".join(pages(folder, "final")))
    assert "Test, A. 2020, ApJ" in final  # an ADS journal macro in the .bib
    fonts = subprocess.run(["pdffonts", "main.pdf"], cwd=folder, capture_output=True, text=True)
    names = {ln.split()[0].split("+")[-1] for ln in fonts.stdout.splitlines()[2:]}
    assert names == {
        "Geist-Light", "Geist-Medium", "Geist-Regular", "Geist-SemiBold", "GeistMono-Regular",
        "Inter-Italic", "Inter-Regular", "STIXTwoMath-Regular",
    }  # fmt: skip


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_a_long_title_without_a_short_form_gets_a_warning(compiled, tmp_path):
    folder, logs = compiled
    thesis.install_thesis(tmp_path)
    doc = f"\\documentclass{{fwlthesis}}\\title{{{LONG}}}\\begin{{document}}x\\end{{document}}\n"
    (tmp_path / "long.tex").write_text(doc)
    run = subprocess.run(["lualatex", "-interaction=nonstopmode", "long"], cwd=tmp_path,
                         capture_output=True, text=True, timeout=300)  # fmt: skip
    assert run.returncode == 0, run.stdout[-1500:]
    warning = "The title is too wide"
    assert warning in re.sub(r"\s+", " ", (tmp_path / "long.log").read_text(errors="replace"))
    assert not any(warning in re.sub(r"\s+", " ", log) for log in logs.values())
