"""Email signature and letterhead PDFs for members of the lab.

The signature is one line of HTML: the name in ink, the lab name as a link in
signal blue, then the institute and the university in grey. Mail clients do not
load Geist, so it is set in Helvetica Neue, Helvetica or Arial, and it has no
image that a client could block.

The letterheads are A4 PDFs with 2 pages, a first page and a page for the rest
of the letter, compiled with LuaLaTeX in Geist. ``letter`` has the lab logo and
the sender block on its first page and the lab line in the footer.
``university`` has the banner of the University of Groningen, the Faculty of
Science and Engineering and the Kapteyn Astronomical Institute in ink with the
sender line under it, and the lab logo with the address and website in the
footer. Without
a name, the files carry the placeholders of the Word letters, so each member
can write their own::

    python -m fwl_visual_language.stationery out --name "Firstname Lastname" \\
        --role "PhD student" --email f.lastname@rug.nl
"""

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import assets_dir, fonts_dir, ramp

__all__ = [
    "KINDS",
    "SIGNATURE_NAME",
    "build_letterhead",
    "build_stationery",
    "letterhead_name",
    "letterhead_tex",
    "signature_html",
]

KINDS = ("letter", "university")
SIGNATURE_NAME = "Forming Worlds Signature.html"
NAME, ROLE, EMAIL = "Name Surname", "Role", "name@rug.nl"
MAIL_FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
INSTITUTE, UNIVERSITY = "Kapteyn Astronomical Institute", "University of Groningen"
ADDRESS, WEB = "Landleven 12, 9747 AD Groningen", "formingworlds.space"
_FONTS = ("Geist-Regular.ttf", "Geist-Medium.ttf")
_LOGOS = ("fwl-logo-ink.png", "rug-banner-ink.png")
# room for the sender block beside the logo, and for the sender line under the banner
_ROOM = {"letter": "118mm", "university": "160mm"}
_TEX_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    # after a row break these would read as its options
    "[": "{[}",
    "]": "{]}",
    "*": "{*}",
}


def _tex(text):
    return "".join(_TEX_CHARS.get(c, c) for c in text)


def _check(name, role, email):
    for label, value in (("name", name), ("role", role), ("email", email)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty text, got {value!r}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"{label} must be 1 line, got {value!r}")
    return name.strip(), role.strip(), email.strip()


def signature_html(name=NAME):
    """Return the email signature of one person as an HTML paragraph.

    Parameters
    ----------
    name : str, optional
        Full name; the placeholder ``Name Surname`` by default.

    Returns
    -------
    str
        One ``<p>`` element with inline styles, which mail clients keep.

    Raises
    ------
    ValueError
        If ``name`` is empty or holds a line break.
    """
    name = _check(name, ROLE, EMAIL)[0]
    # character references keep the file ASCII, so no browser guesses its encoding
    name = html.escape(name).encode("ascii", "xmlcharrefreplace").decode("ascii")
    ink, signal = ramp("ink"), ramp("signal")
    dot = " &middot; "
    return (
        f'<p style="margin:0;font-family:{MAIL_FONT};font-size:12px;line-height:1.5;'
        f'color:{ink["600"]}">'
        f'<span style="color:{ink["900"]};font-weight:600">{name}</span>{dot}'
        f'<a href="https://{WEB}" style="color:{signal["500"]};text-decoration:none">'
        f"Forming Worlds Lab</a>{dot}{INSTITUTE}{dot}{UNIVERSITY}</p>\n"
    )


