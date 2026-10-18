"""Slide masters (.pptx for PowerPoint, Google Slides and the Keynote source)."""

import re
import runpy
import sys
import zipfile

import pytest

pytest.importorskip("pptx")
from PIL import Image  # noqa: E402
from pptx import Presentation  # noqa: E402

import fwl_visual_language as fvl  # noqa: E402
from fwl_visual_language import slides  # noqa: E402

CONTENT = ("Figure", "Figure, large", "Two figures", "Team")
EMU = 12700


@pytest.fixture(scope="module")
def figure(tmp_path_factory):
    path = tmp_path_factory.mktemp("img") / "fig.png"
    Image.new("RGB", (142, 92), (255, 255, 255)).save(path)
    return path


@pytest.fixture(scope="module")
def built(tmp_path_factory, figure):
    d = tmp_path_factory.mktemp("slides")
    return {
        "pptx": slides.build_slides(d / "a.pptx", figure=figure),
        "keynote": slides.build_slides(d / "k.pptx", keynote=True, figure=figure),
        "plain": slides.build_slides(d / "p.pptx"),
    }


def layout_xml(path):
    with zipfile.ZipFile(path) as z:
        names = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)),
        )
        return [z.read(n).decode() for n in names]


def test_layouts_have_the_lab_names_and_sizes(built):
    for key, (w, h) in {"pptx": (960, 540), "keynote": (1920, 1080)}.items():
        prs = Presentation(built[key])
        assert [lay.name for lay in prs.slide_layouts] == list(slides.LAYOUTS)
        assert (prs.slide_width, prs.slide_height) == (w * EMU, h * EMU)
        assert len(prs.slides) == len(slides.LAYOUTS)
        assert [s.slide_layout.name for s in prs.slides] == list(slides.LAYOUTS)


def test_figure_placeholders_only_in_the_powerpoint_file(built):
    def figure_boxes(path):
        prs = Presentation(path)
        return {
            lay.name: sorted(
                ph.placeholder_format.idx
                for ph in lay.placeholders
                if ph.placeholder_format.type == 7
            )  # OBJECT: a content placeholder
            for lay in prs.slide_layouts
        }

    pptx = figure_boxes(built["pptx"])
    assert {k: v for k, v in pptx.items() if v} == {
        "Figure": [10],
        "Figure, large": [10],
        "Two figures": [10, 11],
    }
    assert not any(figure_boxes(built["keynote"]).values())


@pytest.mark.parametrize("key,scale", [("pptx", 0.5), ("keynote", 1.0)])
def test_reference_boxes_sit_in_both_bottom_corners_and_grow_upward(built, key, scale):
    prs = Presentation(built[key])
    for lay in prs.slide_layouts:
        phs = {ph.placeholder_format.idx: ph for ph in lay.placeholders}
        assert (20 in phs and 21 in phs) == (lay.name in CONTENT), lay.name
        if lay.name not in CONTENT:
            continue
        left, right = phs[20], phs[21]
        for ph, align in ((left, "l"), (right, "r")):
            xml = ph._element.xml
            assert 'anchor="b"' in xml  # bottom anchored: a stack grows upward
            assert f'algn="{align}"' in xml
            assert f'sz="{round(slides.REF_PT * scale * 100)}"' in xml
            assert ph.top + ph.height == round((1080 - slides.EDGE) * scale * EMU)
        assert left.left == round(slides.EDGE * scale * EMU)
        assert right.left + right.width == round((1920 - slides.EDGE) * scale * EMU)
        assert left.left + left.width < right.left  # the corners do not overlap


def test_only_lab_fonts_and_token_colours(built):
    allowed = {h[1:] for name in ("ink", "signal", "magma") for h in fvl.ramp(name).values()}
    allowed |= {h[1:] for _, h in fvl.palette("dark")} | {"FFFFFF", "000000"}
    for key in ("pptx", "keynote"):
        for xml in layout_xml(built[key]):
            assert set(re.findall(r'typeface="([^"]+)"', xml)) <= {
                "Geist",
                "Geist Light",
                "Geist Medium",
                "Geist Mono",
            }
            assert set(re.findall(r'srgbClr val="([0-9A-F]{6})"', xml)) <= allowed


