"""Posters and one-pagers: the LaTeX style ``fwlposter.sty`` and the PowerPoint posters."""

import re
import runpy
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from fwl_visual_language import __main__ as cli
from fwl_visual_language import assets_dir, poster, ramp

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TEX = all(shutil.which(t) for t in ("lualatex", "pdffonts", "pdftotext", "pdfinfo", "pdftoppm"))
MESSAGES = ["First statement of the poster", "Second statement here", "Third statement here"]
LONG = "a word " * 60
RED = (192, 57, 43)


def poster_tex(fmt, look, messages=3, **change):
    texts = dict(
        title="A poster title with spaces",
        authors="Name Surname and the Lab",
        affiliation="An Institute",
        contact="formingworlds.space",
        statements=MESSAGES,
        ref="Ref",
    )
    texts.update(change)
    body = "".join(
        f"\\postermessage{{{texts['statements'][i % 3]}}}{{fig}}{{{texts['ref']} {i}a}}"
        f"{{fig}}{{Ref {i}b}}"
        for i in range(messages)
    )
    return (
        f"\\documentclass{{article}}\\usepackage[{fmt},{look}]{{fwlposter}}"
        f"\\postertitle{{{texts['title']}}}\\posterauthors{{{texts['authors']}}}"
        f"\\posteraffiliation{{{texts['affiliation']}}}\\postercontact{{{texts['contact']}}}"
        f"{body}\\begin{{document}}\\makeposter\\end{{document}}\n"
    )


def compile_tex(folder, name, text, ok=True):
    (folder / f"{name}.tex").write_text(text)
    for _ in range(2):  # the overlay picture reads the page position from the first run
        run = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
            cwd=folder, capture_output=True, text=True, timeout=300,
        )  # fmt: skip
        if run.returncode:
            break
    assert (run.returncode == 0) == ok, run.stdout[-1500:]
    return run


