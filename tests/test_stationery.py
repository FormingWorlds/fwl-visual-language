"""Email signature and letterhead PDFs."""

import re
import runpy
import shutil
import subprocess
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

from fwl_visual_language import ramp, stationery

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TEX = all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdffonts", "pdfinfo", "pdftoppm"))
TIM = ("Tim Lichtenberg", "Group Leader", "tim.lichtenberg@rug.nl")
TIM_UNIVERSITY = "Assistant Professor"
LAB_LINE = "Forming Worlds Lab · Kapteyn Astronomical Institute · University of Groningen"


def test_the_signature_is_one_line_of_text_in_the_lab_colours():
    text = stationery.signature_html("Tim Lichtenberg")
    assert text.count("\n") == 1 and text.startswith("<p ") and text.endswith("</p>\n")
    assert "<img" not in text and "Geist" not in text
    assert "font-family:'Helvetica Neue', Helvetica, Arial, sans-serif" in text
    assert f'color:{ramp("ink")["600"]}">' in text
    assert (
        f'<span style="color:{ramp("ink")["900"]};font-weight:600">Tim Lichtenberg</span>' in text
    )
    assert (
        f'<a href="https://formingworlds.space" style="color:{ramp("signal")["500"]};'
        'text-decoration:none">Forming Worlds Lab</a>'
    ) in text
    plain = re.sub(r"<[^>]+>", "", text).replace("&middot;", "·").strip()
    assert plain == f"Tim Lichtenberg · {LAB_LINE}"


def test_the_signature_escapes_the_name_and_has_a_placeholder():
    assert ">Name Surname</span>" in stationery.signature_html()
    text = stationery.signature_html(" A <b> & 'C' ")
    assert ">A &lt;b&gt; &amp; &#x27;C&#x27;</span>" in text
    text = stationery.signature_html("Zoë Łukasz")
    assert ">Zo&#235; &#321;ukasz</span>" in text and text.isascii()


@pytest.mark.parametrize("bad", ["", "   ", "two\nlines", "cr\r", None, 3])
def test_every_sender_field_must_be_one_line_of_text(bad):
    with pytest.raises(ValueError, match="name must be"):
        stationery.signature_html(bad)
    for i, label in enumerate(("name", "role", "email")):
        fields = list(TIM)
        fields[i] = bad
        with pytest.raises(ValueError, match=f"{label} must be"):
            stationery.letterhead_tex("letter", *fields)


def test_file_names_and_unknown_kinds():
    assert stationery.letterhead_name("letter") == "Forming Worlds Letterhead.pdf"
    assert stationery.letterhead_name("university") == "Forming Worlds University Letterhead.pdf"
    for call in (
        lambda: stationery.letterhead_name("memo"),
        lambda: stationery.letterhead_tex("memo"),
    ):
        with pytest.raises(ValueError, match="kind must be one of letter, university"):
            call()


def test_the_source_escapes_tex_characters_and_checks_the_room():
    text = stationery.letterhead_tex("letter", "A & B_C", "50% {x} #1 $ ~ ^ \\", "a_b@rug.nl")
    assert "A \\& B\\_C" in text and "a\\_b@rug.nl" in text
    assert "50\\% \\{x\\} \\#1 \\$ \\textasciitilde{} \\textasciicircum{} \\textbackslash{}" in text
    assert "\\\\{[}Visiting{]} {*}Guest, Forming" in stationery.letterhead_tex(
        "letter", role="[Visiting] *Guest"
    )
    assert "\\ifdim\\wd\\fwlsender>118mm" in text
    assert "\\ifdim\\wd\\fwlsender>160mm" in stationery.letterhead_tex("university")
    for kind, logo, banner in (("letter", 1, 0), ("university", 2, 1)):
        source = stationery.letterhead_tex(kind)
        assert source.count("fwl-logo-ink.png") == logo
        assert source.count("rug-banner-ink.png") == banner
        assert f"\\definecolor{{fwlsignal}}{{HTML}}{{{ramp('signal')['500'][1:]}}}" in source
        assert source.count("\\href{https://formingworlds.space}") == 2 * banner
        assert ("{hyperref}" in source) == bool(banner)


def test_a_missing_lualatex_stops_with_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(stationery.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="lualatex is not on the path"):
        stationery.build_letterhead(tmp_path / "x.pdf", "letter")
    assert not (tmp_path / "x.pdf").exists()


def test_a_failed_compile_without_a_tex_error_line_reports_the_log_end(monkeypatch, tmp_path):
    monkeypatch.setattr(stationery.shutil, "which", lambda name: "/bin/lualatex")
    done = types.SimpleNamespace(returncode=1, stdout="early\nno error line here")
    monkeypatch.setattr(stationery.subprocess, "run", lambda *a, **k: done)
    with pytest.raises(RuntimeError, match="lualatex failed for university: early\nno error"):
        stationery.build_letterhead(tmp_path / "x.pdf", "university")


