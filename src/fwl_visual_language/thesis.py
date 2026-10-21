"""LaTeX thesis class ``fwlthesis.cls`` for BSc and MSc theses of the lab.

The title page carries the banner of the University of Groningen, the Faculty of
Science and Engineering and the Kapteyn Astronomical Institute in ink, the
degree line, the title, the author, the student number, the supervisors and the
lab logo. Every section opens a new page, numbered sections with a large
signal-blue number. Text is Geist at 11 pt with the lab math (``fwl`` with
``math``), citations are author-year (``natbib`` with the AAS style), and
``siunitx`` sets numbers with units.

Grey guidance comes from ``\\guide{text}`` and ``\\guidesection{title}``; the
class option ``final`` hides all of it. ``\\figuredata{link}`` names the data
and the script of a figure in its caption. Compile with LuaLaTeX::

    \\documentclass{fwlthesis}
    \\title{Title of the thesis}
    \\author{Firstname Lastname}
    \\studentnumber{s1234567}
    \\degree{BSc thesis Astronomy}
    \\supervisors{Supervisor & Prof.~dr.~Name Surname\\\\ Second examiner & Dr.~Name}
    \\date{Month Year}
    \\begin{document}\\maketitle ... \\end{document}

Install the class and its fonts and logos, with ``--example`` also a complete
example thesis (text with guidance, data, plotting script, figure, references)::

    python -m fwl_visual_language.thesis path/to/thesis --example

``--zip`` writes the example as one archive that Overleaf can open.
"""

import argparse
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from . import __version__, assets_dir, fonts_dir
from .beamer import ADS_MACROS, ASSET_DIR
from .latex import FONT_DIR, install_latex

__all__ = ["CLS_NAME", "ZIP_NAME", "build_thesis_zip", "install_thesis", "thesis_cls"]

CLS_NAME = "fwlthesis.cls"
ZIP_NAME = "Forming Worlds Thesis.zip"
_LOGOS = ("fwl-logo-ink.png", "rug-banner-ink.png")
_LIGHT = ("Geist-Light.ttf", "Geist-LightItalic.ttf")
_ZIP_TIME = (2026, 10, 21, 0, 0, 0)

_BODY = r"""\newif\iffwl@final
\DeclareOption{final}{\fwl@finaltrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[11pt,a4paper,oneside]{article}
\RequirePackage[math]{fwl}[2026/10/20]
\providecommand{\fwlassetpath}{fwl-assets/}
\newfontfamily\fwllightface{Geist}[Path=\fwlfontpath,UprightFont=Geist-Light.ttf,
  ItalicFont=Geist-LightItalic.ttf]
\RequirePackage[a4paper,top=2.6cm,bottom=3cm,left=2.6cm,right=2.6cm]{geometry}
\RequirePackage{graphicx}
\RequirePackage{siunitx}
\RequirePackage{titlesec}
\RequirePackage{caption}
\RequirePackage{fancyhdr}
\RequirePackage[authoryear,round]{natbib}
\setcitestyle{aysep={}}
\bibliographystyle{aasjournal}
\@ifpackageloaded{hyperref}{\hypersetup{colorlinks=true,linkcolor=fwlLink,urlcolor=fwlLink,citecolor=fwlLink}}{\RequirePackage[colorlinks=true,linkcolor=fwlLink,urlcolor=fwlLink,citecolor=fwlLink]{hyperref}}

\linespread{1.15}\selectfont
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55em}

% Numbered sections open under a large signal-blue number
\titleformat{\section}[display]{\fwllightface\fontsize{26}{30}\selectfont\color{fwlHeading}}%
  {\normalfont\fwlmedium\fontsize{40}{40}\selectfont\color{fwlAccent}\thesection}{0.4em}{}
\titlespacing*{\section}{0pt}{0pt}{1.6em}
\titleformat{\subsection}{\fwlmedium\large\color{fwlHeading}}{\textcolor{fwlAccent}{\thesubsection}}{0.7em}{}
\titlespacing*{\subsection}{0pt}{1.1em}{0.3em}
\titleformat{\subsubsection}{\fwlmedium\normalsize\color{fwlHeading}}{\textcolor{fwlAccent}{\thesubsubsection}}{0.7em}{}
\renewcommand{\tableofcontents}{\section*{\contentsname}\@starttoc{toc}}
\renewcommand{\bibsection}{\section*{\refname}}

\DeclareCaptionFont{fwlmuted}{\color{fwlMuted}}
\DeclareCaptionFont{fwlheading}{\fwlmedium\color{fwlHeading}}
\captionsetup{font={small,fwlmuted},labelfont=fwlheading,labelsep=period,singlelinecheck=false}

% Running head: the title at the left, the current section at the right
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\sectionmark}[1]{\markboth{\thesection\quad#1}{}}
\fancyhead[L]{\ttfamily\footnotesize\color{fwlMuted}\@title}
\fancyhead[R]{\ttfamily\footnotesize\color{fwlMuted}\leftmark}
\fancyfoot[R]{\ttfamily\footnotesize\color{fwlMuted}\thepage}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[R]{\ttfamily\footnotesize\color{fwlMuted}\thepage}}
% Every section opens a new page, also one that follows another heading directly
\AtBeginDocument{\let\fwl@section\section
  \renewcommand{\section}{\clearpage\@ifstar{\fwl@starred}{\fwl@section}}}
\newcommand{\fwl@starred}[1]{\fwl@section*{#1}\markboth{#1}{}}

% Title page
\newcommand{\fwl@degree}{}\newcommand{\fwl@snum}{}\newcommand{\fwl@sup}{}
\newcommand{\degree}[1]{\renewcommand{\fwl@degree}{#1}}
\newcommand{\studentnumber}[1]{\renewcommand{\fwl@snum}{#1}}
\newcommand{\supervisors}[1]{\renewcommand{\fwl@sup}{#1}}
\renewcommand{\maketitle}{\begin{titlepage}\thispagestyle{empty}%
  \includegraphics[width=\textwidth]{\fwlassetpath rug-banner-ink.png}\par
  \vspace*{5.5cm}
  {\fwlmedium\small\color{fwlAccent}\MakeUppercase{\fwl@degree}\quad\textperiodcentered\quad
    \MakeUppercase{Kapteyn Astronomical Institute}\par}\vspace{0.8em}
  {\raggedright\hyphenpenalty=10000\fwllightface\fontsize{30}{36}\selectfont
    \color{fwlHeading}\@title\par}\vspace{1em}
  {\color{fwlAccent}\rule{3cm}{0.8pt}}\par\vspace{1.2em}
  {\large\fwlmedium\color{fwlHeading}\@author\par}{\color{fwlMuted}\fwl@snum\par}\vspace{1.6em}
  {\color{fwlMuted}\small\begin{tabular}{@{}l@{\hspace{1.2em}}l@{}}\fwl@sup\end{tabular}\par}
  \vfill
  \includegraphics[width=3.4cm]{\fwlassetpath fwl-logo-ink.png}\hfill
  \raisebox{0.4cm}{\color{fwlMuted}\small Groningen, \@date}\par
\end{titlepage}}

% Grey guidance; the final option hides all of it
\newcommand{\guide}[1]{\iffwl@final\ignorespaces\else
  \par{\small\color{fwlInk500}#1\par}\medskip\fi}
\newcommand{\guidesection}[1]{\iffwl@final\else\section*{#1}\fi}
\newcommand{\guidecmd}[1]{\texttt{#1}}
% Where the data and the script of a figure are published
\newcommand{\figuredata}[1]{ Data and script: \url{#1}.}

"""


