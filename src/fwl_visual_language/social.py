"""Social media cards in the lab look: ink ground, Geist, signal blue and the lab logo.

Each card is a square PNG, 1080 px by default, for Bluesky, Mastodon, Instagram and
LinkedIn. The cards are:

- ``paper``: the first author's photo with the paper title and an author line
  that names every lab member;
- ``glance``: the short plain-language summary of a paper;
- ``figure``: a figure with a headline and its source;
- ``cover``: the question a paper answers, as the first slide of a carousel;
- ``member``: a member intro over the member's photo;
- ``event``: a conference card with the lab contributions;
- ``highlight``: an Instagram Story Highlight cover, from a detail of an artwork.

Photos and artwork come from the caller; the package holds no images other than
the logo. A text that does not fit its card raises ``ValueError`` instead of
running off the card. Run ``python -m fwl_visual_language.social SPEC.json DIR``
to render the cards that a JSON file lists.
"""

import argparse
import json
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
    "render",
]

SIZE = 1080
INK = ramp("ink")
SIGNAL = ramp("signal")
MARGIN = 48


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
        If ``authors`` is empty or ``shown`` is below 1.
    """
    if not authors or shown < 1:
        raise ValueError("need at least 1 author and shown >= 1")
    head, rest = list(authors[:shown]), list(authors[shown:])
    if not rest:
        return head[0] if len(head) == 1 else ", ".join(head[:-1]) + " and " + head[-1]
    line = ", ".join(head) + f" and {len(rest)} co-author{'s' if len(rest) > 1 else ''}"
    lab = set(lab)
    extra = [a for a in rest if a in lab]
    if extra:
        line += ", incl. " + (
            extra[0] if len(extra) == 1 else ", ".join(extra[:-1]) + " and " + extra[-1]
        )
    return line


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

    def font(self, face, px):
        from PIL import ImageFont

        name = "GeistMono-Regular" if face == "mono" else f"Geist-{face}"
        return ImageFont.truetype(str(fonts_dir() / "ttf" / f"{name}.ttf"), self.u(px))

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

    def label(self, xy, text, px=26):
        """Draw a tracked capital label in signal-400."""
        font, x = self.font("SemiBold", px), self.u(xy[0])
        for ch in text.upper():
            self.d.text((x, self.u(xy[1])), ch, font=font, fill=SIGNAL["400"])
            x += self.d.textlength(ch, font=font) + self.u(3)

    def logo(self, xy, height=60, right=True):
        lg = self.Image.open(assets_dir() / "fwl-logo-white.png").convert("RGBA")
        h = self.u(height)
        lg = lg.resize((round(lg.width * h / lg.height), h), self.Image.LANCZOS)
        x = self.size - self.u(xy[0]) - lg.width if right else self.u(xy[0])
        self.im.alpha_composite(lg, (x, self.u(xy[1])))

    def fade(self, height, alpha, top=False):
        """Darken ``height`` design px at the foot (or the top) towards ink-950 at ``alpha``."""
        h = self.u(height)
        r, g, b = (int(INK["950"][i : i + 2], 16) for i in (1, 3, 5))
        band = self.Image.new("RGBA", (self.size, h))
        draw = self.ImageDraw.Draw(band)
        for y in range(h):
            t = (h - 1 - y if top else y) / max(h - 1, 1)
            draw.line((0, y, self.size, y), fill=(r, g, b, round(alpha * t**0.8)))
        self.im.alpha_composite(band, (0, 0 if top else self.size - h))

    def photo_fades(self, height):
        """Fade a photo card at the foot for the text and at the top for the logo."""
        self.fade(height, 250)
        self.fade(220, 170, top=True)

    def photo(self, path, focus):
        """Fill the card with the largest square of the photo around ``focus``."""
        img = self.Image.open(path).convert("RGBA")
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
    """Write the paper card: the photo, a dark fade, the title and the author line.

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
    """
    c = _Card(size)
    c.photo(photo, focus)
    c.photo_fades(560)
    c.logo((MARGIN, 40))
    author_rows = c.lines(author_line(authors, lab), c.font("Regular", 30), c.u(SIZE - 2 * MARGIN))
    title_rows = c.lines(title, c.font("SemiBold", 40), c.u(SIZE - 2 * MARGIN))
    if len(title_rows) > 3 or len(author_rows) > 2:
        raise ValueError("the title holds 3 lines and the author line 2")
    top = SIZE - 56 - 46 * len(title_rows) - 38 * len(author_rows) - 54
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


def glance_card(out, text, ref, label="At a glance", size=SIZE):
    """Write the summary card: a label, the plain-language summary and the reference.

    Parameters
    ----------
    out : str or pathlib.Path
        PNG file to write.
    text : str
        The summary, at most 15 lines at 41 px (about 120 words).
    ref : str
        Reference in Geist Mono at the foot, for example ``arXiv:2609.03144``.
    label : str
        Capital label above the text.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.
    """
    c = _Card(size)
    c.label((64, 64), label, 28)
    c.block((64, 118), text, "Regular", 41, INK["100"], SIZE - 128, 1.36, 15)
    c.d.text((c.u(64), c.u(SIZE - 96)), ref, font=c.font("mono", 28), fill=INK["400"])
    c.logo((64, SIZE - 112))
    return c.save(out)


def figure_card(out, figure, headline, source, ref, size=SIZE):
    """Write the figure card: headline, the figure on a white panel, source and reference.

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
        Reference in Geist Mono at the foot.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.

    Raises
    ------
    ValueError
        If the headline needs more than 2 lines or the figure is too tall for
        the space left.
    """
    c = _Card(size)
    y = c.block((MARGIN, 48), headline, "SemiBold", 46, INK["0"], SIZE - 2 * MARGIN, 1.12, 2)
    pad, top = 16, y + 22
    fig = c.Image.open(figure).convert("RGBA")
    w = c.u(SIZE - 2 * MARGIN - 2 * pad)
    h = round(fig.height * w / fig.width)
    room = c.u(SIZE - 150) - c.u(top) - c.u(2 * pad)
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
    c.d.text((c.u(MARGIN), bottom + c.u(22)), source, font=c.font("Regular", 28), fill=INK["300"])
    c.d.text((c.u(MARGIN), c.u(SIZE - 76)), ref, font=c.font("mono", 26), fill=INK["300"])
    c.logo((MARGIN, SIZE - 96), 52)
    return c.save(out)


def cover_card(out, question, lead, ref, label="New paper", size=SIZE):
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
        Reference in Geist Mono under the lead.
    label : str
        Capital label above the question.
    size : int
        Card side in px.

    Returns
    -------
    pathlib.Path
        The written file.
    """
    c = _Card(size)
    c.label((64, 110), label, 28)
    y = c.block((64, 160), question, "Light", 86, INK["0"], SIZE - 128, 1.08, 6)
    c.d.rectangle((c.u(64), c.u(y + 30), c.u(174), c.u(y + 36)), fill=SIGNAL["400"])
    c.block((64, SIZE - 160), lead, "Regular", 32, INK["300"], SIZE - 128 - 180, 1.2, 1)
    c.d.text((c.u(64), c.u(SIZE - 112)), ref, font=c.font("mono", 28), fill=INK["300"])
    c.logo((64, SIZE - 124))
    return c.save(out)