def letterhead_name(kind):
    """Return the file name of one letterhead, for example ``Forming Worlds Letterhead.pdf``.

    Parameters
    ----------
    kind : str
        ``letter`` or ``university``.

    Returns
    -------
    str
        The file name.

    Raises
    ------
    ValueError
        If ``kind`` is not one of :data:`KINDS`.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, got {kind!r}")
    return (
        "Forming Worlds University Letterhead.pdf"
        if kind == "university"
        else ("Forming Worlds Letterhead.pdf")
    )


def letterhead_tex(kind, name=NAME, role=ROLE, email=EMAIL):
    """Return the LuaLaTeX source of one letterhead.

    The source reads the fonts and logos from its own folder. Compiling it
    stops with an error when the sender text is wider than its room.

    Parameters
    ----------
    kind : str
        ``letter`` or ``university``.
    name, role, email : str, optional
        Sender; the placeholders of the Word letters by default. The role is
        followed by ``, Forming Worlds Lab``.

    Returns
    -------
    str
        The document source.

    Raises
    ------
    ValueError
        If ``kind`` is unknown, or a sender field is empty or holds a line break.
    """
    letterhead_name(kind)
    name, role, email = (_tex(v) for v in _check(name, role, email))
    ink, signal = ramp("ink"), ramp("signal")
    colours = "".join(
        f"\\definecolor{{{key}}}{{HTML}}{{{hexv.lstrip('#')}}}\n"
        for key, hexv in (
            ("fwlink", ink["900"]),
            ("fwltext", ink["600"]),
            ("fwlfoot", ink["500"]),
            ("fwlsignal", signal["500"]),
        )
    )
    sep = "\\enspace\\textperiodcentered\\enspace "
    pos = "remember picture,overlay,x=1mm,y=1mm,shift={(current page.north west)}"
    small = "font=\\fontsize{7.5}{9}\\selectfont\\color{fwlfoot}"
    if kind == "letter":
        sender = (
            f"\\begin{{tabular}}{{@{{}}r@{{}}}}{{\\bfseries\\color{{fwlink}}{name}}}\\\\"
            f"{role}, Forming Worlds Lab\\\\{INSTITUTE}\\\\{UNIVERSITY}\\\\{ADDRESS}\\\\"
            f"{email}{sep}{WEB}\\end{{tabular}}"
        )
        first = (
            "\\node[anchor=north west,inner sep=0] at (25,-18)"
            " {\\includegraphics[width=36mm]{fwl-logo-ink.png}};\n"
            "\\node[anchor=north east,inner sep=0] at (185,-18.5) {\\usebox\\fwlsender};\n"
            "\\draw[fwlsignal,line width=0.8pt] (25,-45) -- (185,-45);\n"
            f"\\node[anchor=south west,inner sep=0,{small}] at (25,-282)"
            f" {{Forming Worlds Lab{sep}{INSTITUTE}{sep}{UNIVERSITY}}};\n"
        )
        rest = (
            f"\\node[anchor=south west,inner sep=0,{small}] at (25,-282)"
            f" {{Forming Worlds Lab{sep}{INSTITUTE}{sep}{UNIVERSITY}}};\n"
        )
    else:
        sender = f"{{\\bfseries\\color{{fwlink}}{name}}}{sep}{role}, Forming Worlds Lab{sep}{email}"
        logo = (
            "\\node[anchor=south west,inner sep=0] at (25,-284)"
            " {\\includegraphics[width=20mm]{fwl-logo-ink.png}};\n"
        )
        first = (
            "\\node[anchor=north west,inner sep=0] at (25,-15)"
            " {\\includegraphics[width=160mm]{rug-banner-ink.png}};\n"
            "\\node[anchor=north east,inner sep=0] at (185,-35) {\\usebox\\fwlsender};\n"
            + logo
            + f"\\node[anchor=south east,inner sep=0,{small}] at (185,-282)"
            f" {{{ADDRESS}{sep}{WEB}}};\n"
        )
        rest = logo
    rest += f"\\node[anchor=south east,inner sep=0,{small}] at (185,-282) {{2}};\n"
    return (
        "% Forming Worlds Lab letterhead, written by fwl_visual_language.stationery\n"
        "\\documentclass{article}\n"
        "\\usepackage[a4paper,margin=0pt]{geometry}\n"
        "\\usepackage{fontspec,xcolor,tikz,graphicx}\n"
        "\\setmainfont{Geist}[Path=./,UprightFont=Geist-Regular.ttf,BoldFont=Geist-Medium.ttf,"
        "Ligatures=TeXOff]\n"  # -- and ' print as typed
        "\\pdfvariable suppressoptionalinfo 767\n"  # no dates or ID: same input, same PDF
        "\\tracinglostchars=3\n"  # a character without a glyph in Geist stops the run
        f"{colours}"
        "\\pagestyle{empty}\\parindent=0pt\n"
        "\\newsavebox\\fwlsender\n"
        "\\sbox\\fwlsender{\\fontsize{8}{11}\\selectfont\\color{fwltext}"
        f"\\renewcommand{{\\arraystretch}}{{0.95}}{sender}}}\n"
        f"\\ifdim\\wd\\fwlsender>{_ROOM[kind]}\n"
        f"  \\errmessage{{fwl: the sender text is wider than {_ROOM[kind]}}}\n"
        "\\fi\n"
        "\\begin{document}\n"
        f"\\begin{{tikzpicture}}[{pos}]\n{first}\\end{{tikzpicture}}\\null\\newpage\n"
        f"\\begin{{tikzpicture}}[{pos}]\n{rest}\\end{{tikzpicture}}\\null\n"
        "\\end{document}\n"
    )


def build_letterhead(out, kind, name=NAME, role=ROLE, email=EMAIL):
    """Compile one letterhead to a PDF with LuaLaTeX.

    Parameters
    ----------
    out : str or pathlib.Path
        Path of the PDF; its folder must exist.
    kind : str
        ``letter`` or ``university``.
    name, role, email : str, optional
        Sender, as in :func:`letterhead_tex`.

    Returns
    -------
    pathlib.Path
        The written PDF.

    Raises
    ------
    RuntimeError
        If ``lualatex`` is not on the path, or the compile fails; the message
        names a character that Geist does not have, or holds the TeX error, for
        example a sender text wider than its room.
    ValueError
        As :func:`letterhead_tex`.
    """
    source = letterhead_tex(kind, name, role, email)
    if shutil.which("lualatex") is None:
        raise RuntimeError("lualatex is not on the path; install TeX Live or MacTeX")
    out = Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for file in _FONTS:
            shutil.copyfile(fonts_dir() / "ttf" / file, tmp / file)
        for file in _LOGOS:
            shutil.copyfile(assets_dir() / file, tmp / file)
        (tmp / "letterhead.tex").write_text(source, encoding="utf-8")
        # tikz places the page nodes from the .aux of the first pass
        for _ in range(2):
            run = subprocess.run(
                ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "letterhead.tex"],
                cwd=tmp,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            if run.returncode != 0:
                lost = re.search(r"There is no (.+?) \((U\+[0-9A-Fa-f]+)\)", run.stdout)
                if lost:  # TeX stops at the first one
                    char, code = lost.groups()
                    raise RuntimeError(
                        f"Geist has no glyph for {char} ({code}); write the text without it"
                    )
                errors = [ln for ln in run.stdout.splitlines() if ln.startswith("!")]
                detail = " ".join(errors) or run.stdout[-500:]
                raise RuntimeError(f"lualatex failed for {kind}: {detail}")
        shutil.copyfile(tmp / "letterhead.pdf", out)
    return out


def build_stationery(folder, name=NAME, role=ROLE, email=EMAIL):
    """Write the signature and both letterheads of one person into a folder.

    Parameters
    ----------
    folder : str or pathlib.Path
        Output folder; created if needed.
    name, role, email : str, optional
        Sender, as in :func:`letterhead_tex`; the placeholders by default.

    Returns
    -------
    list of pathlib.Path
        The signature, then the letter and the university letterhead.

    Raises
    ------
    RuntimeError, ValueError
        As :func:`build_letterhead`; the folder then stays as it was.
    """
    folder = Path(folder)
    names = [SIGNATURE_NAME, *(letterhead_name(k) for k in KINDS)]
    # build all 3 first, so a failure leaves the folder as it was
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / SIGNATURE_NAME).write_text(signature_html(name), encoding="ascii")
        for kind in KINDS:
            build_letterhead(tmp / letterhead_name(kind), kind, name, role, email)
        folder.mkdir(parents=True, exist_ok=True)
        for file in names:
            shutil.copyfile(tmp / file, folder / file)
    return [folder / file for file in names]


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.stationery FOLDER``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.stationery",
        description="Write the Forming Worlds Lab email signature and letterhead PDFs.",
    )
    parser.add_argument("folder", help="output folder")
    parser.add_argument("--name", default=NAME, help=f"full name (default: {NAME})")
    parser.add_argument("--role", default=ROLE, help=f"role in the lab (default: {ROLE})")
    parser.add_argument("--email", default=EMAIL, help=f"email address (default: {EMAIL})")
    args = parser.parse_args(argv)
    try:
        paths = build_stationery(args.folder, args.name, args.role, args.email)
    except (ValueError, RuntimeError, OSError) as err:
        parser.error(str(err))
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
