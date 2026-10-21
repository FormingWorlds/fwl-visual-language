"""Social media cards in the lab look: ink, Geist, signal-blue labels and the lab logo.

Each card is a square PNG, 1080 px by default, for Bluesky, Mastodon, Instagram and
LinkedIn. The cards are:

- ``paper``: the first author's photo with the paper title and an author line
  that names every lab member;
- ``glance``: the short plain-language summary of a paper;
- ``figure``: a figure with a headline, an optional caption that says how to read it,
  and its source;
- ``cover``: the question a paper answers, as the first slide of a carousel;
- ``member``: a member intro over the member's photo;
- ``event``: a conference card with the lab contributions;
- ``highlight``: an Instagram Story Highlight cover, from a detail of an artwork.

The cards sit on the ink ground, or on a photo or artwork darkened towards ink.
Photos and artwork come from the caller. Every text is measured: a text that does
not fit its card raises ``ValueError`` instead of running off the card or under
the logo; only the 1-line reference in Geist Mono shrinks, down to 20 px, to fit.
A character that Geist has no glyph for (for example η or a superscript minus)
draws as a blank box, so drawing one gives a warning. Run
``python -m fwl_visual_language.social SPEC.json DIR`` to render the cards that a
JSON file lists.
"""

import argparse
import json
import warnings
from pathlib import Path

from . import assets_dir, fonts_dir, ramp

__all__ = [
    "CARDS",
    "author_line",
    "cover_card",
    "event_card",
    "figure_card",
    "glance_card",
    "highlight_card",
    "member_card",
    "paper_card",
    "ref_line",
    "render",
]

SIZE = 1080
INK = ramp("ink")
SIGNAL = ramp("signal")
MARGIN = 48
MONO_MIN = 20  # smallest px of a reference line that shrinks to fit
CAPTION_PX, CAPTION_LEAD, CAPTION_LINES = 30, 1.3, 4
STATUS = {"submitted": "Submitted to", "accepted": "Accepted to", "published": "Published in"}
_CMAPS = {}
_DRAWING = []  # the file stem of the card that render() draws, for its warnings


def ref_line(ref, status=None, journal=None):
    """Return the reference line, with the publication status when one is given.

    Parameters
    ----------
    ref : str
        The reference, for example ``arXiv:2609.20155``.
    status : str, optional
        ``submitted``, ``accepted`` or ``published``.
    journal : str, optional
        The journal in full, for example ``The Astrophysical Journal``.

    Returns
    -------
    str
        ``ref``, or ``"arXiv:2609.20155 · Accepted to The Astrophysical Journal"``.

    Raises
    ------
    ValueError
        If ``ref`` is not a text or is empty, only one of ``status`` and
        ``journal`` is given, the status is not one of the 3, or the journal is
        blank. A status and a journal that are both ``None`` or empty mean no
        status.
    """
    if not isinstance(ref, str):
        raise ValueError(f"the reference must be a text, not {ref!r}")
    if not ref.strip():
        raise ValueError("a card text is empty: the reference")
    if status in (None, "") and journal in (None, ""):
        return ref
    if not isinstance(status, str) or not isinstance(journal, str) or not journal.strip():
        raise ValueError("a status needs a journal and a journal needs a status")
    key = status.strip().lower()
    if key not in STATUS:
        raise ValueError(f"unknown status {status!r}; statuses: {', '.join(STATUS)}")
    return f"{ref} · {STATUS[key]} {journal.strip()}"


def _missing(name, text):
    """Return the characters of ``text`` that the font file ``name`` has no glyph for."""
    if name not in _CMAPS:
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            if None not in _CMAPS.values():  # warn once
                msg = "fontTools is not installed: the cards are drawn without a glyph check"
                warnings.warn(msg, stacklevel=4)
            _CMAPS[name] = None
        else:
            with TTFont(fonts_dir() / "ttf" / f"{name}.ttf") as font:
                _CMAPS[name] = set(font.getBestCmap())
    if _CMAPS[name] is None:
        return []
    return sorted({ch for ch in text if not ch.isspace() and ord(ch) not in _CMAPS[name]})


