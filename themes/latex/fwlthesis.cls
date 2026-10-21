% Forming Worlds Lab thesis class (fwl-visual-language 0.2.0). Generated; edit the generator, not this file.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{fwlthesis}[2026/10/21 v0.2.0 Forming Worlds Lab]
\newif\iffwl@final
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
% Contents and lists on their own pages; unnumbered sections after the contents enter it
\newif\iffwl@listed
\renewcommand{\tableofcontents}{\section*{\contentsname}\@starttoc{toc}\global\fwl@listedtrue}
\renewcommand{\listoffigures}{\section*{\listfigurename}\@starttoc{lof}}
\renewcommand{\listoftables}{\section*{\listtablename}\@starttoc{lot}}
\renewcommand{\bibsection}{\section*{\refname}}

\DeclareCaptionFont{fwlmuted}{\color{fwlMuted}}
\DeclareCaptionFont{fwlheading}{\fwlmedium\color{fwlHeading}}
\captionsetup{font={small,fwlmuted},labelfont=fwlheading,labelsep=period,singlelinecheck=false}

% Running head: the title at the left, the current section at the right
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\sectionmark}[1]{\markboth{\thesection\quad#1}{}}
\fancyhead[L]{\ttfamily\footnotesize\color{fwlMuted}\fwl@short}
\fancyhead[R]{\ttfamily\footnotesize\color{fwlMuted}\leftmark}
\fancyfoot[R]{\ttfamily\footnotesize\color{fwlMuted}\thepage}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[R]{\ttfamily\footnotesize\color{fwlMuted}\thepage}}
% Every section opens a new page, also one that follows another heading directly
\AtBeginDocument{\let\fwl@section\section
  \renewcommand{\section}{\clearpage\@ifstar{\fwl@starred}{\fwl@section}}}
\newcommand{\fwl@starred}[1]{\iffwl@listed\phantomsection\fi\fwl@section*{#1}\markboth{#1}{}%
  \iffwl@listed\addcontentsline{toc}{section}{#1}\fi}
% A head title wider than 0.55 of the text width needs a shorter \shorttitle
\AtBeginDocument{\begingroup\let\\\relax
  \settowidth{\@tempdima}{\ttfamily\footnotesize\fwl@short}%
  \ifdim\@tempdima>0.55\textwidth\ClassWarningNoLine{fwlthesis}{The title is too wide
    for the running head; give a shorter one with \protect\shorttitle}\fi\endgroup}

% Title page
\newcommand{\fwl@type}{}\newcommand{\fwl@snum}{}\newcommand{\fwl@sup}{}
\newcommand{\fwl@short}{\@title}
\newcommand{\thesistype}[1]{\renewcommand{\fwl@type}{#1}}
\newcommand{\shorttitle}[1]{\renewcommand{\fwl@short}{#1}}
\newcommand{\studentnumber}[1]{\renewcommand{\fwl@snum}{#1}}
\newcommand{\supervisors}[1]{\renewcommand{\fwl@sup}{#1}}
\renewcommand{\maketitle}{\begin{titlepage}\thispagestyle{empty}%
  \includegraphics[width=\textwidth]{\fwlassetpath rug-banner-ink.png}\par
  \vspace*{5.5cm}
  {\fwlmedium\color{fwlAccent}\fwl@type\par}\vspace{0.8em}
  {\raggedright\hyphenpenalty=10000\fwllightface\fontsize{30}{36}\selectfont
    \color{fwlHeading}\@title\par}\vspace{1em}
  {\color{fwlAccent}\rule{3cm}{0.8pt}}\par\vspace{1.2em}
  {\large\fwlmedium\color{fwlHeading}\@author\par}{\color{fwlMuted}\fwl@snum\par}\vspace{1.6em}
  {\color{fwlMuted}\small\begin{tabular}{@{}l@{\hspace{1.2em}}l@{}}\fwl@sup\end{tabular}\par}
  \vfill
  \begin{minipage}[b]{5cm}\includegraphics[width=3.4cm]{\fwlassetpath fwl-logo-ink.png}\par
    \vspace{0.35em}{\ttfamily\small\color{fwlMuted}formingworlds.space}\end{minipage}\hfill
  {\color{fwlMuted}\small Groningen, \@date}\par
\end{titlepage}}

% Grey guidance; the final option hides all of it
\newcommand{\guide}[1]{\iffwl@final\ignorespaces\else
  \par{\small\emergencystretch=3em\color{fwlInk500}#1\par}\medskip\fi}
\newcommand{\guidesection}[1]{\iffwl@final\else\section*{#1}\fi}
% Code in guidance; \allowbreak inside it marks where a long command may break
\newcommand{\guidecmd}[1]{\texttt{#1}}
% Where the data and the script of a figure are published
\newcommand{\figuredata}[1]{ Data and script: \url{#1}.}

% ADS journal macros, at \begin{document} and only where the preamble defines none
\AtBeginDocument{%
\providecommand{\aj}{AJ}\providecommand{\araa}{ARA\&A}\providecommand{\apj}{ApJ}
\providecommand{\apjl}{ApJL}\providecommand{\apjs}{ApJS}\providecommand{\apss}{Ap\&SS}
\providecommand{\aap}{A\&A}\providecommand{\aapr}{A\&A Rv}\providecommand{\aaps}{A\&AS}
\providecommand{\baas}{BAAS}\providecommand{\icarus}{Icarus}\providecommand{\jcap}{JCAP}
\providecommand{\jgr}{JGR}\providecommand{\grl}{GRL}\providecommand{\gca}{GCA}
\providecommand{\jqsrt}{JQSRT}\providecommand{\mnras}{MNRAS}\providecommand{\nat}{Nature}
\providecommand{\na}{New Astron.}\providecommand{\pasa}{PASA}\providecommand{\pasj}{PASJ}
\providecommand{\pasp}{PASP}\providecommand{\planss}{Planet. Space Sci.}\providecommand{\psj}{PSJ}
\providecommand{\prd}{Phys. Rev. D}\providecommand{\prl}{Phys. Rev. Lett.}
\providecommand{\physrep}{Phys. Rep.}\providecommand{\procspie}{Proc. SPIE}
\providecommand{\solphys}{Sol. Phys.}\providecommand{\ssr}{Space Sci. Rev.}}
\endinput
