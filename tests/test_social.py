"""Social media cards: author line, texts and their places, crops, fades, limits and the spec."""

import json
import re
import runpy
import sys

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

from fwl_visual_language import assets_dir, contrast, ramp, social  # noqa: E402

INK, SIGNAL = ramp("ink"), ramp("signal")
AUTHORS = ["A One", "B Two", "C Three", "D Four", "E Five", "F Six"]
LOGO = Image.open(assets_dir() / "fwl-logo-white.png")


def rgb(hexv):
    return tuple(int(hexv[i : i + 2], 16) for i in (1, 3, 5))


def near(a, b, tol=6):
    return all(abs(x - y) <= tol for x, y in zip(a, b, strict=True))


def hexof(p):
    return "#{:02X}{:02X}{:02X}".format(*p[:3])


@pytest.fixture
def drawn(monkeypatch):
    """Record every text draw as (box, text, fill); the draw still happens."""
    calls = []
    real = ImageDraw.ImageDraw.text

    def spy(self, xy, text, fill=None, font=None, **kw):
        x0, y0, x1, y1 = font.getbbox(text)
        calls.append(((xy[0] + x0, xy[1] + y0, xy[0] + x1, xy[1] + y1), text, fill))
        return real(self, xy, text, fill=fill, font=font, **kw)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    return calls


def label_of(calls):
    return "".join(t for _, t, f in calls if f == SIGNAL["400"])


def logo_box(size, right, top, height):
    """Box of the logo for a card of ``size`` from its design place."""
    s = size / 1080
    h = round(height * s)
    w = round(LOGO.width * h / LOGO.height)
    x1 = size - round(right * s)
    return (x1 - w, round(top * s), x1, round(top * s) + h)


def has_white(im):
    """True when the image holds a near-white pixel (the white logo)."""
    px, (w, h) = im.convert("RGB").load(), im.size
    return any(min(px[x, y]) > 200 for x in range(w) for y in range(h))


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def fill_to(n, unit, measure):
    """Return the longest repeat of ``unit`` that ``measure`` breaks into ``n`` lines."""
    k = 1
    while len(measure(unit * (k + 1))) <= n:
        k += 1
    assert len(measure(unit * k)) == n
    return unit * k


def breaker(face, px, width):
    c = social._Card(1080)
    return lambda text: c.lines(text, c.font(face, px), width)


@pytest.fixture
def photo(tmp_path):
    """A white photo, 300 x 200, with a red left third and a blue right third."""
    im = Image.new("RGB", (300, 200), "white")
    im.paste((255, 0, 0), (0, 0, 100, 200))
    im.paste((0, 0, 255), (200, 0, 300, 200))
    path = tmp_path / "photo.png"
    im.save(path)
    return path


@pytest.fixture
def tall(tmp_path):
    """A portrait photo, 200 x 300, in 3 horizontal bands: red, green, blue."""
    im = Image.new("RGB", (200, 300), (0, 255, 0))
    im.paste((255, 0, 0), (0, 0, 200, 100))
    im.paste((0, 0, 255), (0, 200, 200, 300))
    path = tmp_path / "tall.png"
    im.save(path)
    return path


@pytest.fixture
def white(tmp_path):
    path = tmp_path / "white.png"
    Image.new("RGB", (600, 600), "white").save(path)
    return path


@pytest.fixture
def figure(tmp_path):
    path = tmp_path / "fig.png"
    Image.new("RGB", (400, 250), (200, 30, 30)).save(path)
    return path


@pytest.mark.parametrize(
    "authors, lab, expect",
    [
        (["A One"], [], "A One"),
        (["A One", "B Two"], [], "A One and B Two"),
        (AUTHORS[:3], ["B Two"], "A One, B Two and C Three"),
        (AUTHORS[:4], [], "A One, B Two, C Three and 1 co-author"),
        (AUTHORS, [], "A One, B Two, C Three and 3 co-authors"),
        (AUTHORS, ["A One", "E Five"], "A One, B Two, C Three and 3 co-authors, incl. E Five"),
        (
            AUTHORS,
            ["D Four", "F Six"],
            "A One, B Two, C Three and 3 co-authors, incl. D Four and F Six",
        ),
        (
            AUTHORS,
            ["D Four", "E Five", "F Six"],
            "A One, B Two, C Three and 3 co-authors, incl. D Four, E Five and F Six",
        ),
    ],
)
def test_the_author_line_names_every_lab_member(authors, lab, expect):
    assert social.author_line(authors, lab) == expect