def member_card(out, photo, name, lines, label="Meet the lab", focus=(0.5, 0.45), size=SIZE):
    """Write the member intro: the photo, a dark fade, the name and up to 2 short lines.

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
    """
    if len(lines) > 2:
        raise ValueError("the member card holds 2 lines under the name")
    c = _Card(size)
    c.photo(photo, focus)
    c.photo_fades(480)
    c.logo((MARGIN, 40))
    top = SIZE - 64 - 48 * len(lines) - 86
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
        width = c.d.textlength(detail, font=mono) / c.s
        c.block((64, y), who, "Regular", 38, INK["100"], SIZE - 128 - width - 32, 1.2, 1)
        c.d.text(
            (c.size - c.u(64) - round(width * c.s), c.u(y + 6)), detail, font=mono, fill=INK["400"]
        )
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
    """
    from PIL import Image

    img = Image.open(art).convert("RGBA")
    x, y, side = box
    if x < 0 or y < 0 or side <= 0 or x + side > img.width or y + side > img.height:
        raise ValueError(f"the box {box} is not inside the artwork ({img.width} x {img.height})")
    ground = img.crop((x, y, x + side, y + side)).resize((size, size), Image.LANCZOS)
    ground.alpha_composite(Image.new("RGBA", (size, size), (1, 3, 5, 120)))
    c = _Card(size, ground)
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
        ``{"cards": [{"card": <name in CARDS>, "file": <file stem>, ...}]}``;
        the other keys are the keyword arguments of that card function. Relative
        image paths resolve against ``base``, a key of ``spec`` that defaults to
        the current folder.
    folder : str or pathlib.Path
        Output folder.

    Returns
    -------
    list of pathlib.Path
        The written files, in spec order.

    Raises
    ------
    ValueError
        If a card name is unknown or 2 cards share a file name.
    """
    base = Path(spec.get("base", "."))
    names = [c["file"] for c in spec["cards"]]
    if len(set(names)) != len(names):
        raise ValueError("2 cards share a file name")
    written = []
    for item in spec["cards"]:
        args = dict(item)
        kind, stem = args.pop("card"), args.pop("file")
        if kind not in CARDS:
            raise ValueError(f"unknown card {kind!r}; cards: {', '.join(CARDS)}")
        for key in ("photo", "figure", "art"):
            if key in args:
                args[key] = base / args[key]
        for key in ("entries", "focus", "box"):
            if key in args:
                args[key] = [tuple(e) for e in args[key]] if key == "entries" else tuple(args[key])
        written.append(CARDS[kind](Path(folder) / f"{stem}.png", **args))
    return written


def main(argv=None):
    """Render the cards of a JSON spec file: ``python -m fwl_visual_language.social SPEC DIR``."""
    p = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.social", description=__doc__.split("\n")[0]
    )
    p.add_argument("spec", type=Path, help="JSON file with a 'cards' list")
    p.add_argument("folder", type=Path, help="output folder")
    a = p.parse_args(argv)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    spec.setdefault("base", str(a.spec.parent))
    for path in render(spec, a.folder):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
