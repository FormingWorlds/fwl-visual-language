"""Word templates (.dotx) for letters, reports, memos and handbooks."""

import re
import runpy
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("docx")
from lxml import etree  # noqa: E402

from fwl_visual_language import assets_dir, word  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1]}
FACE = {
    "geist": ("Geist", "Geist Light", "Geist Medium"),
    "aptos": ("Aptos", "Aptos Light", "Aptos SemiBold"),
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("word")
    paths = iter(word.build_word(d))
    return {(k, f): next(paths) for f in word.FACES for k in word.KINDS}


def part(path, name):
    with zipfile.ZipFile(path) as z:
        return etree.fromstring(z.read(name))


def style(path, sid):
    s = part(path, "word/styles.xml").find(f"w:style[@w:styleId='{sid}']", NS)
    assert s is not None, sid
    return s


def val(el, tag):
    found = el.find(f".//w:{tag}", NS)
    return None if found is None else found.get(f"{W}val")


def fonts(el):
    rf = el.find(".//w:rPr/w:rFonts", NS)
    return {k.split("}")[1]: v for k, v in rf.attrib.items()}


def texts(path):
    with zipfile.ZipFile(path) as z:
        names = [
            n for n in z.namelist() if re.fullmatch(r"word/(document|header\d+|footer\d+)\.xml", n)
        ]
        return " ".join("".join(etree.fromstring(z.read(n)).itertext()) for n in names)


def test_every_kind_and_face_is_a_template_with_the_lab_name(built):
    assert sorted(built) == sorted((k, f) for k in word.KINDS for f in word.FACES)
    assert built["letter", "geist"].name == "Forming Worlds Letter (Geist).dotx"
    for path in built.values():
        types = part(path, "[Content_Types].xml")
        doc = [o for o in types if o.get("PartName") == "/word/document.xml"]
        assert doc[0].get("ContentType") == word.TEMPLATE_CT


def test_docx_documents_keep_the_document_type(tmp_path):
    (path,) = word.build_word(tmp_path, ["aptos"], ["memo"], template=False)
    assert path.suffix == ".docx"
    types = part(path, "[Content_Types].xml")
    doc = [o for o in types if o.get("PartName") == "/word/document.xml"]
    assert doc[0].get("ContentType").endswith("document.main+xml")


@pytest.mark.parametrize("face", ["geist", "aptos"])
def test_styles_set_the_face_size_and_colour(built, face):
    regular, light, medium = FACE[face]
    path = built["report", face]
    expect = {
        "Normal": (regular, "21", "03090F"),
        "Title": (light, "48", "010305"),
        "Subtitle": (regular, "24", "475159"),
        "Heading1": (medium, "26", "010305"),
        "Heading2": (medium, "22", "010305"),
        "Caption": (regular, "17", "475159"),
        "Footer": (regular, "15", "6B747C"),
        "Keyword": (medium, None, "B74B21"),
        "Hyperlink": (regular, None, "0072A1"),
        "Note": (regular, "20", "2A343C"),
    }
    for sid, (face_name, size, color) in expect.items():
        s = style(path, sid)
        assert set(fonts(s).values()) == {face_name}, sid
        assert set(fonts(s)) == {"ascii", "hAnsi", "eastAsia", "cs"}, sid
        assert (val(s, "sz"), val(s, "color")) == (size, color), sid
        if size:
            assert val(s, "szCs") == size, sid
        for leftover in ("bCs", "iCs", "kern", "b", "i"):
            assert s.find(f".//w:rPr/w:{leftover}", NS) is None, (sid, leftover)
    assert style(path, "Title").find(".//w:rPr/w:spacing", NS) is None
    assert style(path, "Subtitle").find(".//w:rPr/w:spacing", NS) is None
    assert style(path, "Memolabel").find(".//w:rPr/w:spacing", NS).get(f"{W}val") == "40"
    defaults = part(path, "word/styles.xml").find("w:docDefaults/w:rPrDefault", NS)
    assert set(fonts(defaults).values()) == {regular}


def test_handbook_chapters_open_a_page_and_the_report_does_not(built):
    hb, rep = (
        style(built["handbook", "geist"], "Heading1"),
        style(built["report", "geist"], "Heading1"),
    )
    assert hb.find(".//w:pageBreakBefore", NS) is not None
    assert (val(hb, "sz"), fonts(hb)["ascii"]) == ("40", "Geist Light")
    assert rep.find(".//w:pageBreakBefore", NS) is None
    toc = style(built["handbook", "geist"], "TOCHeading")
    assert toc.find(".//w:numPr/w:numId", NS).get(f"{W}val") == "0"
    assert toc.find(".//w:pageBreakBefore", NS).get(f"{W}val") in ("0", "false")


def test_numbering_links_headings_and_lists_in_signal_blue(built):
    path = built["handbook", "aptos"]
    links = {
        "Heading1": ("90", "0"),
        "Heading2": ("90", "1"),
        "ListBullet": ("91", "0"),
        "ListNumber": ("92", "0"),
        "ListNumber2": ("92", "1"),
    }
    for sid, (num, lvl) in links.items():
        numpr = style(path, sid).find(".//w:numPr", NS)
        assert (val(numpr, "numId"), val(numpr, "ilvl")) == (num, lvl), sid
    numbering = part(path, "word/numbering.xml")
    tags = [c.tag for c in numbering]
    assert max(i for i, t in enumerate(tags) if t == f"{W}abstractNum") < tags.index(f"{W}num")
    absn = {a.get(f"{W}abstractNumId"): a for a in numbering.findall("w:abstractNum", NS)}
    texts_ = {
        k: [val(lv, "lvlText") for lv in absn[k].findall("w:lvl", NS)] for k in ("90", "91", "92")
    }
    assert texts_ == {"90": ["%1", "%1.%2"], "91": ["•"], "92": ["%1.", "%2."]}
    for k in ("90", "91", "92"):
        assert {val(lv, "color") for lv in absn[k].findall("w:lvl", NS)} == {"0072A1"}
    assert set(fonts(absn["91"].find("w:lvl", NS)).values()) == {"Aptos"}
    assert val(absn["90"].find("w:lvl", NS), "sz") == "40"  # the large chapter number
    assert val(part(built["report", "aptos"], "word/numbering.xml"), "sz") is None


def test_letter_header_has_logo_sender_and_blue_rule_on_page_one(built):
    path = built["letter", "geist"]
    doc = part(path, "word/document.xml")
    assert doc.find(".//w:sectPr/w:titlePg", NS) is not None
    with zipfile.ZipFile(path) as z:
        rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
        first = doc.find(".//w:headerReference[@w:type='first']", NS).get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        target = next(r.get("Target") for r in rels if r.get("Id") == first)
        hdr = etree.fromstring(z.read(f"word/{target}"))
    assert hdr.find(".//{*}blip") is not None
    assert "Name Surname" in "".join(hdr.itertext()) and "name@rug.nl" in "".join(hdr.itertext())
    last = hdr[-1]
    assert last.tag == f"{W}p"
    assert last.find(".//w:pBdr/w:bottom", NS).get(f"{W}color") == "0072A1"
    assert word.LAB_LINE in texts(path)


def test_footers_clear_the_style_tabs_and_number_the_page(built):
    for path in built.values():
        with zipfile.ZipFile(path) as z:
            footers = [
                etree.fromstring(z.read(n))
                for n in z.namelist()
                if re.fullmatch(r"word/footer\d+\.xml", n)
            ]
        filled = [f for f in footers if f.find(".//w:fldSimple", NS) is not None]
        assert filled, path.name
        for f in filled:
            assert f.find(".//w:fldSimple", NS).get(f"{W}instr") == "PAGE"
            tabs = {(t.get(f"{W}val"), t.get(f"{W}pos")) for t in f.findall(".//w:tab", NS)}
            assert {("clear", "4680"), ("clear", "9360"), ("right", "9411")} <= tabs, path.name


def test_memo_has_label_logo_and_narrow_label_column(built):
    doc = part(built["memo", "geist"], "word/document.xml")
    first, rows = doc.findall(".//w:tbl", NS)[:2]
    assert "MEMO" in "".join(first.itertext()) and first.find(".//{*}blip") is not None
    labels = ["".join(r.find("w:tc", NS).itertext()) for r in rows.findall("w:tr", NS)]
    assert labels == ["To", "From", "Date", "Subject"]
    assert [g.get(f"{W}w") for g in rows.findall("w:tblGrid/w:gridCol", NS)] == ["1361", "8050"]


def test_handbook_has_cover_contents_field_and_note(built):
    path = built["handbook", "geist"]
    doc = part(path, "word/document.xml")
    paras = doc.findall(".//w:body/w:p", NS)
    styles = [val(p, "pStyle") for p in paras]
    assert styles[1:6] == ["Covertitle", "Coversubtitle", "Byline", "Subject", None]
    breaks = [i for i, p in enumerate(paras) if p.find(".//w:br[@w:type='page']", NS) is not None]
    assert breaks[0] == 5  # the welcome stays on the cover; the contents start on page 2
    assert {
        "TOCHeading",
        "Heading1",
        "Heading2",
        "Heading3",
        "ListNumber",
        "ListNumber2",
        "Note",
    } <= set(styles)
    toc = paras[styles.index("TOCHeading") + 1]
    kinds = [c.get(f"{W}fldCharType") for c in toc.findall(".//w:fldChar", NS)]
    assert kinds == ["begin", "separate", "end"]
    assert toc.find(".//w:instrText", NS).text.strip() == 'TOC \\o "1-2" \\h \\z \\u'
    note = style(path, "Note")
    assert note.find(".//w:pBdr/w:left", NS).get(f"{W}color") == "0072A1"
    assert note.find(".//w:shd", NS).get(f"{W}fill") == "F3F6F9"
    toc1 = style(path, "TOC1").find(".//w:tabs/w:tab", NS)
    assert (toc1.get(f"{W}leader"), toc1.get(f"{W}pos")) == ("dot", "9411")


def test_templates_hold_placeholders_only(built):
    for path in built.values():
        text = texts(path)
        assert not re.search(r"\bTim\b|Lichtenberg|@astro|@gmail", text), path.name
        props = part(path, "docProps/core.xml")
        assert {e.text for e in props if e.tag.endswith(("creator", "lastModifiedBy"))} == {
            "Forming Worlds Lab"
        }


def test_a_build_is_reproducible(tmp_path):
    a = word.build_word(tmp_path / "a", ["geist"], ["handbook"])[0]
    b = word.build_word(tmp_path / "b", ["geist"], ["handbook"])[0]
    with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
        assert {n: za.read(n) for n in za.namelist()} == {n: zb.read(n) for n in zb.namelist()}


def test_the_ink_logo_is_the_white_logo_with_ink_letters():
    white = (assets_dir() / "fwl-logo-white.svg").read_text()
    ink = (assets_dir() / "fwl-logo-ink.svg").read_text()
    assert white.count('fill="#fff"') == 4
    assert ink == white.replace('fill="#fff"', 'fill="#010305"')
    import numpy as np
    from PIL import Image

    def dark_pixels(name):
        with Image.open(assets_dir() / name) as im:
            a = np.asarray(im.convert("RGBA"))
        return a.shape[:2], int(((a[..., 3] > 200) & (a[..., :3].max(axis=2) < 40)).sum())

    (ink_size, ink_dark), (white_size, white_dark) = map(
        dark_pixels, ("fwl-logo-ink.png", "fwl-logo-white.png")
    )
    assert ink_size == white_size == (662, 1200)
    assert ink_dark > 50_000 and white_dark == 0


def test_unknown_faces_and_kinds_are_refused(tmp_path):
    with pytest.raises(ValueError, match="unknown face or kind: \\['comic'\\]"):
        word.build_word(tmp_path, ["comic"])
    with pytest.raises(ValueError, match="poster"):
        word.build_word(tmp_path, kinds=["poster"])
    assert not list(tmp_path.iterdir())


def test_a_missing_python_docx_names_the_extra(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "docx", None)
    with pytest.raises(ImportError, match=r"fwl-visual-language\[word\]"):
        word.build_word(tmp_path)


def test_command_line_and_module_run(tmp_path, capsys, monkeypatch):
    word.main([str(tmp_path / "cli"), "--face", "aptos", "--docx"])
    out = capsys.readouterr().out.split("\n")
    assert sorted(p.name for p in (tmp_path / "cli").iterdir()) == sorted(
        f"{word.template_name(k, 'aptos')}.docx" for k in word.KINDS
    )
    assert len([line for line in out if line]) == len(word.KINDS)
    monkeypatch.setattr(sys, "argv", ["word", str(tmp_path / "mod")])
    runpy.run_module("fwl_visual_language.word", run_name="__main__")
    assert len(list((tmp_path / "mod").glob("*.dotx"))) == 2 * len(word.KINDS)


def test_the_committed_templates_match_a_fresh_build(tmp_path):
    folder = Path(__file__).resolve().parents[1] / "templates"
    fresh = {p.name: p for p in word.build_word(tmp_path)}
    committed = sorted(p.name for p in folder.glob("*.dotx"))
    assert committed == sorted(fresh), "rebuild with: python -m fwl_visual_language.word templates"
    for name, path in fresh.items():
        with zipfile.ZipFile(folder / name) as a, zipfile.ZipFile(path) as b:
            old = {n: a.read(n) for n in a.namelist()}
            new = {n: b.read(n) for n in b.namelist()}
        differ = sorted(n for n in old.keys() | new.keys() if old.get(n) != new.get(n))
        assert differ == [], (
            f"{name}: {differ} differ; rebuild with: python -m fwl_visual_language.word templates"
        )


ORDER = {
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
              "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
              "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"],
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
            "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
            "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
            "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
            "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
            "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
    "rPr": ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
            "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish",
            "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight",
            "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
            "eastAsianLayout", "specVanish", "oMath"],
}  # fmt: skip


