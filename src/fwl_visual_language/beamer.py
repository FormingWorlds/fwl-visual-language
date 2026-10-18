"""Beamer theme ``beamerthemefwl.sty``: the lab slide masters for LaTeX talks.

The theme follows the slide masters of :mod:`fwl_visual_language.slides`:
every frame on the ink-950 ground and statement frames on ink-980, with no
background picture, one-line Geist Light titles and two reference corners.
``\\slideref{key}[left|right]`` prints a reference from the bibliography as
``Teske+ 25 ApJL`` (1 or 2 family names, else the first plus "+", a 2-digit
year, the journal in italics); several references in one corner stack upward
from a fixed base. Compile with LuaLaTeX and BibTeX.

Install it next to a talk::

    python -m fwl_visual_language.beamer path/to/talk
"""

import argparse
import shutil
from datetime import date
from pathlib import Path

from . import __version__, assets_dir, fonts_dir
from .latex import FONT_DIR, install_latex

__all__ = ["ASSET_DIR", "THEME_NAME", "beamer_theme", "install_beamer"]

THEME_NAME = "beamerthemefwl.sty"
ASSET_DIR = "fwl-assets"
_LIGHT = ("Geist-Light.ttf", "Geist-LightItalic.ttf")
_LOGO = "fwl-logo-white.png"

