"""Social media cards: author line, card layout, text limits and the JSON spec."""

import json
import runpy
import sys

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from fwl_visual_language import ramp, social  # noqa: E402

INK, SIGNAL = ramp("ink"), ramp("signal")
AUTHORS = ["A One", "B Two", "C Three", "D Four", "E Five", "F Six"]


def rgb(hexv):
    return tuple(int(hexv[i : i + 2], 16) for i in (1, 3, 5))


def near(a, b, tol=6):
    return all(abs(x - y) <= tol for x, y in zip(a, b, strict=True))


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


@pytest.mark.parametrize("authors, shown", [([], 3), (AUTHORS, 0)])
def test_the_author_line_refuses_no_authors(authors, shown):
    with pytest.raises(ValueError, match="at least 1 author"):
        social.author_line(authors, [], shown)


def test_the_paper_card_has_the_photo_the_fades_and_the_label(tmp_path, photo):
    out = social.paper_card(tmp_path / "p.png", photo, "A short title", AUTHORS, ["E Five"])
    im = Image.open(out).convert("RGB")
    assert im.size == (1080, 1080)
    # the 200 px square around the centre spans photo x 50 to 250: red, white, blue
    assert near(im.getpixel((540, 400)), (255, 255, 255), 2)
    assert near(im.getpixel((5, 400)), (255, 0, 0), 2)
    assert near(im.getpixel((1075, 480)), (0, 0, 255), 2)
    assert near(im.getpixel((540, 1079)), rgb(INK["950"]), 8)
    assert im.getpixel((540, 2))[0] < 120
    labels = [im.getpixel((x, y)) for x in range(48, 200) for y in range(700, 1000)]
    assert any(near(p, rgb(SIGNAL["400"]), 30) for p in labels)


def test_the_photo_crop_follows_the_focus(tmp_path, photo):
    left = Image.open(social.paper_card(tmp_path / "l.png", photo, "T", ["A"], focus=(0, 0.5)))
    right = Image.open(social.paper_card(tmp_path / "r.png", photo, "T", ["A"], focus=(1, 0.5)))
    assert near(left.convert("RGB").getpixel((100, 400)), (255, 0, 0), 2)
    assert near(right.convert("RGB").getpixel((1000, 400)), (0, 0, 255), 2)


def test_the_paper_card_refuses_a_long_title(tmp_path, photo):
    with pytest.raises(ValueError, match="3 lines"):
        social.paper_card(tmp_path / "p.png", photo, "word " * 60, AUTHORS)


def test_a_word_wider_than_the_card_is_refused(tmp_path):
    with pytest.raises(ValueError, match="wider than the card"):
        social.glance_card(tmp_path / "g.png", "x" * 200, "ref")


def test_the_glance_card_holds_15_lines(tmp_path):
    out = social.glance_card(tmp_path / "g.png", "word " * 100, "arXiv:0000.00000")
    im = Image.open(out).convert("RGB")
    assert near(im.getpixel((5, 5)), rgb(INK["950"]), 1)
    with pytest.raises(ValueError, match="the card holds 15"):
        social.glance_card(tmp_path / "g2.png", "word " * 400, "ref")


def test_the_figure_card_sets_the_figure_on_a_white_panel(tmp_path, figure):
    im = Image.open(
        social.figure_card(tmp_path / "f.png", figure, "A headline", "Source", "ref")
    ).convert("RGB")
    assert near(im.getpixel((540, 450)), (200, 30, 30), 3)
    assert near(im.getpixel((52, 450)), (255, 255, 255), 2)


def test_the_figure_card_refuses_a_tall_figure(tmp_path):
    tall = tmp_path / "tall.png"
    Image.new("RGB", (100, 300), "white").save(tall)
    with pytest.raises(ValueError, match="px of height"):
        social.figure_card(tmp_path / "f.png", tall, "Headline", "Source", "ref")


def test_the_cover_card_and_its_limits(tmp_path):
    im = Image.open(
        social.cover_card(tmp_path / "c.png", "Can a world keep its air?", "Led by A", "ref")
    )
    assert im.size == (1080, 1080)
    with pytest.raises(ValueError, match="the card holds 6"):
        social.cover_card(tmp_path / "c2.png", "word " * 80, "Led by A", "ref")