def test_property_children_keep_the_schema_order(built):
    for path in built.values():
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if re.fullmatch(r"word/[a-z0-9]+\.xml", n)]
            roots = {n: etree.fromstring(z.read(n)) for n in names}
        for name, root in roots.items():
            for tag, order in ORDER.items():
                for el in root.iter(f"{W}{tag}"):
                    kids = [c.tag.split("}")[1] for c in el if c.tag.startswith(W)]
                    assert set(kids) <= set(order) | {"ins", "del"}, (path.name, tag, kids)
                    pos = [order.index(k) for k in kids if k in order]
                    assert pos == sorted(set(pos)), (path.name, name, tag, kids)


def test_every_template_embeds_the_ink_logo(built):
    ink = (assets_dir() / "fwl-logo-ink.png").read_bytes()
    for path in built.values():
        with zipfile.ZipFile(path) as z:
            media = [z.read(n) for n in z.namelist() if n.startswith("word/media/")]
        banner = (assets_dir() / "rug-banner.png").read_bytes()
        expect = {ink, banner} if "University" in path.name else {ink}
        assert media and set(media) == expect, path.name


def test_numbers_point_at_their_lists_and_borders_are_stripped(built):
    path = built["handbook", "geist"]
    numbering = part(path, "word/numbering.xml")
    nums = {n.get(f"{W}numId"): val(n, "abstractNumId") for n in numbering.findall("w:num", NS)}
    assert {k: nums[k] for k in ("90", "91", "92")} == {"90": "90", "91": "91", "92": "92"}
    assert len(nums) == len(numbering.findall("w:num", NS))
    absn = {a.get(f"{W}abstractNumId"): a for a in numbering.findall("w:abstractNum", NS)}
    fmts = {
        k: [val(lv, "numFmt") for lv in absn[k].findall("w:lvl", NS)] for k in ("90", "91", "92")
    }
    assert fmts == {
        "90": ["decimal", "decimal"],
        "91": ["bullet"],
        "92": ["decimal", "lowerLetter"],
    }
    for sid in ("Title", "Subtitle", "Heading3"):
        s = style(path, sid)
        assert s.find(".//w:pBdr", NS) is None and s.find(".//w:numPr", NS) is None, sid
    for sid in ("Heading1", "Heading2"):
        assert style(path, sid).find(".//w:pBdr", NS) is None, sid
    for sid in ("Heading1", "Heading2", "Heading3"):
        assert style(path, sid).find(".//w:keepNext", NS) is not None, sid