def test_every_layout_has_a_plain_ink_ground_and_no_background_picture(built):
    for key in ("pptx", "keynote", "plain"):
        for name, xml in zip(slides.LAYOUTS, layout_xml(built[key]), strict=True):
            ground = xml.split("</p:bg>")[0]
            assert "<a:blipFill" not in ground, (key, name)
            step = "980" if name == "Statement" else "950"
            assert f'<a:srgbClr val="{slides.INK[step]}"/>' in ground, (key, name)
            assert "Garlick" not in xml


def test_letter_spacing_scales_with_the_slide(built):
    for key, spc in (("pptx", "300"), ("keynote", "600")):
        title = layout_xml(built[key])[0]
        assert f'spc="{spc}"' in title


def test_theme_has_the_lab_colour_and_font_schemes(built):
    with zipfile.ZipFile(built["pptx"]) as z:
        theme = z.read("ppt/theme/theme1.xml").decode()
    assert '<a:clrScheme name="Forming Worlds">' in theme
    accent1 = re.search(r"<a:accent1><a:srgbClr val=\"(\w+)\"", theme).group(1)
    assert accent1 == fvl.ramp("magma")["400"][1:]
    assert re.search(r'<a:majorFont><a:latin typeface="Geist Light"', theme)
    assert re.search(r'<a:minorFont><a:latin typeface="Geist"', theme)


def test_sample_figures_fit_their_boxes(built):
    for key, scale in (("pptx", 0.5), ("keynote", 1.0)):
        prs = Presentation(built[key])
        for s in prs.slides:
            pics = [sh for sh in s.shapes if sh.shape_type == 13]
            boxes = [b for (n, _), b in slides.BOX.items() if n == s.slide_layout.name]
            assert len(pics) == len(boxes), s.slide_layout.name
            for pic, (x, y, w, h) in zip(sorted(pics, key=lambda p: p.left), boxes, strict=True):
                assert x * scale * EMU - 2 <= pic.left
                assert pic.left + pic.width <= (x + w) * scale * EMU + 2
                assert y * scale * EMU - 2 <= pic.top
                assert pic.top + pic.height <= (y + h) * scale * EMU + 2
            # a sample figure replaces the empty figure box on its slide
            if boxes:
                assert not [ph for ph in s.placeholders if ph.placeholder_format.idx in (10, 11)]


def test_samples_have_no_personal_content(built):
    prs = Presentation(built["pptx"])
    text = " ".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    text += " ".join(
        sh.text_frame.text for lay in prs.slide_layouts for sh in lay.shapes if sh.has_text_frame
    )
    assert "SPEAKER NAME" in text and "Venue, city" in text
    assert not re.search(r"Tim|Leuven|TIM LICHTENBERG", text)


def test_more_layouts_than_the_base_template_has_are_refused(tmp_path, monkeypatch):
    real = slides._layouts
    monkeypatch.setattr(slides, "_layouts", lambda *a, **k: real(*a, **k) * 2)
    with pytest.raises(RuntimeError, match="expected 20 layouts in the base template, got 11"):
        slides.build_slides(tmp_path / "x.pptx")


def test_command_line_and_module_run(tmp_path, capsys, monkeypatch, figure):
    slides.main([str(tmp_path / "a.pptx"), "--keynote", "--figure", str(figure)])
    assert capsys.readouterr().out.strip() == str(tmp_path / "a.pptx")
    assert Presentation(tmp_path / "a.pptx").slide_width == 1920 * EMU
    monkeypatch.setattr(sys, "argv", ["fwl_visual_language.slides", str(tmp_path / "b.pptx")])
    monkeypatch.delitem(sys.modules, "fwl_visual_language.slides")
    runpy.run_module("fwl_visual_language.slides", run_name="__main__")
    assert (tmp_path / "b.pptx").is_file()