def test_the_member_card_and_its_limits(tmp_path, photo):
    im = Image.open(
        social.member_card(tmp_path / "m.png", photo, "A Name", ["Role", "Path"])
    ).convert("RGB")
    assert near(im.getpixel((540, 1079)), rgb(INK["950"]), 8)
    with pytest.raises(ValueError, match="2 lines under the name"):
        social.member_card(tmp_path / "m2.png", photo, "A Name", ["1", "2", "3"])


def test_the_event_card_right_aligns_the_details(tmp_path):
    entries = [("A One", "poster 1"), ("B Two", "poster 22")]
    im = Image.open(
        social.event_card(tmp_path / "e.png", "Event", "Place", "2 posters", entries)
    ).convert("RGB")
    row = [im.getpixel((x, 392 + 20)) for x in range(900, 1016)]
    assert any(p[0] > 100 for p in row)
    assert all(p[0] < 30 for p in [im.getpixel((x, 412)) for x in range(1017, 1080)])
    with pytest.raises(ValueError, match="7 entries"):
        social.event_card(tmp_path / "e2.png", "Event", "Place", "Many", [("A", "1")] * 8)


def test_the_highlight_cover_darkens_the_detail_and_centres_the_label(tmp_path):
    art = tmp_path / "art.png"
    Image.new("RGB", (400, 300), (255, 255, 255)).save(art)
    im = Image.open(social.highlight_card(tmp_path / "h.png", art, (0, 0, 300), "Results")).convert(
        "RGB"
    )
    corner = im.getpixel((5, 5))
    assert 120 < corner[0] < 160
    centre = [im.getpixel((x, 540)) for x in range(300, 780)]
    assert any(near(p, (255, 255, 255), 3) for p in centre)
    for box in [(200, 0, 300), (-1, 0, 10), (0, 0, 0)]:
        with pytest.raises(ValueError, match="not inside the artwork"):
            social.highlight_card(tmp_path / "h2.png", art, box, "Results")
    with pytest.raises(ValueError, match="cover holds 2"):
        social.highlight_card(
            tmp_path / "h3.png",
            art,
            (0, 0, 300),
            "Many words in this very long label for one cover",
        )


def test_a_smaller_size_scales_the_whole_card(tmp_path, photo):
    im = Image.open(social.paper_card(tmp_path / "s.png", photo, "Title", AUTHORS, size=540))
    assert im.size == (540, 540)


def test_render_reads_a_spec_with_paths_relative_to_its_base(tmp_path, photo):
    spec = {
        "base": str(photo.parent),
        "cards": [
            {
                "card": "paper",
                "file": "one",
                "photo": photo.name,
                "title": "T",
                "authors": ["A"],
                "focus": [0.5, 0.5],
            },
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
        ],
    }
    written = social.render(spec, tmp_path / "out")
    assert [p.name for p in written] == ["one.png", "two.png", "three.png"]
    assert all(p.is_file() for p in written)


@pytest.mark.parametrize(
    "cards, match",
    [
        ([{"card": "glance", "file": "a", "text": "t", "ref": "r"}] * 2, "share a file name"),
        ([{"card": "poster", "file": "a"}], "unknown card"),
    ],
)
def test_render_refuses_a_bad_spec(tmp_path, cards, match):
    with pytest.raises(ValueError, match=match):
        social.render({"cards": cards}, tmp_path)


def test_the_command_line_resolves_images_next_to_the_spec(tmp_path, photo, capsys):
    spec = tmp_path / "cards.json"
    spec.write_text(
        json.dumps(
            {
                "cards": [
                    {
                        "card": "member",
                        "file": "m",
                        "photo": photo.name,
                        "name": "N",
                        "lines": ["R"],
                    }
                ]
            }
        )
    )
    assert social.main([str(spec), str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "m.png").is_file()
    assert "m.png" in capsys.readouterr().out


def test_the_module_runs_as_a_script(tmp_path, monkeypatch):
    spec = tmp_path / "cards.json"
    spec.write_text(
        json.dumps({"cards": [{"card": "glance", "file": "g", "text": "t", "ref": "r"}]})
    )
    monkeypatch.setattr(sys, "argv", ["social", str(spec), str(tmp_path / "out")])
    with pytest.raises(SystemExit) as exit_:
        runpy.run_module("fwl_visual_language.social", run_name="__main__")
    assert exit_.value.code == 0
    assert (tmp_path / "out" / "g.png").is_file()