def test_pages_are_a4_with_the_lab_margins(built):
    for path in built.values():
        sect = part(path, "word/document.xml").find(".//w:body/w:sectPr", NS)
        size, mar = sect.find("w:pgSz", NS), sect.find("w:pgMar", NS)
        assert (size.get(f"{W}w"), size.get(f"{W}h")) == ("11906", "16838"), path.name
        sides = [mar.get(f"{W}{k}") for k in ("top", "bottom", "left", "right")]
        assert sides == ["1247"] * 4, path.name
        assert part(path, "docProps/core.xml").find("{*}description") is None or not (
            part(path, "docProps/core.xml").find("{*}description").text
        )


@pytest.mark.parametrize(
    "sid, face, size, color",
    [
        ("Header", 0, "15", "6B747C"),
        ("Heading3", 2, "21", "03090F"),
        ("ListNumber", 0, "21", "03090F"),
        ("ListNumber2", 0, "21", "03090F"),
        ("ListBullet", 0, "21", "03090F"),
        ("Byline", 0, "18", "6B747C"),
        ("Subject", 2, "22", "010305"),
        ("Dateline", 0, "19", "475159"),
        ("Sender", 0, "16", "475159"),
        ("Memolabel", 2, "18", "0072A1"),
        ("Covertitle", 1, "80", "010305"),
        ("Coversubtitle", 1, "32", "0072A1"),
        ("TOCHeading", 2, "26", "010305"),
        ("TOC1", 2, "21", "010305"),
        ("TOC2", 0, "20", "475159"),
    ],
)
def test_the_other_styles_set_face_size_and_colour(built, sid, face, size, color):
    for f in ("geist", "aptos"):
        s = style(built["handbook", f], sid)
        assert set(fonts(s).values()) == {FACE[f][face]}, (sid, f)
        assert (val(s, "sz"), val(s, "color")) == (size, color), (sid, f)


