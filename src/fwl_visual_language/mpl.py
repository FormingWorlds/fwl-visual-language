"""Matplotlib style sheets for lab figures, paper (white ground) and dark.

Words are set in Geist; math symbols and Greek letters in Inter, which has the
Greek that Geist lacks; plain-text Greek outside math falls back to Inter per
glyph. The layout (figure size, open axes, outward ticks, type sizes) is the
one of the fwl-mpl package, which loads these sheets and registers the fonts.
"""

from . import __version__, palette, roles, tokens

__all__ = ["MPL_MODES", "mplstyle"]

MPL_MODES = ("paper", "dark")

_TEMPLATE = """\
## Forming Worlds Lab figure style, {mode} mode (fwl-visual-language {version}).
## Generated from the lab tokens; edit tokens/fwl.json, not this file.

## Figure: one column of a two-column page; PDF and PS embed TrueType fonts,
## SVG draws text as paths so it renders without the fonts installed
figure.figsize: 3.5, 2.6
figure.dpi: 150
figure.constrained_layout.use: True
figure.facecolor: {background}
savefig.facecolor: {background}
savefig.dpi: 300
pdf.fonttype: 42
ps.fonttype: 42
svg.fonttype: path

## Type: Geist for words, Inter for math and Greek
font.family: {text_font}, {math_font}, DejaVu Sans
font.monospace: {mono_font}, DejaVu Sans Mono
font.size: 8.5
mathtext.fontset: custom
mathtext.rm: {math_font}
mathtext.sf: {math_font}
mathtext.it: {math_font}:italic
mathtext.bf: {math_font}:medium
mathtext.bfit: {math_font}:italic:medium
mathtext.cal: {math_font}:italic
mathtext.fallback: stixsans
axes.unicode_minus: True

## Colours
axes.prop_cycle: cycler('color', [{cycle}])
image.cmap: cmc.{cmap}
axes.facecolor: {background}
axes.edgecolor: {axis}
axes.labelcolor: {heading}
text.color: {heading}
xtick.color: {axis}
ytick.color: {axis}
xtick.labelcolor: {heading}
ytick.labelcolor: {heading}
grid.color: {line}
legend.labelcolor: {heading}
boxplot.boxprops.color: {heading}
boxplot.whiskerprops.color: {heading}
boxplot.capprops.color: {heading}
boxplot.flierprops.markeredgecolor: {heading}
errorbar.capsize: 0

## Axes: open frame, outward ticks, no grid
axes.spines.top: False
axes.spines.right: False
axes.linewidth: 0.6
axes.grid: False
axes.titlesize: 9.5
axes.titleweight: medium
axes.titlelocation: left
axes.labelsize: 9
axes.labelpad: 3
xtick.direction: out
ytick.direction: out
xtick.labelsize: 8
ytick.labelsize: 8
xtick.major.size: 3
ytick.major.size: 3
xtick.minor.size: 1.6
ytick.minor.size: 1.6
xtick.major.width: 0.6
ytick.major.width: 0.6
xtick.minor.width: 0.5
ytick.minor.width: 0.5
xtick.minor.visible: True
ytick.minor.visible: True
grid.linewidth: 0.5

## Marks
lines.linewidth: 1.3
lines.markersize: 3.5
patch.linewidth: 0.5
scatter.edgecolors: face

## Legend
legend.frameon: False
legend.fontsize: 8
legend.title_fontsize: 8
legend.handlelength: 1.4
legend.borderaxespad: 0.3
"""


def mplstyle(mode="paper"):
    """Return the matplotlib style sheet text for a mode.

    Parameters
    ----------
    mode : str
        ``paper`` (white ground, light palette) or ``dark`` (ink-950 ground,
        dark palette).

    Returns
    -------
    str
        Content of a ``.mplstyle`` file. Colours are written without ``#``, as
        matplotlib style files require.

    Raises
    ------
    ValueError
        If the mode is not ``paper`` or ``dark``.
    """
    if mode not in MPL_MODES:
        raise ValueError(f"mode must be one of {MPL_MODES}, got {mode!r}")
    r = roles(mode)
    fonts = tokens()["fonts"]
    maps = tokens()["colormaps"]["default"]
    cycle = ", ".join(f"'{h[1:]}'" for _, h in palette(mode))
    return _TEMPLATE.format(
        mode=mode,
        version=__version__,
        background=r["background"][1:],
        heading=r["heading"][1:],
        axis=r["axis"][1:],
        line=r["line"][1:],
        text_font=fonts["text"],
        math_font=fonts["math"],
        mono_font=fonts["mono"],
        cycle=cycle,
        cmap=maps["sequential"],
    )
