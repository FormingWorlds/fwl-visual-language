# fwl-visual-language

Visual identity of the Forming Worlds Lab: one set of design tokens and the themes generated from it for the website, figures, documentation and documents.

The tokens start from [formingworlds.space](https://www.formingworlds.space): the cool `ink` neutrals, the logo blue `signal` (`#0072A1`) and the warm `magma` accent. Words are set in [Geist](https://github.com/vercel/geist-font); math symbols and Greek letters, which Geist does not have, in [Inter](https://github.com/rsms/inter); code in Geist Mono.

## What is in it

| File in `dist/` | For | Install |
|---|---|---|
| `css/fwl-tokens.css` | any web page: every colour step and role as a `--fwl-*` variable, dark by default, light (mist ground) with `data-theme="light"` or the visitor's system setting | link it |
| `css/fwl-tailwind-theme.css` | the lab website: the Tailwind v4 `@theme` block | import it |
| `css/fwl-fonts.css` | self-hosted web fonts | copy with the `woff2` files |
| `mpl/fwl-paper.mplstyle`, `mpl/fwl-dark.mplstyle` | matplotlib figures, through [fwl-mpl](https://github.com/FormingWorlds/fwl-mpl) | |
| `documenter/fwl.css` | Documenter.jl sites, light and dark | `python -m fwl_visual_language.documenter docs/src/assets` |
| `jupyterbook/fwl-jupyterbook.css` | Jupyter Book 1 (sphinx-book-theme), light and dark | `python -m fwl_visual_language.jupyterbook book/_static` |
| `latex/fwl.sty` | letters, proposals and the CV with LuaLaTeX or XeLaTeX | `python -m fwl_visual_language.latex path/to/document` |

The install commands copy the fonts and their licences next to the stylesheet or package. The Documenter.jl and Jupyter Book themes keep the stock layouts and change only colours and type. For Documenter.jl, add `"assets/fwl.css"` to `Documenter.HTML(; assets=[...])`; Jupyter Book 1 picks up every stylesheet in `_static` by itself.

## Colours

The figure palette has 8 colours. Colour 1 is signal and colour 2 is magma; the other 6 are fitted around them so that the closest pair stays apart for readers with red-green or blue-yellow colour-vision deficiency (smallest CAM02-UCS distance over normal vision and full deuteranomaly, protanomaly and tritanomaly: 15.0 on white, 11.0 on the dark ground). The tests hold these floors and a 3:1 contrast against the background for every line colour.

| | signal | magma | fern | iris | ochre | lagoon | garnet | ink |
|---|---|---|---|---|---|---|---|---|
| paper | `#0172A1` | `#B74B21` | `#20A976` | `#4E2585` | `#BC8D03` | `#124F54` | `#741721` | `#6E747A` |
| dark | `#4DAAD8` | `#F1935B` | `#6AE7AD` | `#7E66C3` | `#F3C451` | `#4A8289` | `#C25656` | `#BACAD7` |

Colour maps default to the [Crameri scientific colour maps](https://www.fabiocrameri.ch/colourmaps/): batlow for sequential data, vik (paper) and berlin (dark) for diverging data.

All `oklch()` steps lie inside sRGB, so every browser and screen shows the same colour.

## Develop

```bash
python -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/python -m fwl_visual_language build dist   # regenerate after a token change
.venv/bin/python -m pytest
```

`tokens/fwl.json` inside the package is the only source. `python -m fwl_visual_language check dist` fails when a file in `dist/` does not match the tokens.

## Licence

Code and tokens: Apache 2.0. Geist, Geist Mono and Inter: SIL Open Font License 1.1, bundled unmodified with their licence texts in `src/fwl_visual_language/fonts/`.