def spacing(s):
    sp = s.find(".//w:pPr/w:spacing", NS)
    get = (lambda k: sp.get(f"{W}{k}")) if sp is not None else (lambda k: None)
    ind = s.find(".//w:pPr/w:ind", NS)
    return get("before"), get("after"), get("line"), None if ind is None else ind.get(f"{W}left")


def test_styles_set_their_spacing_and_indents(built):
    path = built["handbook", "geist"]
    expect = {  # twentieths of a point; line in 240ths; indent in twips
        "Normal": (None, "120", "288", None),
        "Title": ("360", "40", "240", None),
        "Heading1": ("0", "360", None, None),
        "Heading2": ("240", "80", None, None),
        "Caption": ("80", "240", "240", None),
        "Note": ("120", "160", None, "227"),
        "TOC2": ("0", "40", None, "340"),
        "Covertitle": ("2200", "80", None, None),
    }
    assert {sid: spacing(style(path, sid)) for sid in expect} == expect
    assert spacing(style(built["report", "geist"], "Heading1"))[:2] == ("320", "120")


@pytest.mark.parametrize(
    "kind, left, first_page",
    [
        ("letter", word.LAB_LINE, True),
        ("report", "Title of the report  ·  Forming Worlds Lab", False),
        ("memo", "Forming Worlds Lab  ·  internal memo", False),
        ("handbook", "Forming Worlds Lab  ·  Handbook", True),
        ("university-letter", "", True),
    ],
)
def test_each_kind_has_its_footer_and_first_page_setting(built, kind, left, first_page):
    path = built[kind, "aptos"]
    doc = part(path, "word/document.xml")
    assert (doc.find(".//w:sectPr/w:titlePg", NS) is not None) == first_page
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as z:
        rels = {
            r.get("Id"): r.get("Target")
            for r in etree.fromstring(z.read("word/_rels/document.xml.rels"))
        }
        refs = {
            f.get(f"{W}type"): f.get(rid) for f in doc.findall(".//w:sectPr/w:footerReference", NS)
        }
        default = etree.fromstring(z.read(f"word/{rels[refs['default']]}"))
        first = etree.fromstring(z.read(f"word/{rels[refs['first']]}")) if "first" in refs else None
    p = default.find("w:p", NS)
    assert "".join(p.itertext()) == left + "1" and p.find(".//w:r/w:tab", NS) is not None
    assert val(p, "pStyle") == "Footer"
    if kind == "letter":
        assert "".join(first.itertext()) == left + "1"
    elif kind == "handbook":  # the cover has no footer
        assert first is None or not "".join(first.itertext()).strip()