def test_the_author_line_takes_the_shown_count():
    assert social.author_line(AUTHORS, ["B Two"], shown=1) == "A One and 5 co-authors, incl. B Two"


@pytest.mark.parametrize(
    "authors, lab, shown, match",
    [
        ([], [], 3, "at least 1 author"),
        (AUTHORS, [], 0, "at least 1 author"),
        (AUTHORS, "D Four", 3, "not one string"),
        (AUTHORS, ["D. Four"], 3, "not among the authors: D. Four"),
    ],
)
def test_the_author_line_refuses_bad_input(authors, lab, shown, match):
    with pytest.raises(ValueError, match=match):
        social.author_line(authors, lab, shown)


@pytest.mark.parametrize("size", [1080, 540])
def test_the_paper_card_texts_colours_and_places(tmp_path, photo, drawn, size):
    out = social.paper_card(
        tmp_path / "p.png", photo, "A short title", AUTHORS, ["E Five"], size=size
    )
    im = Image.open(out)
    assert im.size == (size, size) and im.mode == "RGB"
    texts = {t: (box, f) for box, t, f in drawn}
    assert label_of(drawn) == "NEW PAPER"
    assert texts["A short title"][1] == INK["0"]
    line = "A One, B Two, C Three and 3 co-authors, incl. E Five"
    assert texts[line][1] == INK["200"]
    assert texts["A short title"][0][1] < texts[line][0][1]
    logo = logo_box(size, 48, 40, 60)
    for box, _, _ in drawn:
        assert 0 <= box[0] and box[2] <= size and box[3] <= size
        assert not overlaps(box, logo)
    # the white logo sits in its box over the faded blue third
    assert has_white(im.crop(logo))


def test_the_paper_card_crop_spans_the_photo_centre(tmp_path, photo):
    im = Image.open(social.paper_card(tmp_path / "p.png", photo, "T", ["A"])).convert("RGB")
    # the 200 px square around the centre spans photo x 50 to 250: edges at card x 270 and 810
    expect = [(5, (255, 0, 0)), (265, (255, 0, 0)), (275, (255, 255, 255))]
    expect += [(805, (255, 255, 255)), (815, (0, 0, 255))]
    for x, colour in expect:
        assert near(im.getpixel((x, 450)), colour, 3), x


@pytest.mark.parametrize(
    "fy, edge, above, below",
    [
        (0, 540, (255, 0, 0), (0, 255, 0)),
        (0.5, 270, (255, 0, 0), (0, 255, 0)),
        (1, 540, (0, 255, 0), (0, 0, 255)),
    ],
)
def test_a_portrait_photo_crops_along_the_focus(tmp_path, tall, fy, edge, above, below):
    out = social.member_card(tmp_path / "m.png", tall, "N", [], focus=(0.5, fy))
    im = Image.open(out).convert("RGB")
    assert near(im.getpixel((540, edge - 5)), above, 3)
    assert near(im.getpixel((540, edge + 5)), below, 3)


def test_a_landscape_photo_crops_along_the_focus(tmp_path, photo):
    left = Image.open(social.paper_card(tmp_path / "l.png", photo, "T", ["A"], focus=(0, 0.5)))
    right = Image.open(social.paper_card(tmp_path / "r.png", photo, "T", ["A"], focus=(1, 0.5)))
    assert near(left.getpixel((100, 400)), (255, 0, 0), 2)
    assert near(right.getpixel((1000, 400)), (0, 0, 255), 2)