def test_a_failed_build_leaves_the_folder_as_it_was(monkeypatch, tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    (folder / stationery.SIGNATURE_NAME).write_text("old")
    calls = []

    def fail_second(out, kind, *sender):
        calls.append(kind)
        if kind == "university":
            raise RuntimeError("no room")
        Path(out).write_bytes(b"%PDF")

    monkeypatch.setattr(stationery, "build_letterhead", fail_second)
    with pytest.raises(RuntimeError, match="no room"):
        stationery.build_stationery(folder, "New Name")
    assert calls == ["letter", "university"]
    assert sorted(p.name for p in folder.iterdir()) == [stationery.SIGNATURE_NAME]
    assert (folder / stationery.SIGNATURE_NAME).read_text() == "old"
    assert not (tmp_path / "missing").exists()
    with pytest.raises(RuntimeError):
        stationery.build_stationery(tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_the_command_line_reports_a_folder_it_cannot_write(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(stationery, "build_letterhead", lambda out, *a: Path(out).write_bytes(b""))
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    with pytest.raises(SystemExit) as err:
        stationery.main([str(blocker)])
    assert err.value.code == 2 and "File exists" in capsys.readouterr().err
    assert blocker.read_text() == "not a folder"


def test_the_command_line_refuses_an_empty_name(tmp_path, capsys):
    with pytest.raises(SystemExit) as err:
        stationery.main([str(tmp_path / "out"), "--name", " "])
    assert err.value.code == 2
    assert "name must be non-empty text" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_the_module_runs_as_a_script(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["stationery", str(tmp_path / "out"), "--email", ""])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.stationery")
    with pytest.raises(SystemExit) as err:
        runpy.run_module("fwl_visual_language.stationery", run_name="__main__")
    assert err.value.code == 2 and "email must be non-empty text" in capsys.readouterr().err


def test_the_committed_signature_matches_a_fresh_build():
    committed = (TEMPLATES / stationery.SIGNATURE_NAME).read_text(encoding="utf-8")
    assert committed == stationery.signature_html()


def _pages(pdf):
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
    return [re.sub(r"\s+", " ", p).strip() for p in text.stdout.split("\f")][:-1]


@pytest.mark.parametrize(
    "extra, roles",
    [([], ["Lead", "Lead"]), (["--university-role", "Professor"], ["Lead", "Professor"])],
)
def test_the_university_letterhead_can_take_its_own_role(monkeypatch, tmp_path, extra, roles):
    seen = []

    def record(out, kind, name, role, email):
        seen.append(role)
        Path(out).write_bytes(b"%PDF")

    monkeypatch.setattr(stationery, "build_letterhead", record)
    stationery.main([str(tmp_path / "out"), "--role", "Lead", *extra])
    assert seen == roles


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """The placeholder set and my own set, each built by the command line."""
    root = tmp_path_factory.mktemp("stationery")
    stationery.main([str(root / "generic")])
    name, role, email = TIM
    stationery.main(
        [str(root / "tim"), "--name", name, "--role", role, "--email", email]
        + ["--university-role", TIM_UNIVERSITY]
    )
    return root


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_each_letterhead_has_2_a4_pages_with_the_sender_and_footers(built):
    letter, university = (built / "tim" / stationery.letterhead_name(k) for k in stationery.KINDS)
    for pdf in (letter, university):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        assert re.search(r"Pages:\s+2\n", info) and "595.276 x 841.89 pts (A4)" in info
    assert _pages(letter) == [
        "Tim Lichtenberg Group Leader, Forming Worlds Lab Kapteyn Astronomical Institute "
        "University of Groningen Landleven 12, 9747 AD Groningen "
        f"tim.lichtenberg@rug.nl · formingworlds.space {LAB_LINE}",
        f"{LAB_LINE} 2",
    ]
    assert _pages(university) == [
        "Tim Lichtenberg · Assistant Professor, Kapteyn Astronomical Institute · "
        "tim.lichtenberg@rug.nl "
        "Landleven 12, 9747 AD Groningen formingworlds.space",
        "2 formingworlds.space",
    ]
    generic = _pages(built / "generic" / stationery.letterhead_name("university"))[0]
    assert generic.startswith("Name Surname · Role, Kapteyn Astronomical Institute · name@rug.nl")


def _links(pdf):
    urls = subprocess.run(["pdfinfo", "-url", str(pdf)], capture_output=True, text=True)
    assert urls.returncode == 0, urls.stderr
    return re.findall(r"^\s*(\d+)\s+Annotation\s+(\S+)\s*$", urls.stdout, re.M)


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_only_the_university_letterhead_links_the_website_on_each_page(built):
    web = "https://formingworlds.space"
    name = stationery.letterhead_name("university")
    for pdf in (built / "tim" / name, built / "generic" / name, TEMPLATES / name):
        assert _links(pdf) == [("1", web), ("2", web)], pdf
    name = stationery.letterhead_name("letter")
    for pdf in (built / "tim" / name, built / "generic" / name, TEMPLATES / name):
        assert _links(pdf) == [], pdf


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_letterheads_embed_only_geist_and_draw_the_rule_in_signal_blue(built):
    for kind in stationery.KINDS:
        pdf = built / "tim" / stationery.letterhead_name(kind)
        fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout
        names = sorted(ln.split()[0].split("+")[-1] for ln in fonts.splitlines()[2:])
        assert names == ["Geist-Medium", "Geist-Regular"], kind
        assert all(" yes yes yes " in ln for ln in fonts.splitlines()[2:])
    from PIL import Image

    pdf = built / "tim" / stationery.letterhead_name("letter")
    subprocess.run(
        ["pdftoppm", "-r", "300", "-f", "1", "-l", "1", "-png", str(pdf), str(built / "p")]
    )
    image = Image.open(built / "p-1.png").convert("RGB")
    mm = 300 / 25.4
    colours = Counter(
        image.getpixel((int(100 * mm), int(y))) for y in range(int(43 * mm), int(47 * mm))
    )
    signal = tuple(int(ramp("signal")["500"][i : i + 2], 16) for i in (1, 3, 5))

    def blend(c):  # the share of signal blue in a pixel over white, or None for another colour
        share = (255 - c[1]) / (255 - signal[1])
        mix = [255 - share * (255 - s) for s in signal]
        return share if all(abs(m - x) <= 6 for m, x in zip(mix, c, strict=True)) else None

    shares = [blend(c) for c in colours.elements()]
    assert None not in shares  # only white, the blue and its edges over white
    assert 2.8 <= sum(shares) <= 3.9  # 0.8 pt is 3.3 px at 300 dpi


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_the_same_sender_gives_the_same_bytes_and_the_committed_files_match(built, tmp_path):
    for kind, role in (("letter", TIM[1]), ("university", TIM_UNIVERSITY)):
        again = stationery.build_letterhead(tmp_path / f"{kind}.pdf", kind, TIM[0], role, TIM[2])
        assert again.read_bytes() == (built / "tim" / stationery.letterhead_name(kind)).read_bytes()
    assert (
        built / "generic" / stationery.SIGNATURE_NAME
    ).read_text() == stationery.signature_html()
    for kind in stationery.KINDS:
        name = stationery.letterhead_name(kind)
        assert _pages(TEMPLATES / name) == _pages(built / "generic" / name), kind


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_tex_characters_in_the_sender_compile_and_print_as_typed(tmp_path):
    role = "[Visiting] *x 50% #1 $ {y} ~ ^ \\ -- 'q' ``r''"
    pdf = stationery.build_letterhead(
        tmp_path / "x.pdf", "letter", "Ana & Bo_C", role, "a_b@rug.nl"
    )
    assert _pages(pdf)[0].startswith(f"Ana & Bo_C {role}, Forming Worlds Lab ")
    assert "a_b@rug.nl · formingworlds.space" in _pages(pdf)[0]


@pytest.mark.skipif(not TEX, reason="no TeX")
def test_a_character_without_a_glyph_in_geist_stops_the_build(tmp_path):
    with pytest.raises(RuntimeError, match=r"Geist has no glyph for Ε \(U\+0395\); write"):
        stationery.build_letterhead(tmp_path / "x.pdf", "letter", "Ελλάς", "Role", "n@rug.nl")
    assert not (tmp_path / "x.pdf").exists()
    pdf = stationery.build_letterhead(
        tmp_path / "y.pdf", "letter", "Zoë Ångström", "Role", "n@rug.nl"
    )
    assert _pages(pdf)[0].startswith("Zoë Ångström Role, Forming Worlds Lab ")


ROOM_CASES = [
    ("letter", "N", "Postdoctoral researcher in planetary interiors and atmospheres of", "rocky"),
    (
        "university",
        "Firstname Lastname",
        "Postdoctoral researcher in planetary interiors and",
        "atmospheres",
    ),
]


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize("kind, name, role, word", ROOM_CASES)
def test_the_room_ends_within_1_word_of_the_longest_sender_that_fits(
    tmp_path, kind, name, role, word
):
    pdf = stationery.build_letterhead(tmp_path / "x.pdf", kind, name, role, "n@rug.nl")
    unit = "Forming Worlds Lab" if kind == "letter" else "Kapteyn Astronomical Institute"
    assert f"{role}, {unit}" in _pages(pdf)[0]
    with pytest.raises(RuntimeError, match="sender text is wider than"):
        stationery.build_letterhead(tmp_path / "y.pdf", kind, name, f"{role} {word}", "n@rug.nl")


@pytest.mark.skipif(not TEX, reason="no TeX")
@pytest.mark.parametrize("kind, room", [("letter", "118mm"), ("university", "160mm")])
def test_a_sender_wider_than_its_room_stops_the_build(tmp_path, capsys, kind, room):
    role = "Visiting researcher in planetary interiors and atmospheres " * 2
    with pytest.raises(RuntimeError, match=f"sender text is wider than {room}"):
        stationery.build_letterhead(tmp_path / "x.pdf", kind, "Name", role, "n@rug.nl")
    assert not (tmp_path / "x.pdf").exists()
    with pytest.raises(SystemExit) as err:
        stationery.main([str(tmp_path / "cli"), "--role", role])
    assert err.value.code == 2 and "wider than" in capsys.readouterr().err
    assert not (tmp_path / "cli").exists()