def test_tables_have_no_borders_and_the_sender_block_its_style(built):
    for kind in ("letter", "memo"):
        with zipfile.ZipFile(built[kind, "geist"]) as z:
            xml = [
                etree.fromstring(z.read(n))
                for n in z.namelist()
                if re.fullmatch(r"word/(document|header\d+)\.xml", n)
            ]
        tables = [t for x in xml for t in x.iter(f"{W}tbl")]
        assert len(tables) == (1 if kind == "letter" else 2)
        for t in tables:
            b = t.find("w:tblPr/w:tblBorders", NS)
            assert b is not None and [c.get(f"{W}val") for c in b] == ["nil"] * 6, kind
    doc = part(built["letter", "geist"], "word/document.xml")
    with zipfile.ZipFile(built["letter", "geist"]) as z:
        hdr = next(
            etree.fromstring(z.read(n))
            for n in z.namelist()
            if re.fullmatch(r"word/header\d+\.xml", n) and b"Name Surname" in z.read(n)
        )
    cell = hdr.findall(".//w:tc", NS)[1]
    lines = cell.findall("w:p", NS)
    assert ["".join(p.itertext()) for p in lines] == list(word.SENDER)
    assert {val(p, "pStyle") for p in lines} == {"Sender"} and {val(p, "jc") for p in lines} == {
        "right"
    }
    assert fonts(lines[0].find("w:r", NS))["ascii"] == "Geist Medium"
    assert doc is not None