def test_the_exif_orientation_is_applied(tmp_path):
    # stored 300 x 200 with red left and blue right; orientation 6 shows it turned: red on top
    im = Image.new("RGB", (300, 200), "white")
    im.paste((255, 0, 0), (0, 0, 100, 200))
    im.paste((0, 0, 255), (200, 0, 300, 200))
    exif = Image.Exif()
    exif[0x0112] = 6
    path = tmp_path / "rot.jpg"
    im.save(path, exif=exif, quality=95)
    out = social.member_card(tmp_path / "m.png", path, "N", [], focus=(0.5, 0))
    assert near(Image.open(out).convert("RGB").getpixel((540, 260)), (255, 0, 0), 25)


def test_the_text_sits_on_a_dark_ground_on_a_white_photo(tmp_path, white, drawn):
    title = (
        "Evolutionary pathways toward survival of a thick atmosphere on the lava world TOI-561 b"
    )
    out = social.paper_card(tmp_path / "p.png", white, title, AUTHORS, ["E Five"])
    im = Image.open(out).convert("RGB")
    top = round(min(box[1] for box, _, f in drawn if f == SIGNAL["400"]))
    ground = hexof(im.getpixel((20, top)))
    assert contrast(SIGNAL["400"], ground) >= 4.5
    assert contrast(INK["0"], ground) >= 12
    # the fade darkens without a step back towards light, from its start to the foot
    column = [sum(im.getpixel((20, y))) for y in range(top - 200, 1080)]
    assert all(b <= a + 1 for a, b in zip(column, column[1:], strict=False))
    assert column[0] > 700
    # the top fade keeps the corner darker than the white middle
    assert sum(im.getpixel((20, 2))) < sum(im.getpixel((20, 400))) - 200


def test_the_glance_card(tmp_path, drawn):
    social.glance_card(tmp_path / "g.png", "Some words here.", "arXiv:0000.00000")
    assert label_of(drawn) == "AT A GLANCE"
    texts = {t: f for _, t, f in drawn}
    assert texts["Some words here."] == INK["100"] and texts["arXiv:0000.00000"] == INK["400"]
    im = Image.open(tmp_path / "g.png")
    assert near(im.getpixel((5, 5)), rgb(INK["950"]), 1)
    assert has_white(im.crop(logo_box(1080, 64, 968, 60)))


@pytest.mark.parametrize(
    "card, face, px, width, n",
    [
        ("glance", "Regular", 41, 1080 - 128, 15),
        ("cover", "Light", 86, 1080 - 128, 6),
        ("paper", "SemiBold", 40, 1080 - 96, 3),
        ("figure", "SemiBold", 46, 1080 - 96, 2),
    ],
)
def test_each_text_limit_holds_n_lines_and_refuses_one_more(
    tmp_path, photo, figure, card, face, px, width, n
):
    exact = fill_to(n, "word ", breaker(face, px, width))
    longer = exact + "word " * 8
    make = {
        "glance": lambda t, o: social.glance_card(o, t, "ref"),
        "cover": lambda t, o: social.cover_card(o, t, "Lead", "ref"),
        "paper": lambda t, o: social.paper_card(o, photo, t, ["A"]),
        "figure": lambda t, o: social.figure_card(o, figure, t, "Source", "ref"),
    }[card]
    make(exact, tmp_path / "ok.png")
    with pytest.raises(ValueError, match="holds"):
        make(longer, tmp_path / "no.png")


def test_the_author_line_holds_2_lines(tmp_path, photo):
    names = [f"Author{i:02d} Surname{i:02d}" for i in range(40)]
    with pytest.raises(ValueError, match="author line 2"):
        social.paper_card(tmp_path / "p.png", photo, "T", names, names[3:])