def author_line(authors, lab, shown=3):
    """Return the author line of a paper card.

    Parameters
    ----------
    authors : list of str
        All authors in paper order.
    lab : iterable of str
        The authors who are lab members.
    shown : int
        How many authors to name before the count of the others.

    Returns
    -------
    str
        The first ``shown`` authors, the number of the others, and every lab
        member among those others after "incl.", for example "A, B, C and 10
        co-authors, incl. D and E".

    Raises
    ------
    ValueError
        If ``authors`` is empty, ``shown`` is below 1, ``lab`` is a single
        string, or a lab member is not among the authors.
    """
    if not authors or shown < 1:
        raise ValueError("need at least 1 author and shown >= 1")
    if isinstance(lab, str):
        raise ValueError("lab must be a list of names, not one string")
    missing = [a for a in lab if a not in authors]
    if missing:
        raise ValueError(f"lab members not among the authors: {', '.join(missing)}")
    head, rest = list(authors[:shown]), list(authors[shown:])
    if not rest:
        return head[0] if len(head) == 1 else ", ".join(head[:-1]) + " and " + head[-1]
    line = ", ".join(head) + f" and {len(rest)} co-author{'s' if len(rest) > 1 else ''}"
    extra = [a for a in rest if a in set(lab)]
    if extra:
        line += ", incl. " + (
            extra[0] if len(extra) == 1 else ", ".join(extra[:-1]) + " and " + extra[-1]
        )
    return line


def _open(path):
    """Open an image upright (EXIF orientation applied) as RGBA."""
    from PIL import Image, ImageOps

    return ImageOps.exif_transpose(Image.open(path)).convert("RGBA")