_BODY = r"""\RequirePackage[math]{fwl}
\RequirePackage{tikz}
\RequirePackage{xstring}
\RequirePackage{etoolbox}
\RequirePackage[backend=bibtex,style=authoryear,maxcitenames=99,
  uniquename=false,uniquelist=false]{biblatex}

\usefonttheme{professionalfonts}
\setbeamertemplate{navigation symbols}{}
\setbeamersize{text margin left=15pt,text margin right=15pt}
\newfontfamily\fwllight{Geist}[Path=\fwlfontpath, UprightFont=Geist-Light.ttf,
  ItalicFont=Geist-LightItalic.ttf, BoldFont=Geist-SemiBold.ttf,
  BoldItalicFont=Geist-SemiBoldItalic.ttf]
\providecommand{\fwlassetpath}{fwl-assets/}

% Sizes are in points of the 1920-wide slide design; 0.2371 scales them to the 160 mm beamer page.
\newcommand{\fwlsize}[1]{\fontsize{\fpeval{#1*0.2371}pt}{\fpeval{#1*0.2371*1.2}pt}\selectfont}

% Colours of text on the ink ground
\setbeamercolor{normal text}{fg=fwlInk100,bg=fwlInk950}
\setbeamercolor{frametitle}{fg=white}
\setbeamercolor{structure}{fg=fwlSignal400}
\setbeamercolor{alerted text}{fg=fwlMagma400}
\setbeamercolor{item}{fg=fwlMagma400}
\setbeamerfont{normal text}{size=\fwlsize{34}}
\setbeamertemplate{itemize items}{\raisebox{0.15ex}{\small$\blacktriangleright$}}
\newcommand{\hl}[1]{\textcolor{fwlMagma400}{#1}}

% Grounds: ink-950; the [statement] frame option uses ink-980.
\newif\iffwl@statement
\newif\iffwl@titlepage
\define@key{beamerframe}{statement}[true]{\global\fwl@statementtrue}
% The ground holds for every overlay of a frame and resets at the next frame.
\BeforeBeginEnvironment{frame}{\global\fwl@statementfalse}
\setbeamertemplate{background canvas}{%
  \iffwl@statement
    \textcolor{fwlInk980}{\rule{\paperwidth}{\paperheight}}%
  \else
    \textcolor{fwlInk950}{\rule{\paperwidth}{\paperheight}}%
  \fi}

% Frame title: Geist Light, one line, top left
\setbeamertemplate{frametitle}{%
  \vspace*{\fpeval{40*0.2371}pt}%
  {\fwllight\fwlsize{72}\usebeamercolor[fg]{frametitle}\insertframetitle\par}%
  \vspace*{4pt}}

% References: \slideref{key1,key2}[left|right]; a corner stack grows upward from a fixed base.
\newcommand{\fwl@refl}{}
\newcommand{\fwl@refr}{}
\NewDocumentCommand{\slideref}{m O{left}}{%
  \ifstrequal{#2}{right}%
    {\xappto\fwl@refr{\unexpanded{\fwlcite{#1}\par}}}%
    {\xappto\fwl@refl{\unexpanded{\fwlcite{#1}\par}}}}
% Journal names on slides: \fwljournal{name in the .bib}{name on the slide}
\newcommand{\fwljournal}[2]{\csdef{fwl@j@\detokenize{#1}}{#2}}
\newcommand{\fwl@journal}[1]{\ifcsdef{fwl@j@\detokenize{#1}}{\csuse{fwl@j@\detokenize{#1}}}{#1}}
\fwljournal{Mon. Not. R. Astron. Soc.}{MNRAS}
\fwljournal{Monthly Notices of the Royal Astronomical Society}{MNRAS}
\fwljournal{Astrophys. J.}{ApJ}
\fwljournal{The Astrophysical Journal}{ApJ}
\fwljournal{Astrophys. J. Lett.}{ApJL}
\fwljournal{The Astrophysical Journal Letters}{ApJL}
\fwljournal{Astrophys. J. Suppl. Ser.}{ApJS}
\fwljournal{Astron. J.}{AJ}
\fwljournal{Astron. Astrophys.}{A\&A}
\fwljournal{Astronomy \& Astrophysics}{A\&A}
\fwljournal{Nat. Astron.}{Nature Astronomy}
\fwljournal{Planet. Sci. J.}{PSJ}
\fwljournal{The Planetary Science Journal}{PSJ}
\fwljournal{J. Geophys. Res. Planets}{JGR Planets}
\fwljournal{Earth Planet. Sci. Lett.}{EPSL}
\fwljournal{Annu. Rev. Earth Planet. Sci.}{AREPS}
\fwljournal{Annu. Rev. Astron. Astrophys.}{ARA\&A}
\fwljournal{Geochim. Cosmochim. Acta}{GCA}
\fwljournal{J. Open Source Softw.}{JOSS}
% ADS journal macros
\providecommand{\mnras}{MNRAS}\providecommand{\apj}{ApJ}\providecommand{\apjl}{ApJL}
\providecommand{\apjs}{ApJS}\providecommand{\aj}{AJ}\providecommand{\aap}{A\&A}
\providecommand{\nat}{Nature}\providecommand{\icarus}{Icarus}\providecommand{\araa}{ARA\&A}
\providecommand{\psj}{PSJ}\providecommand{\jgr}{JGR}\providecommand{\pasp}{PASP}

% "Teske+ 25 ApJL": 1 or 2 family names, else the first plus "+"; 2-digit year; journal in italics.
\DeclareNameFormat{fwlfamily}{%
  \namepartfamily\ifthenelse{\value{listcount}<\value{liststop}}{\addspace\&\addspace}{}}
\DeclareFieldFormat{fwlyy}{\StrRight{#1}{2}}
\newbibmacro{fwl:source}{%
  \iffieldundef{journaltitle}%
    {\iffieldundef{booktitle}{}{\addspace\mkbibemph{\printfield[noformat]{booktitle}}}}%
    {\addspace\edef\fwl@tmp{\thefield{journaltitle}}%
     \mkbibemph{\expandafter\fwl@journal\expandafter{\fwl@tmp}}}}
\DeclareCiteCommand{\fwlcite}{}%
  {\ifnumgreater{\value{labelname}}{2}%
     {\printnames[fwlfamily][1-1]{labelname}+}%
     {\printnames[fwlfamily]{labelname}}%
   \addspace\printfield[fwlyy]{year}\usebibmacro{fwl:source}}%
  {\par}{}

\newcommand{\fwl@refbox}[2]{% #1 alignment, #2 content
  \parbox[b]{\fpeval{900*0.2371}pt}{#1\fwlsize{24}\color{fwlInk300}\setlength{\parskip}{0pt}#2}}

% Footline: reference corners and slide number. It is drawn after the frame body,
% so \slideref works anywhere in a frame.
\setbeamertemplate{footline}{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[anchor=south west,inner sep=0] at ([xshift=6.6pt,yshift=6.6pt]current page.south west)
      {\fwl@refbox{\raggedright}{\fwl@refl}};
    \node[anchor=south east,inner sep=0] at ([xshift=-6.6pt,yshift=6.6pt]current page.south east)
      {\fwl@refbox{\raggedleft}{\fwl@refr}};
    \iffwl@titlepage\else
    \node[anchor=north west,inner sep=0,text=fwlInk400,font=\fwlsize{16}]
      at ([xshift=3.8pt,yshift=-2.4pt]current page.north west)
      {\insertframenumber};
    \fi
  \end{tikzpicture}%
  \gdef\fwl@refl{}\gdef\fwl@refr{}}

\newcommand{\fwl@logo}{%
  \node[anchor=south east,inner sep=0] (logo)
    at ([xshift=-\fpeval{18*0.2371}pt,yshift=\fpeval{50*0.2371}pt]current page.south east)
    {\includegraphics[height=\fpeval{100*0.2371}pt]{\fwlassetpath fwl-logo-white.png}};
  \node[anchor=north east,inner sep=0,text=fwlInk100,font=\fwlsize{17}]
    at ([yshift=-1pt]logo.south east) {formingworlds.space};}

% Title page: \title, \author (speaker), \date (venue and date),
% optional \fwlkeypapers{...}
\newcommand{\fwl@keypapers}{}
\newcommand{\fwlkeypapers}[1]{\renewcommand{\fwl@keypapers}{#1}}
\setbeamertemplate{title page}{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[anchor=north west,inner sep=0,text width=\fpeval{1600*0.2371}pt,
        font=\fwllight\fwlsize{120},text=white]
      at ([xshift=15.2pt,yshift=-\fpeval{70*0.2371}pt]current page.north west) {\inserttitle};
    \node[anchor=north east,inner sep=0,font=\fontseries{md}\selectfont\fwlsize{30},text=white]
      at ([xshift=-15.2pt,yshift=-\fpeval{330*0.2371}pt]current page.north east)
      {\addfontfeatures{LetterSpace=20}\MakeUppercase{\insertauthor}};
    \node[anchor=north west,inner sep=0,text width=\fpeval{760*0.2371}pt,font=\fwlsize{22},
        text=fwlInk100]
      at ([xshift=15.2pt,yshift=-\fpeval{470*0.2371}pt]current page.north west) {\fwl@keypapers};
    \node[anchor=south west,inner sep=0,align=left,font=\fwlsize{22},text=fwlInk100]
      at ([xshift=6.6pt,yshift=6.6pt]current page.south west) {\insertdate};
    \fwl@logo
  \end{tikzpicture}}

\newcommand{\titleframe}{{\fwl@titlepagetrue\begin{frame}\titlepage\end{frame}}}

% Question, section, statement and closing frames
\newcommand{\questionframe}[2][]{%
  \begin{frame}
    \begin{tikzpicture}[remember picture,overlay]
      \node[anchor=south,inner sep=0,text width=\fpeval{1760*0.2371}pt,align=center,
          font=\fwllight\fwlsize{88},text=white]
        at ([yshift=-\fpeval{380*0.2371}pt]current page.north) {#2};
      \node[anchor=north,inner sep=0,text width=\fpeval{1400*0.2371}pt,align=center,
          font=\fwllight\fwlsize{44},text=fwlInk100]
        at ([yshift=-\fpeval{400*0.2371}pt]current page.north) {#1};
    \end{tikzpicture}
  \end{frame}}
\newcommand{\sectionframe}[2]{%
  \begin{frame}
    \begin{tikzpicture}[remember picture,overlay]
      \node[anchor=north west,inner sep=0,font=\ttfamily\fwlsize{24},text=fwlMagma400]
        at ([xshift=15.2pt,yshift=-\fpeval{380*0.2371}pt]current page.north west)
        {\addfontfeatures{LetterSpace=15}\MakeUppercase{#1}};
      \node[anchor=north west,inner sep=0,text width=\fpeval{1500*0.2371}pt,
          font=\fwllight\fwlsize{96},text=white]
        at ([xshift=15.2pt,yshift=-\fpeval{430*0.2371}pt]current page.north west) {#2};
    \end{tikzpicture}
  \end{frame}}
\newcommand{\statementframe}[1]{%
  \begin{frame}[statement]
    \vfill\centering{\fwllight\itshape\fwlsize{64}\color{white}#1\par}\vfill
  \end{frame}}
\newcommand{\closingframe}[2][]{%
  \begin{frame}
    \begin{tikzpicture}[remember picture,overlay]
      \node[anchor=south,inner sep=0,text width=\fpeval{1600*0.2371}pt,align=center,
          font=\fwllight\fwlsize{88},text=white]
        at ([yshift=-\fpeval{380*0.2371}pt]current page.north) {#2};
      \node[anchor=north,inner sep=0,text width=\fpeval{1200*0.2371}pt,align=center,
          font=\fwllight\fwlsize{32},text=fwlInk100]
        at ([yshift=-\fpeval{400*0.2371}pt]current page.north) {#1};
      \fwl@logo
    \end{tikzpicture}
  \end{frame}}
% Figure frame: \figureframe{title}{side text}{image}; put \slideref in the side text.
\newcommand{\figureframe}[3]{%
  \begin{frame}{#1}
    \begin{tikzpicture}[remember picture,overlay]
      \node[anchor=center,inner sep=0]
        at ([xshift=\fpeval{288*0.2371}pt,yshift=-\fpeval{45*0.2371}pt]current page.center)
        {\includegraphics[width=\fpeval{1216*0.2371}pt,height=\fpeval{790*0.2371}pt,
          keepaspectratio]{#3}};
      \node[anchor=west,inner sep=0,text width=\fpeval{520*0.2371}pt,font=\fwllight\fwlsize{34},
          text=fwlInk100]
        at ([xshift=15.2pt,yshift=-\fpeval{(610-540)*0.2371}pt]current page.west) {#2};
    \end{tikzpicture}
  \end{frame}}
"""


