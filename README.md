# fwl-visual-language

Visual identity of the Forming Worlds Lab: one set of design tokens and the themes generated from it for the website, figures, documentation and documents.

The tokens start from [formingworlds.space](https://www.formingworlds.space): the cool `ink` neutrals, the logo blue `signal` (`#0072A1`) and the warm `magma` accent. Words are set in [Geist](https://github.com/vercel/geist-font); math symbols and Greek letters, which Geist does not have, in [Inter](https://github.com/rsms/inter); code in Geist Mono. In LaTeX, math letters, digits and Greek come from Inter and operators, delimiters and large symbols from [STIX Two Math](https://github.com/stipub/stixfonts).

## What is in it

| File in `themes/` | For | Install |
|---|---|---|
| `css/fwl-tokens.css` | any web page: every colour step and role as a `--fwl-*` variable, dark by default, light (mist ground) with `data-theme="light"` or the visitor's system setting; it names the fonts but loads none, so add `fwl-fonts.css` | link it |
| `css/fwl-tailwind-theme.css` | the lab website: the Tailwind v4 `@theme` block | import it |
| `css/fwl-tailwind-light.css` | the lab website: the light theme over the same variables (system setting or `data-theme="light"`), and `.on-dark` for areas that stay dark | import it right after `@import "tailwindcss"` |
| `css/fwl-fonts.css` | self-hosted web fonts | `python -m fwl_visual_language.css static/css` |
| `mpl/fwl-paper.mplstyle`, `mpl/fwl-dark.mplstyle` | matplotlib figures, through [fwl-mpl](https://github.com/FormingWorlds/fwl-mpl) | |
| `documenter/fwl.css` | Documenter.jl sites, light and dark | `python -m fwl_visual_language.documenter docs/src/assets` |
| `jupyterbook/fwl-jupyterbook.css` | Jupyter Book 1 (sphinx-book-theme), light and dark | `python -m fwl_visual_language.jupyterbook book/_static` |
| `latex/fwl.sty` | colours and fonts for letters, proposals and the CV with LuaLaTeX or XeLaTeX; `\usepackage[math]{fwl}` (or `\fwlusemath` in the preamble) adds the Inter and STIX Two math | `python -m fwl_visual_language.latex path/to/document` |
| `latex/fwlproposal.sty` | page style of proposals and reports: A4 with 2 cm margins, numbered headings, captions, links, footer (`\fwltitle{title}{subtitle}`, `\renewcommand{\fwlfooter}{...}`); loads `fwl` with `math` | same command |
| `beamer/beamerthemefwl.sty` | LaTeX talks (`\usetheme{fwl}`), LuaLaTeX and BibTeX | `python -m fwl_visual_language.beamer path/to/talk` |

The install commands copy the fonts and their licences next to the stylesheet or package. The Documenter.jl and Jupyter Book themes keep the stock layouts and change only colours and type. For Documenter.jl, add `"assets/fwl.css"` to `Documenter.HTML(; assets=[...])`; Jupyter Book 1 picks up every stylesheet in `_static` by itself.

## Colours

The figure palette has 8 colours. Colour 1 is signal and colour 2 is magma, the website steps that read on each ground (signal-500 and magma-600 on white, signal-400 and magma-400 on the dark ground); the other 6 are fitted around them so that the closest pair stays apart for readers with red-green or blue-yellow colour-vision deficiency (smallest CAM02-UCS distance over normal vision and full deuteranomaly, protanomaly and tritanomaly: 15.0 on white, 11.0 on the dark ground). The tests hold these floors, a 3:1 contrast on white for every colour of the light palette and 4.5:1 on the dark ground. On the pale mist ground of the website's light theme, fern and ochre fall to about 2.8:1, so charts on a light-theme page sit on a white surface (`--fwl-surface`).

| | signal | magma | fern | iris | ochre | lagoon | garnet | ink |
|---|---|---|---|---|---|---|---|---|
| paper | `#0072A1` | `#B74B21` | `#20A976` | `#4E2585` | `#BC8D03` | `#124F54` | `#741721` | `#6E747A` |
| dark | `#4DAAD8` | `#F1935B` | `#6AE7AD` | `#7E66C3` | `#F3C451` | `#4A8289` | `#C25656` | `#BACAD7` |

The matplotlib styles set batlow from the [Crameri scientific colour maps](https://www.fabiocrameri.ch/colourmaps/) as the default map; it is registered as `cmc.batlow` once `cmcrameri` is imported. The token file also names the diverging defaults (vik on paper, berlin on dark) and the stops of 2 optional lab maps, ember and tide, for packages that build colour maps.

All `oklch()` steps lie inside sRGB, so every browser and screen shows the same colour.

The website's light theme reassigns the ramp steps instead of changing classes. `website_light` in the token file gives the light value of each step: another step (`"ink-950"`), a hex literal, or an OKLCH list (`[L, C]` on the ramp's hue, or `[L, C, h]`) for a hover step that sits between 2 ramp steps. The light rules are not in a cascade layer, so they win over Tailwind's `@theme` layer wherever the import sits.

## Slides

The slide masters are a PowerPoint file with 10 layouts (`Title`, `Question`, `Section`, `Figure`, `Figure, large`, `Two figures`, `Summary`, `Statement`, `Team`, `Closing`), a Keynote source made from the same layouts, and a beamer theme with frames for the title, a question, a section, a figure, a statement and the closing slide. Every slide sits on the ink-950 ground (statements on ink-980) and takes figures in the dark figure style; the masters have no background picture, so a talk can add its own. Titles are one line of Geist Light. Key words take magma-400.

Every figure layout has 2 reference boxes, bottom left and bottom right, in 24 pt on the 1920 x 1080 design; the Summary layout has one reference box per point. A box is anchored at its base, so several references stack upward and never run off the slide. The format is `Teske+ 25 ApJL`: 1 or 2 family names (`Lichtenberg & Miguel 25`) with any prefix such as `van`, else the first plus `+` (also for `and others`), a 2-digit year with the letter that tells papers of one author and year apart (`Smith 25a`, `Smith 25b`), and the journal in italics.

```bash
pip install "fwl-visual-language[slides]"
python -m fwl_visual_language.slides "Forming Worlds.pptx"                   # PowerPoint, Google Slides
python -m fwl_visual_language.slides fwl-keynote-source.pptx --keynote      # Keynote source
```

The PowerPoint file is 13.333 x 7.5 in; its figure boxes are content placeholders, not picture placeholders. Google Slides imports `.pptx` files; this one has not been tried there. The Keynote source is 1920 x 1080 pt without figure boxes, because Keynote removes them on import. Open it in Keynote and save it; Keynote turns the layouts into master slides, and a copy of the saved file with the extension `.kth` is the theme: Keynote makes a new presentation with all 10 masters from it. Keynote and PowerPoint need the Geist and Geist Mono fonts installed on the computer (the masters use Geist, Geist Light, Geist Medium and Geist Mono).

The built files are in `templates/`: `Forming Worlds.pptx` for PowerPoint and Google Slides, and `Forming Worlds.kth` for Keynote. Their sample figure slides show `templates/sample-figure.png`, example plots of made-up data and a colour-vision swatch grid in the dark figure style.

- `Forming Worlds.pptx` must have the same parts as a fresh build (zip time stamps aside); a test checks it. Rebuild it with `python -m fwl_visual_language.slides "templates/Forming Worlds.pptx" --figure templates/sample-figure.png`.
- `Forming Worlds.kth` needs Keynote; this one was saved with Keynote 15.4. `templates/keynote-source.sha256` records a hash of the parts of the Keynote source the theme was made from (`source`, zip time stamps aside) and the SHA-256 of the theme file (`kth`). The tests fail when the builder writes a different source or when the theme file differs from the recorded one; they cannot check that the theme was made from that source, which the person who records both hashes vouches for. After a change to the slides, run from the repository root, with the checkout installed (`pip install -e ".[slides]"`): `python -m fwl_visual_language.slides ~/fwl-keynote-source.pptx --keynote --figure templates/sample-figure.png` (outside the repository, so the source is not committed), open it in Keynote and save it, copy the saved file to `templates/Forming Worlds.kth`, and write the `source` and `kth` lines that the failing tests print to `keynote-source.sha256`. The figure file name is part of the `source` hash (python-pptx writes it as the picture description), but it does not appear in this theme.

In beamer, `\slideref{key}` puts a reference from the bibliography in the bottom left corner and `\slideref{key}[right]` in the bottom right one; one call can take several keys; an unknown key prints the key itself. `\fwljournal{name in the .bib}{name on the slide}` adds a journal name to the list that maps, for example, `Mon. Not. R. Astron. Soc.` to `MNRAS`; the common ADS journal macros (`\mnras`, `\apjl`, ...) are defined at `\begin{document}` where the preamble defines none. `\fwlhl{word}` sets a key word in magma-400, also as `\hl` when the preamble (for example `soul`) defines no `\hl`. Put `\slideref` inside a frame; the title and closing frames keep their bottom right corner for the logo. The frames are `\titleframe`, `\questionframe[sub-question]{question}`, `\sectionframe{label}{statement}`, `\figureframe{title}{side text}{image}`, `\statementframe{text}`, `\closingframe[announcement]{statement}`, ordinary frames, and `[statement]` frames on ink-980. `[plain]` frames have no reference corners. Compile with `lualatex`, `bibtex`, then `lualatex` twice.

## Word

```bash
pip install "fwl-visual-language[word]"
python -m fwl_visual_language.word templates
```

The command writes Word templates for 5 kinds of document, each in 2 faces: `Forming Worlds Letter`, `Forming Worlds University Letter`, `Forming Worlds Report`, `Forming Worlds Memo` and `Forming Worlds Handbook`, in Geist for documents that leave as PDF and in Aptos, the Office default, for documents that others edit without the lab fonts. The built `.dotx` files are in `templates/`, and a test checks that each one matches a fresh build.

Text, headings, lists, notes and captions use named styles, among them Normal, Title, Subtitle, Heading 1 to 3 (Heading 1 and 2 numbered, with the numbers in signal blue), Caption, List Bullet, List Number and List Number 2, Note, Key word (magma), Hyperlink and the contents styles, so typed text keeps the lab look. The Headings and Body theme fonts are set too, to the medium and the regular face (Geist Medium and Geist, or Aptos SemiBold and Aptos). The theme colours are ink-900 and ink-700 for text, white and ink-50 for the ground, magma-600 and signal-500 as accents 1 and 2 (magma first, as on the slides, with the paper steps instead of the dark-ground steps), then the paper-palette fern, ochre, iris and garnet, with links underlined in signal-500 and followed links underlined in iris. The text colour is a document default, so the table styles of Word set their own text colour: Medium Shading 1 sets white header text on an accent fill, Dark List sets white text on accent fills in every row, and Light Shading sets the whole table in a darker shade of the accent. White on fern and on ochre reaches a contrast of 3:1, below the 4.5:1 that small text needs, so a table with white text on an accent fill uses the other accents. The letter has the lab logo and the sender block on its first page; the university letter has the banner of the University of Groningen, the Faculty of Science and Engineering and the Kapteyn Astronomical Institute, with the lab logo in the footer. Both letters set their body text justified; dates, subjects, headings and captions stay left-aligned. The handbook has a cover with a welcome note, a contents field (right-click it and choose Update Field) and chapters that start on a new page.

In Word for Mac, export a Geist document to PDF with *Best for printing*. The other choice, for electronic distribution, renders through a Microsoft online service; in a test with Word 16.113 it replaced Geist with other fonts. Geist must be installed on the computer; Word 16.113 ships with Aptos.

## Social media

```bash
pip install "fwl-visual-language[social]"
python -m fwl_visual_language.social cards.json cards/
```

The command renders square 1080 px PNG cards for Bluesky, Mastodon, Instagram and LinkedIn, set in Geist on the ink ground or on a photo darkened towards ink, with signal-blue labels and the lab logo. `cards.json` holds a `cards` list; each entry names its `card`, its output `file` (the name without `.png`) and the arguments of that card. Image paths resolve next to the JSON file, or in the folder that an optional `base` key names relative to it. The example needs `first-author.jpg` next to `cards.json`:

```json
{"cards": [
  {"card": "paper", "file": "paper", "photo": "first-author.jpg", "title": "Title of the paper",
   "authors": ["First Author", "Second Author", "Third Author", "Fourth Author"], "lab": ["Fourth Author"]},
  {"card": "glance", "file": "glance", "text": "The At a glance text of the paper.", "ref": "arXiv:0000.00000"}
]}
```

| Card | Holds |
|---|---|
| `paper` | the first author's photo, the paper title, and the first 3 authors, the number of the others and every lab member among them ("and 10 co-authors, incl. ...") |
| `glance` | the At a glance text of the paper, up to 15 lines |
| `figure` | a headline, the figure on a white panel and its source |
| `cover` | the question the paper answers, as the first slide of a carousel |
| `member` | a member's photo with the name and up to 2 short lines |
| `event` | a conference with up to 7 lab contributions |
| `highlight` | an Instagram Story Highlight cover from a square detail of an artwork |

Every text is measured: a text that does not fit its card, a lab member who is not among the authors, or an unknown key stops the command with an error before a wrong card goes out. The command checks the whole list before it writes the first card. Photos and artwork are not in this repository; the cards take them from the caller.

## Develop

```bash
python -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/python -m fwl_visual_language build   # regenerate themes/ after a token change
.venv/bin/python -m pytest
```

`tokens/fwl.json` inside the package is the only source. `python -m fwl_visual_language check` fails when a file in `themes/` does not match the tokens or does not belong there.

## Licence

Code and tokens: Apache 2.0. Geist, Geist Mono, Inter and STIX Two Math: SIL Open Font License 1.1, bundled unmodified with their licence texts in `src/fwl_visual_language/fonts/`. The logo in `src/fwl_visual_language/assets/`, also on the slide templates in `templates/`, is the mark of the Forming Worlds Lab, as on formingworlds.space. It is not covered by the Apache 2.0 or OFL licences of this repository; use it only for material of the Forming Worlds Lab. The banner `rug-banner.png` in the same folder, which the university letter templates embed, carries the marks of the University of Groningen, its Faculty of Science and Engineering and the Kapteyn Astronomical Institute. It ships in the package with the other assets, it is not covered by these licences, and this repository grants no permission for it: use it only as the university's rules for these marks allow.