class _Card:
    """One square canvas with the lab fonts, scaled from a 1080 px design."""

    def __init__(self, size, ground=None):
        from PIL import Image, ImageDraw

        self.Image, self.ImageDraw = Image, ImageDraw
        self.s = size / SIZE
        self.size = size
        self.im = ground if ground is not None else Image.new("RGBA", (size, size), INK["950"])
        self.d = ImageDraw.Draw(self.im)

    def u(self, v):
        return round(v * self.s)

    @staticmethod
    def name(face):
        return "GeistMono-Regular" if face == "mono" else f"Geist-{face}"

    def font(self, face, px):
        from PIL import ImageFont

        return ImageFont.truetype(str(fonts_dir() / "ttf" / f"{self.name(face)}.ttf"), self.u(px))

    def check(self, text, face):
        """Warn when the face has no glyph for a character of ``text``: it draws a blank box."""
        gone = _missing(self.name(face), text)
        if gone:
            chars = ", ".join(f"{ch} (U+{ord(ch):04X})" for ch in gone)
            card = f"card {_DRAWING[-1]!r}: " if _DRAWING else ""
            warnings.warn(
                f"{card}{self.name(face)} has no glyph for {chars}; "
                f"it draws a blank box in {text[:40]!r}",
                stacklevel=3,
            )

    def lines(self, text, font, width):
        """Break ``text`` into lines no wider than ``width`` px."""
        out, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if cur and self.d.textlength(trial, font=font) > width:
                out.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            out.append(cur)
        if any(self.d.textlength(ln, font=font) > width for ln in out):
            raise ValueError(f"a word is wider than the card: {text[:40]!r}")
        return out

    def block(self, xy, text, face, px, fill, width, lead, max_lines):
        """Draw wrapped text at a design position; return the y below it."""
        if not text.strip():
            raise ValueError("a card text is empty")
        self.check(text, face)
        font = self.font(face, px)
        rows = self.lines(text, font, self.u(width))
        if len(rows) > max_lines:
            raise ValueError(
                f"text needs {len(rows)} lines, the card holds {max_lines}: {text[:40]!r}"
            )
        x, y = self.u(xy[0]), self.u(xy[1])
        for row in rows:
            self.d.text((x, y), row, font=font, fill=fill)
            y += round(font.size * lead)
        return y / self.s

    def fit(self, xy, text, face, px, fill, width):
        """Draw 1 line at the largest size from ``px`` to :data:`MONO_MIN` that fits ``width``."""
        line = " ".join(text.split())  # as block() draws it
        for size in range(px, MONO_MIN - 1, -1):
            if self.d.textlength(line, font=self.font(face, size)) <= self.u(width):
                return self.block(xy, line, face, size, fill, width, 1, 1)
        raise ValueError(f"the text does not fit 1 line even at {MONO_MIN} px: {text[:40]!r}")

    def right(self, x_end, y, text, face, px, fill, width):
        """Draw 1 line that ends at design ``x_end``; refuse it when wider than ``width``."""
        self.check(text, face)
        font = self.font(face, px)
        w = self.d.textlength(text, font=font)
        if w > self.u(width):
            raise ValueError(f"the text is wider than its {width} px space: {text[:40]!r}")
        self.d.text((self.u(x_end) - round(w), self.u(y)), text, font=font, fill=fill)

    def label(self, xy, text, px=26, width=SIZE - 2 * MARGIN - 140):
        """Draw a tracked capital label in signal-400; refuse it when wider than ``width``."""
        self.check(text.upper(), "SemiBold")
        font, x = self.font("SemiBold", px), self.u(xy[0])
        total = sum(self.d.textlength(ch, font=font) + self.u(3) for ch in text.upper())
        if total > self.u(width):
            raise ValueError(f"the label is wider than its {width} px space: {text[:40]!r}")
        for ch in text.upper():
            self.d.text((x, self.u(xy[1])), ch, font=font, fill=SIGNAL["400"])
            x += self.d.textlength(ch, font=font) + self.u(3)

    def logo_width(self, height):
        """Return the drawn width in px of the logo at design ``height``."""
        with self.Image.open(assets_dir() / "fwl-logo-white.png") as lg:
            return round(lg.width * self.u(height) / lg.height)

    def logo_room(self, margin, height, gap=32):
        """Return the design width from ``margin`` to ``gap`` px before a right-hand logo."""
        return SIZE - 2 * margin - self.logo_width(height) / self.s - gap

    def logo(self, xy, height=60, right=True):
        with self.Image.open(assets_dir() / "fwl-logo-white.png") as img:
            lg = img.convert("RGBA")
        h = self.u(height)
        lg = lg.resize((self.logo_width(height), h), self.Image.LANCZOS)
        x = self.size - self.u(xy[0]) - lg.width if right else self.u(xy[0])
        self.im.alpha_composite(lg, (x, self.u(xy[1])))

    def fade(self, height, alpha, ramp, top=False):
        """Darken ``height`` design px at the foot (or the top) towards ink-950.

        The alpha grows over the first ``ramp`` design px and stays at ``alpha``
        over the rest, so text in that rest sits on an even dark ground.
        """
        h, r_px = self.u(height), max(self.u(ramp), 1)
        r, g, b = (int(INK["950"][i : i + 2], 16) for i in (1, 3, 5))
        band = self.Image.new("RGBA", (self.size, h))
        draw = self.ImageDraw.Draw(band)
        for y in range(h):
            t = min((h - 1 - y if top else y) / r_px, 1)
            draw.line((0, y, self.size, y), fill=(r, g, b, round(alpha * t**0.8)))
        self.im.alpha_composite(band, (0, 0 if top else self.size - h))

    def photo_fades(self, text_top):
        """Fade a photo card: dark under the text from ``text_top`` down, and at the top."""
        self.fade(SIZE - text_top + 170, 235, 170)
        self.fade(220, 170, 220, top=True)

    def photo(self, path, focus):
        """Fill the card with the largest square of the photo around ``focus``."""
        img = _open(path)
        side = min(img.size)
        fx, fy = focus
        x = min(max(round(fx * img.width - side / 2), 0), img.width - side)
        y = min(max(round(fy * img.height - side / 2), 0), img.height - side)
        sq = img.crop((x, y, x + side, y + side)).resize((self.size, self.size), self.Image.LANCZOS)
        self.im.alpha_composite(sq)

    def save(self, out):
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.im.convert("RGB").save(out, format="PNG", optimize=True)
        return out