def test_letters_justify_their_text_and_the_other_kinds_do_not(built):
    for (kind, face), path in built.items():
        jc = val(style(path, "Normal"), "jc")
        assert jc == ("both" if "letter" in kind else None), (kind, face)


def test_the_university_letter_has_the_banner_and_the_lab_logo_in_the_footer(built):
    path = built["university-letter", "aptos"]
    assert path.name == "Forming Worlds University Letter (Aptos).dotx"
    with zipfile.ZipFile(path) as z:
        parts = {
            n: etree.fromstring(z.read(n))
            for n in z.namelist()
            if re.fullmatch(r"word/(header|footer)\d+\.xml", n)
        }
        rels = {
            n: z.read(n)
            for n in z.namelist()
            if re.fullmatch(r"word/_rels/(header|footer)\d+\.xml\.rels", n)
        }
    headers = [x for n, x in parts.items() if "header" in n and x.find(".//{*}blip") is not None]
    assert len(headers) == 1
    sender = headers[0].findall("w:p", NS)[-1]
    assert "".join(sender.itertext()) == f"{word.SENDER[0]}  ·  {word.SENDER[-1]}"
    assert (val(sender, "pStyle"), val(sender, "jc")) == ("Sender", "right")
    footers = [
        x for n, x in parts.items() if "footer" in n and x.find(".//w:fldSimple", NS) is not None
    ]
    assert len(footers) == 2 and all(f.find(".//{*}blip") is not None for f in footers)
    assert len(rels) == 3  # 1 header and 2 footers point at an image