@pytest.mark.parametrize(
    "make, match",
    [
        (lambda o, f, p: social.glance_card(o, "t", "ref " * 30), "holds 1"),
        (lambda o, f, p: social.cover_card(o, "Q", "Lead", "ref " * 30), "holds 1"),
        (lambda o, f, p: social.cover_card(o, "Q", "Lead " * 20, "ref"), "holds 1"),
        (lambda o, f, p: social.figure_card(o, f, "H", "Source " * 30, "ref"), "holds 1"),
        (lambda o, f, p: social.figure_card(o, f, "H", "Source", "ref " * 30), "holds 1"),
        (lambda o, f, p: social.glance_card(o, "t", "ref", label="label " * 20), "label is wider"),
        (
            lambda o, f, p: social.event_card(o, "E", "W", "H", [("A", "detail " * 20)]),
            "wider than its",
        ),
        (lambda o, f, p: social.event_card(o, "Event " * 10, "W", "H", []), "holds 1"),
        (lambda o, f, p: social.event_card(o, "E", "W " * 60, "H", []), "holds 1"),
        (lambda o, f, p: social.event_card(o, "E", "W", "H", [("A", "1")] * 8), "7 entries"),
        (lambda o, f, p: social.member_card(o, p, "Name " * 20, []), "holds 1"),
        (lambda o, f, p: social.member_card(o, p, "N", ["1", "2", "3"]), "up to 2 lines"),
        (lambda o, f, p: social.member_card(o, p, "N", "Role"), "up to 2 lines"),
        (lambda o, f, p: social.glance_card(o, "   ", "ref"), "empty"),
        (lambda o, f, p: social.glance_card(o, "x" * 200, "ref"), "wider than the card"),
    ],
)
def test_texts_that_do_not_fit_are_refused(tmp_path, figure, photo, make, match):
    with pytest.raises(ValueError, match=match):
        make(tmp_path / "x.png", figure, photo)


def test_the_figure_card(tmp_path, figure, drawn):
    im = Image.open(social.figure_card(tmp_path / "f.png", figure, "A headline", "Source", "ref"))
    assert near(im.getpixel((540, 450)), (200, 30, 30), 3)
    assert near(im.getpixel((52, 450)), (255, 255, 255), 2)
    texts = {t: f for _, t, f in drawn}
    assert texts["A headline"] == INK["0"] and texts["Source"] == INK["300"]
    logo = logo_box(1080, 48, 984, 52)
    assert not any(overlaps(b, logo) for b, _, _ in drawn)
    assert has_white(im.crop(logo))


def test_the_figure_card_refuses_a_tall_figure(tmp_path):
    tall = tmp_path / "tall.png"
    Image.new("RGB", (100, 300), "white").save(tall)
    with pytest.raises(ValueError, match="px of height"):
        social.figure_card(tmp_path / "f.png", tall, "Headline", "Source", "ref")


def test_the_cover_card(tmp_path, drawn):
    social.cover_card(tmp_path / "c.png", "Can a world keep its air?", "Led by A", "ref")
    assert label_of(drawn) == "NEW PAPER"
    texts = [t for _, t, f in drawn if f == INK["0"]]
    assert " ".join(texts) == "Can a world keep its air?"
    assert {t for _, t, _ in drawn} >= {"Led by A", "ref"}


def test_the_member_card(tmp_path, photo, drawn):
    im = Image.open(social.member_card(tmp_path / "m.png", photo, "A Name", ["Role", "Path"]))
    assert label_of(drawn) == "MEET THE LAB"
    texts = {t: (b, f) for b, t, f in drawn}
    assert texts["A Name"][1] == INK["0"] and texts["Role"][1] == INK["200"]
    assert texts["A Name"][0][1] < texts["Role"][0][1] < texts["Path"][0][1]
    # ink-950 at alpha 235 over the white middle of the photo
    assert near(im.getpixel((540, 1079)), (21, 23, 25), 2)


@pytest.mark.parametrize("size", [1080, 540])
def test_the_event_card_right_aligns_every_detail(tmp_path, drawn, size):
    entries = [("A One", "poster 1"), ("B Two", "poster 22"), ("C Three", "talk")]
    social.event_card(tmp_path / "e.png", "Event", "Place", "3 posters", entries, size=size)
    ends = {t: b[2] for b, t, _ in drawn}
    edge = size - round(64 * size / 1080)
    assert all(abs(ends[t] - edge) <= 3 for t in ("poster 1", "poster 22", "talk"))
    assert label_of(drawn) == "AT THE CONFERENCE"