def paper_card(out, photo, title, authors, lab=(), label="New paper", focus=(0.5, 0.4), size=SIZE):
    """Write the paper card: the photo, dark fades, the title and the author line.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    photo : str or pathlib.Path
        Photo of the first author; the card shows its largest square.
    title : str
        Paper title, at most 3 lines.
    authors : list of str
        All authors in paper order.
    lab : iterable of str
        Authors who are lab members; :func:`author_line` names them.
    label : str
        Capital label above the title.
    focus : tuple of float
        Centre of the square crop as fractions of the photo width and height.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If the title needs more than 3 lines, the author line more than 2, or
        :func:`author_line` refuses the authors.
    """
    c = _Card(size)
    author_rows = c.lines(author_line(authors, lab), c.font("Regular", 30), c.u(SIZE - 2 * MARGIN))
    title_rows = c.lines(title, c.font("SemiBold", 40), c.u(SIZE - 2 * MARGIN))
    if len(title_rows) > 3 or len(author_rows) > 2:
        raise ValueError("the title holds 3 lines and the author line 2")
    top = SIZE - 56 - 46 * len(title_rows) - 38 * len(author_rows) - 54
    c.photo(photo, focus)
    c.photo_fades(top - 16)
    c.logo((MARGIN, 40))
    c.label((MARGIN, top), label)
    y = c.block((MARGIN, top + 40), title, "SemiBold", 40, INK["0"], SIZE - 2 * MARGIN, 1.15, 3)
    c.block(
        (MARGIN, y + 10),
        author_line(authors, lab),
        "Regular",
        30,
        INK["200"],
        SIZE - 2 * MARGIN,
        1.25,
        2,
    )
    return c.save(out)


def glance_card(out, text, ref, label="At a glance", size=SIZE, *, status=None, journal=None):
    """Write the summary card: a label, the plain-language summary and the reference.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    text : str
        The summary, at most 15 lines at 41 px.
    ref : str
        Reference in Geist Mono at the foot, for example ``arXiv:2609.03144``; it
        shrinks to fit 1 line.
    label : str
        Capital label above the text.
    status, journal : str, optional
        Publication status and journal, added to the reference by :func:`ref_line`.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If a text does not fit its space on the card, or :func:`ref_line`
        refuses the reference, status or journal.
    """
    c = _Card(size)
    c.label((64, 64), label, 28)
    c.block((64, 118), text, "Regular", 41, INK["100"], SIZE - 128, 1.36, 15)
    ref = ref_line(ref, status, journal)
    logo_h = 60
    c.fit((64, SIZE - 96), ref, "mono", 28, INK["400"], c.logo_room(64, logo_h))
    c.logo((64, SIZE - 112), logo_h)
    return c.save(out)