def thesis_cls(release=None):
    """Return the text of ``fwlthesis.cls``.

    Parameters
    ----------
    release : datetime.date, optional
        Date written into ``\\ProvidesClass``. Defaults to 2026-10-21 so the
        output does not change from day to day.

    Returns
    -------
    str
        LaTeX class source.
    """
    release = release or date(2026, 10, 21)
    head = [
        "% Forming Worlds Lab thesis class (fwl-visual-language "
        f"{__version__}). Generated; edit the generator, not this file.",
        "\\NeedsTeXFormat{LaTeX2e}",
        f"\\ProvidesClass{{fwlthesis}}[{release:%Y/%m/%d} v{__version__} Forming Worlds Lab]",
    ]
    return "\n".join(head) + "\n" + _BODY + ADS_MACROS + "\\endinput\n"


def install_thesis(dest, example=False):
    """Write ``fwlthesis.cls``, the ``fwl`` package, the fonts and the logos into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Folder of the thesis. It is created if it does not exist.
    example : bool, optional
        Also write the example thesis: ``main.tex`` with the guidance,
        ``references.bib``, ``latexmkrc``, and the data, script and figure of
        Figure 1. An existing ``main.tex`` stops the call before anything is
        written.

    Returns
    -------
    pathlib.Path
        Path of the written class file.

    Raises
    ------
    FileExistsError
        If ``example`` is true and ``dest`` already holds a ``main.tex``.
    """
    dest = Path(dest)
    src = Path(__file__).resolve().parent / "thesis_example"
    if example and (dest / "main.tex").exists():
        raise FileExistsError(f"{dest / 'main.tex'} exists; install the example elsewhere")
    install_latex(dest)
    for face in _LIGHT:
        shutil.copyfile(fonts_dir() / "ttf" / face, dest / FONT_DIR / face)
    assets = dest / ASSET_DIR
    assets.mkdir(exist_ok=True)
    for logo in _LOGOS:
        shutil.copyfile(assets_dir() / logo, assets / logo)
    if example:
        for path in sorted(src.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                out = dest / path.relative_to(src)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, out)
    out = dest / CLS_NAME
    out.write_text(thesis_cls(), encoding="utf-8")
    return out


def build_thesis_zip(out):
    """Write the example thesis with the class, fonts and logos as one zip archive.

    The archive holds no folder around the files, so Overleaf (New project,
    Upload project) opens ``main.tex`` at its root. Time stamps are fixed, so
    the same version writes the same archive.

    Parameters
    ----------
    out : str or pathlib.Path
        Path of the archive; its folder must exist.

    Returns
    -------
    pathlib.Path
        The written archive.
    """
    out = Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        install_thesis(tmp, example=True)
        files = sorted(p for p in Path(tmp).rglob("*") if p.is_file())
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for path in files:
                info = zipfile.ZipInfo(path.relative_to(tmp).as_posix(), _ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, path.read_bytes())
    return out


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.thesis DEST``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.thesis",
        description="Write the Forming Worlds Lab thesis class, its fonts and logos.",
    )
    parser.add_argument("dest", help="folder of the thesis, or with --zip the archive path")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--example", action="store_true", help="also write the example thesis")
    group.add_argument("--zip", action="store_true", help="write the example as a zip archive")
    args = parser.parse_args(argv)
    if args.zip:
        print(build_thesis_zip(args.dest))
    else:
        print(install_thesis(args.dest, example=args.example))


if __name__ == "__main__":
    main()