def test_the_highlight_cover_crops_the_box_darkens_it_and_centres_the_label(tmp_path, drawn):
    art = tmp_path / "art.png"
    im = Image.new("RGB", (400, 300), (0, 255, 0))
    im.paste((255, 255, 255), (100, 50, 300, 250))
    im.save(art)
    out = Image.open(social.highlight_card(tmp_path / "h.png", art, (100, 50, 200), "Results"))
    over = tuple(round(255 * (1 - 120 / 255) + c * 120 / 255) for c in rgb(INK["950"]))
    assert near(out.getpixel((5, 5)), over, 2)
    ((box, text, fill),) = drawn
    assert text == "Results" and fill == INK["0"]
    assert abs((box[0] + box[2]) / 2 - 540) <= 3 and abs((box[1] + box[3]) / 2 - 540) <= 40


@pytest.mark.parametrize("box", [(200, 0, 300), (0, 150, 200), (-1, 0, 10), (0, -1, 10), (0, 0, 0)])
def test_the_highlight_box_must_lie_inside_the_artwork(tmp_path, box):
    art = tmp_path / "art.png"
    Image.new("RGB", (400, 300)).save(art)
    with pytest.raises(ValueError, match="not inside the artwork"):
        social.highlight_card(tmp_path / "h.png", art, box, "Results")


@pytest.mark.parametrize("box", [(100, 0, 300), (0, 0, 300)])
def test_a_box_on_the_artwork_edge_is_accepted(tmp_path, box):
    art = tmp_path / "art.png"
    Image.new("RGB", (400, 300)).save(art)
    assert social.highlight_card(tmp_path / "h.png", art, box, "Talks").is_file()


def test_the_highlight_label_holds_2_lines(tmp_path):
    art = tmp_path / "art.png"
    Image.new("RGB", (400, 300)).save(art)
    with pytest.raises(ValueError, match="cover holds 2"):
        social.highlight_card(
            tmp_path / "h.png", art, (0, 0, 300), "Many words in this very long label"
        )


def test_render_reads_a_spec_with_paths_relative_to_its_base(tmp_path, photo, figure):
    spec = {
        "base": str(photo.parent),
        "cards": [
            {"card": "paper", "file": "one", "photo": photo.name, "title": "T", "authors": ["A"]},
            {
                "card": "event",
                "file": "two",
                "name": "E",
                "when": "W",
                "heading": "H",
                "entries": [["A", "1"]],
            },
            {
                "card": "highlight",
                "file": "three",
                "art": photo.name,
                "box": [0, 0, 200],
                "label": "Talks",
            },
            {
                "card": "figure",
                "file": "four",
                "figure": figure.name,
                "headline": "H",
                "source": "S",
                "ref": "r",
            },
        ],
    }
    written = social.render(spec, tmp_path / "out")
    assert [p.name for p in written] == ["one.png", "two.png", "three.png", "four.png"]
    assert all(p.is_file() for p in written)


GOOD = {"card": "glance", "file": "a", "text": "t", "ref": "r"}