def figure_card(
    out, figure, headline, source, ref, size=SIZE, *, caption=None, status=None, journal=None
):
    """Write the figure card: headline, the figure, an optional caption, source and reference.

    With a caption, the caption sits under the panel and the source under the caption,
    and the figure gets less height: the bottom of its panel may reach
    ``SIZE - 140 - (36 + 39 * lines)`` px, against ``SIZE - 150`` without a caption.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    figure : str or pathlib.Path
        Figure image; it takes the full width and keeps its aspect.
    headline : str
        One statement about the figure, at most 2 lines.
    source : str
        Source line under the figure, for example ``Postolec et al., Fig. 2``.
    ref : str
        Reference in Geist Mono at the foot; it shrinks to fit 1 line.
    caption : str, optional
        How to read the figure, at most 4 lines at 30 px.
    status, journal : str, optional
        Publication status and journal, added to the reference by :func:`ref_line`.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If the headline needs more than 2 lines, the caption more than 4, the
        source more than 1, the reference does not fit 1 line at 20 px or
        :func:`ref_line` refuses it, or the figure is too tall for the space
        left. A caption never shrinks.
    """
    c = _Card(size)
    ref = ref_line(ref, status, journal)
    y = c.block((MARGIN, 48), headline, "SemiBold", 46, INK["0"], SIZE - 2 * MARGIN, 1.12, 2)
    pad, top = 16, y + 22
    fig = _open(figure)
    w = c.u(SIZE - 2 * MARGIN - 2 * pad)
    h = round(fig.height * w / fig.width)
    room = c.u(SIZE - 150) - c.u(top) - c.u(2 * pad)
    if caption is not None:
        rows = c.lines(caption, c.font("Regular", CAPTION_PX), c.u(SIZE - 2 * MARGIN))
        if len(rows) > CAPTION_LINES:
            raise ValueError(
                f"text needs {len(rows)} lines, the card holds {CAPTION_LINES}: {caption[:40]!r}"
            )
        caption_h = 36 + CAPTION_PX * CAPTION_LEAD * len(rows)
        room = c.u(SIZE - 140 - caption_h) - c.u(top) - c.u(2 * pad)
    if h > room:
        raise ValueError(f"the figure needs {h} px of height, the card has {room}")
    fig = fig.resize((w, h), c.Image.LANCZOS)
    c.d.rounded_rectangle(
        (c.u(MARGIN), c.u(top), c.size - c.u(MARGIN), c.u(top) + h + c.u(2 * pad)),
        c.u(14),
        fill=INK["0"],
    )
    c.im.alpha_composite(fig, (c.u(MARGIN + pad), c.u(top + pad)))
    bottom = c.u(top) + h + c.u(2 * pad)
    if caption is None:
        c.block(
            (MARGIN, (bottom + c.u(22)) / c.s),
            source,
            "Regular",
            28,
            INK["300"],
            SIZE - 2 * MARGIN - 130,
            1,
            1,
        )
    else:
        y = c.block(
            (MARGIN, bottom / c.s + 18),
            caption,
            "Regular",
            CAPTION_PX,
            INK["100"],
            SIZE - 2 * MARGIN,
            CAPTION_LEAD,
            CAPTION_LINES,
        )
        c.block((MARGIN, y + 8), source, "Regular", 26, INK["300"], SIZE - 2 * MARGIN - 130, 1, 1)
    logo_h = 52
    c.fit((MARGIN, SIZE - 76), ref, "mono", 26, INK["300"], c.logo_room(MARGIN, logo_h))
    c.logo((MARGIN, SIZE - 96), logo_h)
    return c.save(out)


def cover_card(
    out, question, lead, ref, label="New paper", size=SIZE, *, status=None, journal=None
):
    """Write the carousel cover: the question a paper answers, in Geist Light.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    question : str
        The question, at most 6 lines at 86 px.
    lead : str
        One line at the foot, for example ``Led by PhD student Emma Postolec``.
    ref : str
        Reference in Geist Mono under the lead; it shrinks to fit 1 line.
    label : str
        Capital label above the question.
    status, journal : str, optional
        Publication status and journal, added to the reference by :func:`ref_line`.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If a text does not fit its space on the card, or :func:`ref_line`
        refuses the reference, status or journal.
    """
    c = _Card(size)
    c.label((64, 110), label, 28)
    y = c.block((64, 160), question, "Light", 86, INK["0"], SIZE - 128, 1.08, 6)
    c.d.rectangle((c.u(64), c.u(y + 30), c.u(174), c.u(y + 36)), fill=SIGNAL["400"])
    c.block((64, SIZE - 160), lead, "Regular", 32, INK["300"], SIZE - 128 - 180, 1.2, 1)
    ref = ref_line(ref, status, journal)
    logo_h = 60
    c.fit((64, SIZE - 112), ref, "mono", 28, INK["300"], c.logo_room(64, logo_h))
    c.logo((64, SIZE - 124), logo_h)
    return c.save(out)