def beamer_theme(release=None):
    """Return the text of ``beamerthemefwl.sty``.

    Parameters
    ----------
    release : datetime.date, optional
        Date written into ``\\ProvidesPackage``. Defaults to 2026-10-18 so the
        generated file does not change from day to day.

    Returns
    -------
    str
        LaTeX package source.
    """
    release = release or date(2026, 10, 18)
    head = [
        f"% Forming Worlds Lab beamer theme (fwl-visual-language {__version__}). Generated; edit",
        "% the generator, not this file. Compile with lualatex; references with bibtex.",
        "\\NeedsTeXFormat{LaTeX2e}",
        f"\\ProvidesPackage{{beamerthemefwl}}[{release:%Y/%m/%d} v{__version__} "
        "Forming Worlds Lab]",
    ]
    return "\n".join(head) + "\n" + _BODY


def install_beamer(dest):
    """Write the beamer theme, ``fwl.sty``, the fonts and the logo into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Folder of the talk. It is created if it does not exist.

    Returns
    -------
    pathlib.Path
        Path of the written theme file.

    Raises
    ------
    OSError
        If ``dest`` exists and is not a folder, or a file cannot be copied.
    """
    dest = Path(dest)
    install_latex(dest)
    for file in _LIGHT:
        shutil.copyfile(fonts_dir() / "ttf" / file, dest / FONT_DIR / file)
    assets = dest / ASSET_DIR
    assets.mkdir(exist_ok=True)
    shutil.copyfile(assets_dir() / _LOGO, assets / _LOGO)
    out = dest / THEME_NAME
    out.write_text(beamer_theme(), encoding="utf-8")
    return out


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.beamer DEST``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.beamer",
        description="Write the Forming Worlds Lab beamer theme, fonts and logo.",
    )
    parser.add_argument("dest", help="folder of the talk")
    args = parser.parse_args(argv)
    print(install_beamer(args.dest))


if __name__ == "__main__":
    main()