@pytest.mark.parametrize(
    "spec, match",
    [
        ([GOOD], "'cards' list"),
        ({}, "'cards' list"),
        ({"cards": [GOOD, dict(GOOD, file="A")]}, "share the file name"),
        ({"cards": [GOOD, {"card": "poster", "file": "b"}]}, "unknown card"),
        ({"cards": [GOOD, {"file": "b"}]}, "needs 'card' and 'file'"),
        ({"cards": [GOOD, dict(GOOD, file="../b")]}, "plain name"),
        ({"cards": [GOOD, dict(GOOD, file="b/c")]}, "plain name"),
        ({"cards": [GOOD, dict(GOOD, file="b", colour="red")]}, "unknown keys: colour"),
        ({"cards": [GOOD, dict(GOOD, file="b", out="x")]}, "unknown keys: out"),
    ],
)
def test_render_checks_the_whole_spec_before_writing(tmp_path, spec, match):
    with pytest.raises(ValueError, match=match):
        social.render(spec, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_the_command_line_resolves_images_next_to_the_spec(tmp_path, photo, capsys):
    (tmp_path / "img").mkdir()
    photo.rename(tmp_path / "img" / "p.png")
    spec = tmp_path / "cards.json"
    card = {"card": "member", "file": "m", "photo": "p.png", "name": "N", "lines": ["R"]}
    spec.write_text(json.dumps({"base": "img", "cards": [card]}))
    assert social.main([str(spec), str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "m.png").is_file()
    assert "m.png" in capsys.readouterr().out


def test_the_command_line_reports_a_card_that_does_not_fit(tmp_path, capsys):
    spec = tmp_path / "cards.json"
    card = {"card": "glance", "file": "g", "text": "word " * 400, "ref": "r"}
    spec.write_text(json.dumps({"cards": [card]}))
    assert social.main([str(spec), str(tmp_path / "out")]) == 1
    assert "error:" in capsys.readouterr().err


def test_the_module_runs_as_a_script(tmp_path, monkeypatch):
    spec = tmp_path / "cards.json"
    spec.write_text(json.dumps({"cards": [GOOD]}))
    monkeypatch.setattr(sys, "argv", ["social", str(spec), str(tmp_path / "out")])
    with pytest.raises(SystemExit) as exit_:
        runpy.run_module("fwl_visual_language.social", run_name="__main__")
    assert exit_.value.code == 0
    assert (tmp_path / "out" / "a.png").is_file()


CAPTION = "Each dot is one model run; blue runs keep more than 0.1 bar of atmosphere."


def old_figure_card(out, figure, headline, source, ref):
    """The figure card as it was before captions, to compare the output pixel by pixel."""
    c = social._Card(1080)
    y = c.block((48, 48), headline, "SemiBold", 46, INK["0"], 1080 - 96, 1.12, 2)
    pad, top = 16, y + 22
    fig = social._open(figure)
    w = c.u(1080 - 96 - 2 * pad)
    h = round(fig.height * w / fig.width)
    fig = fig.resize((w, h), c.Image.LANCZOS)
    c.d.rounded_rectangle(
        (c.u(48), c.u(top), c.size - c.u(48), c.u(top) + h + c.u(2 * pad)), c.u(14), fill=INK["0"]
    )
    c.im.alpha_composite(fig, (c.u(48 + pad), c.u(top + pad)))
    bottom = c.u(top) + h + c.u(2 * pad)
    c.block((48, (bottom + c.u(22)) / c.s), source, "Regular", 28,
            INK["300"], 1080 - 96 - 130, 1, 1)  # fmt: skip
    c.block((48, 1080 - 76), ref, "mono", 26, INK["300"], 1080 - 96 - 130, 1, 1)
    c.logo((48, 1080 - 96), 52)
    return c.save(out)


def pixels(path):
    import numpy as np

    return np.asarray(Image.open(path).convert("RGB")).tolist()


def test_a_figure_card_without_caption_matches_the_card_before_captions(tmp_path, figure):
    args = (figure, "A headline over two words", "Source, Fig. 2", "arXiv:0000.00000")
    old = old_figure_card(tmp_path / "old.png", *args)
    new = social.figure_card(tmp_path / "new.png", *args)
    none = social.figure_card(tmp_path / "none.png", *args, caption=None)
    assert pixels(new) == pixels(old) == pixels(none)


def test_the_caption_sits_between_the_panel_and_the_source(tmp_path, figure, drawn):
    im = Image.open(
        social.figure_card(tmp_path / "f.png", figure, "Headline", "Source", "ref", caption=CAPTION)
    )
    boxes = {t: (b, f) for b, t, f in drawn}
    caption_rows = [(b, t) for b, t, f in drawn if f == INK["100"]]
    assert " ".join(t for _, t in caption_rows) == CAPTION and len(caption_rows) == 2
    (src_box, src_fill) = boxes["Source"]
    assert src_fill == INK["300"]
    assert caption_rows[-1][0][3] < src_box[1]  # the source is under the caption
    # the white panel ends 18 px above the first caption line's top (Geist's ascent gap aside)
    column = [im.getpixel((60, y))[:3] for y in range(1080)]
    panel_bottom = max(y for y, px in enumerate(column) if near(px, (255, 255, 255), 2))
    assert 18 <= caption_rows[0][0][1] - panel_bottom <= 18 + 12
    logo = logo_box(1080, 48, 984, 52)
    assert not any(overlaps(b, logo) for b, _, _ in drawn)
    assert src_box[3] < 1080 - 96  # the source stays above the logo row


def test_a_caption_of_5_lines_is_refused_and_never_shrinks(tmp_path):
    figure = tmp_path / "wide.png"
    # 575 px high on the card: it fits beside 4 caption lines (594 px) but not beside 5 (555 px)
    Image.new("RGB", (1000, 604), (200, 30, 30)).save(figure)
    exact = fill_to(4, "word ", breaker("Regular", 30, 1080 - 96))
    social.figure_card(tmp_path / "ok.png", figure, "H", "S", "ref", caption=exact)
    with pytest.raises(ValueError, match="holds 4"):
        social.figure_card(
            tmp_path / "no.png", figure, "H", "S", "ref", caption=exact + "word " * 8
        )


def test_a_figure_that_fits_without_a_caption_is_refused_with_one(tmp_path):
    tall = tmp_path / "tall.png"
    # 720 px high on the card: room 776 px without a caption, 672 px with 2 caption lines
    Image.new("RGB", (1000, 756), "white").save(tall)
    social.figure_card(tmp_path / "a.png", tall, "One headline line", "S", "ref")
    with pytest.raises(ValueError, match="px of height"):
        social.figure_card(
            tmp_path / "b.png", tall, "One headline line", "S", "ref", caption=CAPTION
        )


@pytest.mark.parametrize(
    "status, journal, expect",
    [
        (None, None, "arXiv:1"),
        (
            "accepted",
            "The Astrophysical Journal",
            "arXiv:1 · Accepted to The Astrophysical Journal",
        ),
        ("Submitted", "Icarus", "arXiv:1 · Submitted to Icarus"),
        ("published", "Nature", "arXiv:1 · Published in Nature"),
    ],
)
def test_the_reference_line_carries_the_status(status, journal, expect):
    assert social.ref_line("arXiv:1", status, journal) == expect


@pytest.mark.parametrize(
    "status, journal, match",
    [
        ("accepted", None, "needs a journal"),
        (None, "ApJ", "needs a journal"),
        ("in press", "ApJ", "unknown status"),
    ],
)
def test_the_reference_line_refuses_half_a_status(status, journal, match):
    with pytest.raises(ValueError, match=match):
        social.ref_line("arXiv:1", status, journal)


def test_cards_and_specs_take_status_and_journal(tmp_path, figure, drawn):
    spec = {
        "base": str(tmp_path),
        "cards": [
            {"card": "glance", "file": "g", "text": "T", "ref": "arXiv:1", "status": "accepted",
             "journal": "The Astrophysical Journal"},
            {"card": "cover", "file": "c", "question": "Q", "lead": "L", "ref": "arXiv:1",
             "status": "published", "journal": "Nature"},
            {"card": "figure", "file": "f", "figure": figure.name, "headline": "H", "source": "S",
             "ref": "arXiv:1", "status": "submitted", "journal": "Icarus"},
        ],
    }  # fmt: skip
    social.render(spec, tmp_path / "out")
    texts = {t for _, t, _ in drawn}
    assert {
        "arXiv:1 · Accepted to The Astrophysical Journal",
        "arXiv:1 · Published in Nature",
        "arXiv:1 · Submitted to Icarus",
    } <= texts


LONG_REF = "arXiv:2609.20155 · Accepted to The Astrophysical Journal"


@pytest.mark.parametrize(
    "make, nominal",
    [
        (lambda o, f, r: social.glance_card(o, "T", r), 28),
        (lambda o, f, r: social.cover_card(o, "Q", "L", r), 28),
        (lambda o, f, r: social.figure_card(o, f, "H", "S", r), 26),
    ],
)
def test_a_long_reference_shrinks_to_the_largest_size_that_fits(
    tmp_path, figure, monkeypatch, make, nominal
):
    sizes = []
    real = social._Card.block

    def spy(self, xy, text, face, px, *a):
        if face == "mono":
            sizes.append((text, px, a[1]))
        return real(self, xy, text, face, px, *a)

    monkeypatch.setattr(social._Card, "block", spy)
    make(tmp_path / "short.png", figure, "arXiv:1")
    make(tmp_path / "long.png", figure, LONG_REF)
    (short, short_px, _), (long, long_px, width) = sizes
    assert short_px == nominal and long == LONG_REF and long_px < nominal
    c = social._Card(1080)
    assert c.d.textlength(LONG_REF, font=c.font("mono", long_px)) <= c.u(width)
    assert c.d.textlength(LONG_REF, font=c.font("mono", long_px + 1)) > c.u(width)
    with pytest.raises(ValueError, match="holds 1 line even at 20 px"):
        make(tmp_path / "no.png", figure, LONG_REF * 2)


@pytest.mark.parametrize(
    "make, logo",
    [
        (lambda o, f: social.glance_card(o, "T", LONG_REF), logo_box(1080, 64, 968, 60)),
        (lambda o, f: social.cover_card(o, "Q", "L", LONG_REF), logo_box(1080, 64, 956, 60)),
        (lambda o, f: social.figure_card(o, f, "H", "S", LONG_REF), logo_box(1080, 48, 984, 52)),
    ],
)
def test_a_shrunk_reference_ends_32_px_before_the_logo(tmp_path, figure, drawn, make, logo):
    make(tmp_path / "x.png", figure)
    (box,) = [b for b, t, _ in drawn if t == LONG_REF]
    assert box[2] <= logo[0] - 32 + 1 and not overlaps(box, logo)


@pytest.mark.parametrize(
    "make, chars",
    [
        (
            lambda o, f: social.glance_card(o, "Efficiency η of 10⁻² holds", "ref"),
            "η (U+03B7), ⁻ (U+207B)",
        ),
        (
            lambda o, f: social.figure_card(o, f, "H", "S", "ref", caption="η sets the escape"),
            "η (U+03B7)",
        ),
        (lambda o, f: social.glance_card(o, "T", "ref", label="η label"), "Η (U+0397)"),
        (lambda o, f: social.highlight_card(o, f, (0, 0, 100), "η"), "η (U+03B7)"),
        (lambda o, f: social.event_card(o, "E", "W", "H", [("A", "η 1")]), "η (U+03B7)"),
    ],
)
def test_a_missing_glyph_gives_a_warning(tmp_path, figure, make, chars):
    with pytest.warns(UserWarning, match=r"has no glyph for " + re.escape(chars)):
        make(tmp_path / "x.png", figure)


def test_subscript_digits_and_the_middle_dot_give_no_warning(tmp_path, figure, recwarn):
    # a line break or a tab in a text is not drawn, so it needs no glyph
    social.glance_card(tmp_path / "g.png", "H₂O, S₂\nand SO₂\toutgas.", "arXiv:1 · Accepted to ApJ")
    social.figure_card(tmp_path / "f.png", figure, "S₂ builds up", "S", "ref", caption="H₂ and CO₂")
    assert [w for w in recwarn if "no glyph" in str(w.message)] == []


def test_render_warns_for_a_missing_glyph_in_a_spec(tmp_path):
    spec = {"cards": [{"card": "glance", "file": "g", "text": "η matters", "ref": "r"}]}
    with pytest.warns(UserWarning, match="Geist-Regular has no glyph for η"):
        social.render(spec, tmp_path)


@pytest.mark.parametrize("ref", ["", "   "])
def test_an_empty_reference_is_refused(tmp_path, ref):
    with pytest.raises(ValueError, match="empty"):
        social.glance_card(tmp_path / "g.png", "T", ref)