def member_card(out, photo, name, lines, label="Meet the lab", focus=(0.5, 0.45), size=SIZE):
    """Write the member intro: the photo, dark fades, the name and up to 2 short lines.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    photo : str or pathlib.Path
        Photo of the member; the card shows its largest square.
    name : str
        The member's name, 1 line.
    lines : list of str
        Up to 2 lines under the name, for example the role and the path.
    label : str
        Capital label above the name.
    focus : tuple of float
        Centre of the square crop as fractions of the photo width and height.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If ``lines`` is a string or holds more than 2 lines, or a text does not
        fit its line.
    """
    if isinstance(lines, str) or len(lines) > 2:
        raise ValueError("the member card holds a list of up to 2 lines under the name")
    c = _Card(size)
    top = SIZE - 64 - 48 * len(lines) - 86
    c.photo(photo, focus)
    c.photo_fades(top - 60)
    c.logo((MARGIN, 40))
    c.label((MARGIN, top - 44), label)
    y = c.block((MARGIN, top), name, "SemiBold", 64, INK["0"], SIZE - 2 * MARGIN, 1.2, 1)
    for line in lines:
        y = c.block((MARGIN, y), line, "Regular", 34, INK["200"], SIZE - 2 * MARGIN, 1.4, 1)
    return c.save(out)


def event_card(out, name, when, heading, entries, label="At the conference", size=SIZE):
    """Write the event card: the event, place and dates, and the lab contributions.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    name : str
        Event name, 1 line at 86 px.
    when : str
        Place and dates, 1 line.
    heading : str
        Heading of the list, for example ``4 posters from the lab``.
    entries : list of tuple of str
        Up to 7 ``(name, detail)`` rows; the detail sits right-aligned in Geist
        Mono, for example ``poster 105``.
    label : str
        Capital label above the event name.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If there are more than 7 entries or a text does not fit its line.
    """
    if len(entries) > 7:
        raise ValueError("the event card holds 7 entries")
    c = _Card(size)
    c.label((64, 64), label)
    c.block((64, 108), name, "Light", 86, INK["0"], SIZE - 128, 1.1, 1)
    c.block((64, 214), when, "Regular", 34, INK["200"], SIZE - 128, 1.2, 1)
    c.d.rectangle((c.u(64), c.u(290), c.size - c.u(64), c.u(291)), fill=INK["700"])
    c.block((64, 320), heading, "SemiBold", 40, INK["0"], SIZE - 128, 1.2, 1)
    mono = c.font("mono", 30)
    for i, (who, detail) in enumerate(entries):
        y = 392 + 70 * i
        c.right(SIZE - 64, y + 6, detail, "mono", 30, INK["400"], 360)
        width = c.d.textlength(detail, font=mono) / c.s
        c.block((64, y), who, "Regular", 38, INK["100"], SIZE - 128 - width - 32, 1.2, 1)
    c.logo((64, SIZE - 112))
    return c.save(out)


def highlight_card(out, art, box, label, size=SIZE):
    """Write an Instagram Story Highlight cover: an artwork detail, darkened, with a label.

    Instagram crops the cover to a circle, so the label sits at the centre.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    art : str or pathlib.Path
        Artwork image.
    box : tuple of int
        ``(x, y, side)`` of the square detail in artwork pixels.
    label : str
        Highlight name, at most 2 lines.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If the box is not inside the artwork or the label needs more than 2
        lines.
    """
    from PIL import Image

    img = _open(art)
    x, y, side = box
    if x < 0 or y < 0 or side <= 0 or x + side > img.width or y + side > img.height:
        raise ValueError(f"the box {box} is not inside the artwork ({img.width} x {img.height})")
    ground = img.crop((x, y, x + side, y + side)).resize((size, size), Image.LANCZOS)
    ink = tuple(int(INK["950"][i : i + 2], 16) for i in (1, 3, 5))
    ground.alpha_composite(Image.new("RGBA", (size, size), ink + (120,)))
    c = _Card(size, ground)
    c.check(label, "Medium")
    font = c.font("Medium", 120)
    rows = c.lines(label, font, c.u(760))
    if len(rows) > 2:
        raise ValueError(f"the label needs {len(rows)} lines, the cover holds 2")
    step = round(font.size * 1.15)
    y = (size - step * len(rows)) // 2
    for row in rows:
        c.d.text(((size - c.d.textlength(row, font=font)) / 2, y), row, font=font, fill=INK["0"])
        y += step
    return c.save(out)