def tool(folder, *args):
    run = subprocess.run(args, cwd=folder, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return run.stdout


def test_the_style_declares_every_format_and_both_looks():
    text = poster.poster_sty()
    for name, (w, h, base, layout, *_rest) in poster.FORMATS.items():
        assert f"\\DeclareOption{{{name}}}{{\\def\\fwl@W{{{w}}}\\def\\fwl@H{{{h}}}" in text
        assert f"\\def\\fwl@B{{{base}}}\\def\\fwl@layout{{{layout}}}" in text
    assert "\\DeclareOption{dark}" in text and "\\DeclareOption{light}" in text
    assert "\\ProvidesPackage{fwlposter}[2026/10/20" in text
    assert "\\RequirePackage[math]{fwl}[2026/10/20]" in text


def test_install_poster_writes_the_style_fonts_and_logos(tmp_path):
    out = poster.install_poster(tmp_path / "p")
    assert out.read_text(encoding="utf-8") == poster.poster_sty()
    for rel in ("fwl.sty", "fwl-fonts/Geist-Light.ttf", "fwl-fonts/Inter-Regular.ttf"):
        assert (tmp_path / "p" / rel).is_file(), rel
    for logo in ("fwl-logo-white.png", "fwl-logo-ink.png"):
        assert (tmp_path / "p" / "fwl-assets" / logo).read_bytes() == (
            assets_dir() / logo
        ).read_bytes()


@pytest.fixture(scope="module")
def tex_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp("poster")
    poster.install_poster(folder)
    from PIL import Image

    Image.new("RGB", (800, 500), RED).save(folder / "fig.png")
    return folder


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize("fmt", list(poster.FORMATS))
@pytest.mark.parametrize("look", ["dark", "light"])
def test_each_format_compiles_to_its_page_size_with_every_text(tex_folder, fmt, look):
    name = f"{fmt}-{look}"
    run = compile_tex(tex_folder, name, poster_tex(fmt, look))
    log = (tex_folder / f"{name}.log").read_text(errors="replace")
    assert "Overfull" not in log and "Missing character" not in log, run.stdout[-500:]
    info = tool(tex_folder, "pdfinfo", f"{name}.pdf")
    size = re.search(r"Page size:\s+([\d.]+) x ([\d.]+) pts", info)
    wmm, hmm = poster.FORMATS[fmt][:2]
    assert abs(float(size[1]) - wmm * 72 / 25.4) < 1 and abs(float(size[2]) - hmm * 72 / 25.4) < 1
    assert re.search(r"Pages:\s+1\n", info)
    text = " ".join(tool(tex_folder, "pdftotext", f"{name}.pdf", "-").split())
    # spaces survive: a node with a set text width drops them in large type
    wanted = ["A poster title with spaces", "Name Surname and the Lab", "An Institute"]
    wanted += [*MESSAGES, "formingworlds.space"] + [f"Ref {i}{s}" for i in range(3) for s in "ab"]
    for words in wanted:
        assert words in text, (words, text[:300])
    fonts = tool(tex_folder, "pdffonts", f"{name}.pdf")
    names = {ln.split()[0].split("+")[-1] for ln in fonts.splitlines()[2:]}
    assert {"Geist-Light", "Geist-Medium", "Geist-Regular"} <= names, names
    assert not {n for n in names if not n.startswith(("Geist", "Inter", "STIX"))}, names


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize(
    "fmt, change, message",
    [
        ("a4", {"title": "A title that runs on " * 6}, "taller than the header"),
        ("a4", {"ref": "A reference that runs on " * 8}, "reference a of message 1"),
        ("slide", {"ref": "A reference that runs on " * 4}, "reference a of message 1"),
        ("a4", {"contact": "formingworlds.space and more " * 8}, "contact line"),
        ("a4", {"statements": [LONG, *MESSAGES[1:]]}, "statement of message 1"),
        ("slide", {"statements": [LONG, *MESSAGES[1:]]}, "statement of message 1"),
    ],
)
def test_text_that_does_not_fit_stops_the_run(tex_folder, fmt, change, message):
    run = compile_tex(tex_folder, "long", poster_tex(fmt, "dark", **change), ok=False)
    assert message in run.stdout.replace("\n", ""), run.stdout[-800:]  # TeX wraps at 79


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize("fmt", ["a4", "slide"])
def test_a_longer_statement_pushes_its_figures_down_without_overlap(tex_folder, fmt):
    from PIL import Image

    # rows move the figures from the second line on; columns keep room for 3 lines
    two = "A statement that runs on to a second line in every format of the lab posters"
    if fmt == "slide":
        two += " and on to a fourth line in the narrow columns of the slide"
    tops = {}
    for case, first in (("short", MESSAGES[0]), ("long", two)):
        name = f"push-{fmt}-{case}"
        compile_tex(tex_folder, name, poster_tex(fmt, "light", statements=[first, *MESSAGES[1:]]))
        tool(tex_folder, "pdftoppm", "-r", "30", "-png", f"{name}.pdf", name)
        with Image.open(next(tex_folder.glob(f"{name}-*.png"))) as im:
            im = im.convert("RGB")
            w, h = im.size
            column = range(w // 30, w // 3) if fmt == "slide" else range(w // 30, w // 2)
            reds = [y for y in range(h) for x in column if im.getpixel((x, y)) == RED]
        tops[case] = min(reds) / h
        words = tool(tex_folder, "pdftotext", "-bbox", f"{name}.pdf", "-")
        boxes = re.findall(r'yMax="([\d.]+)">(\w+)</word>', words)
        page_h = float(re.search(r'<page width="[\d.]+" height="([\d.]+)"', words)[1])
        last = (two if case == "long" else MESSAGES[0]).split()[-1]
        bottom = max(float(y) for y, word in boxes if word == last) / page_h
        assert bottom < tops[case], (case, bottom, tops[case])
    assert tops["long"] > tops["short"]


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize("messages", [2, 4])
def test_a_poster_needs_exactly_3_messages(tex_folder, messages):
    run = compile_tex(tex_folder, f"m{messages}", poster_tex("a4", "dark", messages), ok=False)
    expected = "holds 3 messages" if messages == 4 else "needs 3"
    assert expected in run.stdout


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_ground_header_and_rule_have_the_look_colours(tex_folder):
    from PIL import Image

    ink, signal = ramp("ink"), ramp("signal")
    for look, ground, head, rule in (
        ("dark", ink["950"], ink["900"], signal["400"]),
        ("light", "#FFFFFF", ink["50"], signal["500"]),
    ):
        name = f"colours-{look}"
        compile_tex(tex_folder, name, poster_tex("a4", look))
        tool(tex_folder, "pdftoppm", "-r", "40", "-png", f"{name}.pdf", name)
        with Image.open(next(tex_folder.glob(f"{name}-*.png"))) as im:
            im = im.convert("RGB")
            w, h = im.size
            per = h / (297 / 210 * 1000)  # pixels per design unit
            samples = {
                ground: (w // 2, h - 3),
                head: (w - 4, round(4 * per)),
                rule: (w // 2, round(187 * per)),
            }
            for colour, xy in samples.items():
                want = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
                got = im.getpixel(xy)
                assert all(abs(a - b) <= 4 for a, b in zip(got, want, strict=True)), (
                    look,
                    colour,
                    got,
                )


@pytest.fixture
def pptx():
    return pytest.importorskip("pptx")


def slide_texts(slide):
    return [s.text_frame.text for s in slide.shapes if s.has_text_frame and s.text_frame.text]


def overlaps(a, b):
    return (
        a.left < b.left + b.width
        and b.left < a.left + a.width
        and a.top < b.top + b.height
        and (b.top < a.top + a.height)
    )


@pytest.mark.parametrize("fmt", list(poster.FORMATS))
def test_the_pptx_poster_has_a_dark_and_a_light_slide_of_the_format(pptx, tmp_path, fmt):
    from pptx import Presentation
    from pptx.util import Emu

    path = poster.build_pptx_poster(tmp_path / f"{fmt}.pptx", fmt)
    prs = Presentation(path)
    wmm, hmm = poster.FORMATS[fmt][:2]
    assert (prs.slide_width, prs.slide_height) == (Emu(round(wmm * 36000)), Emu(round(hmm * 36000)))
    assert len(prs.slides) == 2
    for slide, ground, panels in zip(prs.slides, ("010305", "FFFFFF"), (6, 0), strict=True):
        assert str(slide.background.fill.fore_color.rgb) == ground
        texts = slide_texts(slide)
        header = texts[0].split("\n")
        assert header == [poster.EXAMPLE[k] for k in ("title", "authors", "affiliation")]
        assert texts[-1] == poster.EXAMPLE["contact"]
        for statement, ref_a, ref_b in poster.EXAMPLE["messages"]:
            assert {statement, ref_a, ref_b} <= set(texts)
        assert {"1", "2", "3"} <= set(texts)
        pictures = [s for s in slide.shapes if s.shape_type == 13]
        assert len(pictures) == 7  # the logo and 6 figures
        rounded = [s for s in slide.shapes if s.shape_type == 1 and s.auto_shape_type == 5]
        assert len(rounded) == panels
        for s in slide.shapes:
            assert 0 <= s.left and s.left + s.width <= prs.slide_width + 2, s.name
            assert 0 <= s.top and s.top + s.height <= prs.slide_height + 2, s.name
        boxes = [s for s in slide.shapes if s.has_text_frame and s.text_frame.text]
        for box in boxes:
            for pic in pictures:
                assert not overlaps(box, pic), (box.text_frame.text, pic.name)


def test_the_pptx_poster_takes_figures_content_and_keeps_aspects(pptx, tmp_path):
    from PIL import Image
    from pptx import Presentation

    figs = []
    for k in range(6):
        figs.append(tmp_path / f"f{k}.png")
        Image.new("RGB", (300 + 200 * k, 600 - 60 * k), "#334455").save(figs[-1])
    content = dict(poster.EXAMPLE, title="Own title")
    prs = Presentation(poster.build_pptx_poster(tmp_path / "p.pptx", "a4", figs, content))
    assert slide_texts(prs.slides[0])[0].startswith("Own title")
    placed = [s for s in prs.slides[0].shapes if s.shape_type == 13][1:]
    for shape, (w, h) in zip(
        placed, [(300 + 200 * k, 600 - 60 * k) for k in range(6)], strict=True
    ):
        assert shape.image.size == (w, h)
        assert abs(shape.width / shape.height - w / h) < 0.01


def test_a_longer_pptx_statement_pushes_its_figures_down(pptx, tmp_path):
    from pptx import Presentation

    tops = {}
    for case, first in (("short", "Short"), ("long", "A statement that runs on " * 4)):
        messages = [(first, "Ref a", "Ref b"), *poster.EXAMPLE["messages"][1:]]
        path = poster.build_pptx_poster(
            tmp_path / f"{case}.pptx", "a4", None, dict(poster.EXAMPLE, messages=messages)
        )
        pictures = [s for s in Presentation(path).slides[0].shapes if s.shape_type == 13]
        tops[case] = pictures[1].top
    assert tops["long"] > tops["short"]


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"fmt": "a3"}, "unknown format"),
        ({"figures": ["a.png"]}, "6 figures"),
        ({"figures": []}, "6 figures"),
        ({"content": dict(poster.EXAMPLE, messages=[("a", "b", "c")])}, "3 messages"),
        ({"content": dict(poster.EXAMPLE, title="A title that runs on " * 6)}, "header"),
        ({"content": dict(poster.EXAMPLE, contact="more words " * 30)}, "contact line"),
        (
            {"content": dict(poster.EXAMPLE, messages=[("S", "A long reference " * 9, "R")] * 3)},
            "reference a of message 1",
        ),
        (
            {"content": dict(poster.EXAMPLE, messages=[("A long statement " * 30, "R", "R")] * 3)},
            "statement of message 1",
        ),
        (
            {
                "fmt": "slide",
                "content": dict(poster.EXAMPLE, messages=[("S", "R", "Ref " * 30)] * 3),
            },
            "reference b of message 1",
        ),
    ],
)
def test_the_pptx_poster_refuses_bad_input(pptx, tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        poster.build_pptx_poster(tmp_path / "p.pptx", **kwargs)


def test_the_pptx_poster_names_the_extra_without_python_pptx(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pptx", None)
    with pytest.raises(ImportError, match=r"fwl-visual-language\[slides\]"):
        poster.build_pptx_poster(tmp_path / "p.pptx")


def test_the_committed_poster_templates_match_a_fresh_build(pptx, tmp_path):
    for path in poster.build_pptx_posters(tmp_path):
        committed = TEMPLATES / path.name
        assert committed.is_file(), "run: python -m fwl_visual_language.poster --pptx templates"
        with zipfile.ZipFile(path) as a, zipfile.ZipFile(committed) as b:
            assert a.namelist() == b.namelist(), path.name
            for name in a.namelist():
                assert a.read(name) == b.read(name), (path.name, name)


def test_the_command_line_installs_the_style_or_writes_the_pptx(
    pptx, tmp_path, capsys, monkeypatch
):
    poster.main([str(tmp_path / "tex")])
    assert (tmp_path / "tex" / poster.STY_NAME).is_file()
    poster.main(["--pptx", str(tmp_path / "pptx")])
    assert len(list((tmp_path / "pptx").glob("*.pptx"))) == len(poster.FORMATS)
    assert "Forming Worlds Poster (a4).pptx" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["poster", str(tmp_path / "again")])
    runpy.run_module("fwl_visual_language.poster", run_name="__main__")
    assert (tmp_path / "again" / poster.STY_NAME).is_file()


def test_the_theme_build_holds_the_poster_style():
    assert cli.OUTPUTS["latex/fwlposter.sty"] is poster.poster_sty


@pytest.mark.parametrize("fmt", list(poster.FORMATS))
def test_pptx_type_sizes_and_line_pitch_follow_the_design_units(pptx, tmp_path, fmt):
    from pptx import Presentation

    w_mm, _, base, _, _, title_u, stmt_u, ref_u = poster.FORMATS[fmt]
    to_pt = w_mm / base * 72 / 25.4  # PowerPoint points are 1/72 in
    slide = Presentation(poster.build_pptx_poster(tmp_path / "p.pptx", fmt)).slides[0]
    sizes = {}
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                if para.runs:
                    sizes[para.runs[0].text] = (para.runs[0].font.size.pt, para.line_spacing.pt)
    statement = poster.EXAMPLE["messages"][0][0]
    assert sizes[poster.EXAMPLE["title"]][0] == pytest.approx(title_u * to_pt, abs=0.06)
    assert sizes[statement][0] == pytest.approx(stmt_u * to_pt, abs=0.06)
    assert sizes[statement][1] == pytest.approx(stmt_u * to_pt * 1.12, abs=0.06)
    assert sizes[poster.EXAMPLE["messages"][0][1]][0] == pytest.approx(ref_u * to_pt, abs=0.06)