CARDS = {
    "paper": paper_card,
    "glance": glance_card,
    "figure": figure_card,
    "cover": cover_card,
    "member": member_card,
    "event": event_card,
    "highlight": highlight_card,
}


def render(spec, folder):
    """Render every card of a spec into ``folder``.

    Parameters
    ----------
    spec : dict
        ``{"cards": [{"card": <name in CARDS>, "file": <file name without
        .png>, ...}]}``; the other keys are the keyword arguments of that card
        function. Relative image paths resolve against ``base``, a key of
        ``spec`` that defaults to the current folder.
    folder : str or pathlib.Path
        Output folder.

    Returns
    -------
    list of pathlib.Path
        The written files, in spec order.

    Raises
    ------
    ValueError
        Before any card is written: if ``cards`` is missing, an entry lacks
        ``card`` or ``file``, a card name is unknown, a file stem holds a path
        separator, or 2 stems differ only in case. While writing: if a card
        refuses its texts or images.

    Warns
    -----
    UserWarning
        When a card draws a character that Geist has no glyph for; the
        warning names the card.
    """
    import inspect

    cards = spec.get("cards") if isinstance(spec, dict) else None
    if not isinstance(cards, list):
        raise ValueError("the spec needs a 'cards' list")
    seen = set()
    for item in cards:
        if not isinstance(item, dict) or "card" not in item or "file" not in item:
            raise ValueError(f"every card needs 'card' and 'file': {item!r}")
        stem = item["file"]
        if item["card"] not in CARDS:
            raise ValueError(f"unknown card {item['card']!r}; cards: {', '.join(CARDS)}")
        if (
            not isinstance(stem, str)
            or not stem
            or "/" in stem
            or "\\" in stem
            or stem.startswith(".")
        ):
            raise ValueError(f"the file stem must be a plain name: {stem!r}")
        if stem.lower() in seen:
            raise ValueError(f"2 cards share the file name {stem!r}")
        seen.add(stem.lower())
        unknown = (
            set(item) - {"card", "file"} - set(inspect.signature(CARDS[item["card"]]).parameters)
        )
        if unknown or "out" in item:
            raise ValueError(
                f"card {stem!r} has unknown keys: {', '.join(sorted(unknown or {'out'}))}"
            )
    base = Path(spec.get("base", "."))
    written = []
    for item in cards:
        args = dict(item)
        kind, stem = args.pop("card"), args.pop("file")
        for key in ("photo", "figure", "art"):
            if key in args:
                args[key] = base / args[key]
        for key in ("entries", "focus", "box"):
            if key in args:
                args[key] = [tuple(e) for e in args[key]] if key == "entries" else tuple(args[key])
        _DRAWING.append(stem)
        try:
            written.append(CARDS[kind](Path(folder) / f"{stem}.png", **args))
        finally:
            _DRAWING.pop()
    return written


def main(argv=None):
    """Render the cards of a JSON spec file: ``python -m fwl_visual_language.social SPEC DIR``.

    Image paths and a relative ``base`` resolve against the folder of the spec
    file. A spec or card error prints its message and returns 1.
    """
    import sys

    p = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.social", description=__doc__.split("\n")[0]
    )
    p.add_argument("spec", type=Path, help="JSON file with a 'cards' list")
    p.add_argument("folder", type=Path, help="output folder")
    a = p.parse_args(argv)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    if isinstance(spec, dict):
        spec["base"] = str(a.spec.parent / spec.get("base", "."))
    try:
        paths = render(spec, a.folder)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
