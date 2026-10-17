"""Forming Worlds Lab visual identity: design tokens and the themes built from them.

The single source is ``tokens/fwl.json`` in the package. It holds the colour
ramps of the lab website (``ink``, ``signal``, ``magma``) in OKLCH, semantic
roles for the dark, light and paper themes, the 8-colour figure palette, the
colour map stops and the font roles. The modules in this package turn the
tokens into a theme for each medium; ``python -m fwl_visual_language build``
writes all of them into ``dist/``.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

__version__ = "0.1.0"

__all__ = [
    "MODES",
    "color",
    "contrast",
    "fonts_dir",
    "hex_to_rgb",
    "oklch_css",
    "oklch_to_hex",
    "palette",
    "ramp",
    "role",
    "roles",
    "tokens",
]

HERE = Path(__file__).parent
TOKENS = HERE / "tokens" / "fwl.json"
MODES = ("dark", "light", "paper")


@lru_cache(maxsize=1)
def tokens():
    """Return the parsed token file.

    Returns
    -------
    dict
        The content of ``tokens/fwl.json``. Callers must not mutate it; it is
        cached for the session.
    """
    return json.loads(TOKENS.read_text(encoding="utf-8"))


def fonts_dir():
    """Return the folder that holds the bundled fonts (``ttf/`` and ``woff2/``).

    Returns
    -------
    pathlib.Path
        Folder with the unmodified Geist, Geist Mono and Inter files and their
        licences.
    """
    return HERE / "fonts"


def _oklch_to_linear(L, C, h):
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )


def _encode(c):
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch_to_hex(L, C, h):
    """Convert an OKLCH colour to sRGB hex, lowering chroma until it fits sRGB.

    Parameters
    ----------
    L : float
        OKLab lightness, 0 to 1.
    C : float
        Chroma, 0 or more.
    h : float
        Hue angle in degrees.

    Returns
    -------
    str
        Upper-case ``#RRGGBB``.

    Notes
    -----
    Out-of-gamut colours keep their lightness and hue; the chroma drops in
    0.001 steps until all channels lie in [0, 1] within 1e-4. This follows the
    chroma-reduction idea of CSS Color 4 gamut mapping, without its
    just-noticeable-difference shortcut, so a browser can render an
    out-of-gamut ``oklch()`` value up to about one hex step differently.
    """
    if C < 0:
        raise ValueError(f"chroma must be >= 0, got {C}")
    while True:
        lin = _oklch_to_linear(L, C, h)
        if all(-1e-4 <= v <= 1 + 1e-4 for v in lin) or C <= 0:
            break
        C = max(C - 0.001, 0.0)
    return "#" + "".join(f"{round(_encode(v) * 255):02X}" for v in lin)


def hex_to_rgb(value):
    """Convert ``#RRGGBB`` to a tuple of 3 floats in [0, 1].

    Parameters
    ----------
    value : str
        Hex colour with or without the leading ``#``.

    Returns
    -------
    tuple of float
        Red, green and blue.

    Raises
    ------
    ValueError
        If the string is not 6 hex digits.
    """
    h = value.lstrip("#")
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise ValueError(f"not a #RRGGBB colour: {value!r}")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(value):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in hex_to_rgb(value)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """Return the WCAG 2 contrast ratio of 2 hex colours (1 to 21).

    Parameters
    ----------
    a, b : str
        Hex colours.

    Returns
    -------
    float
        Contrast ratio, order-independent.
    """
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _step_oklch(name, step):
    ramp_def = tokens()["ramps"][name]
    value = ramp_def["steps"][step]
    if isinstance(value, str):
        return None
    if len(value) == 3:
        return tuple(value)
    return (value[0], value[1], ramp_def["hue"])


def oklch_css(name, step):
    """Return the CSS ``oklch()`` form of a ramp step, as the website writes it.

    Parameters
    ----------
    name : str
        Ramp name: ``ink``, ``signal`` or ``magma``.
    step : str
        Step key, for example ``"500"``.

    Returns
    -------
    str
        ``oklch(L C h)`` with 3 decimals, or the hex value for a step that the
        tokens define as hex (the logo blue, ``signal-500``).
    """
    lch = _step_oklch(name, step)
    if lch is None:
        return tokens()["ramps"][name]["steps"][step].upper()
    L, C, h = lch
    return f"oklch({L:.3f} {C:.3f} {h:g})"


def ramp(name):
    """Return a ramp as an ordered mapping of step to hex colour.

    Parameters
    ----------
    name : str
        Ramp name: ``ink``, ``signal`` or ``magma``.

    Returns
    -------
    dict
        Step key to ``#RRGGBB``, in the order of the token file.

    Raises
    ------
    KeyError
        If the ramp does not exist.
    """
    steps = tokens()["ramps"][name]["steps"]
    out = {}
    for step, value in steps.items():
        lch = _step_oklch(name, step)
        out[step] = value.upper() if lch is None else oklch_to_hex(*lch)
    return out


def color(ref):
    """Resolve a token reference such as ``"signal-600"`` to a hex colour.

    Parameters
    ----------
    ref : str
        ``<ramp>-<step>``, or a literal ``#RRGGBB``.

    Returns
    -------
    str
        Upper-case ``#RRGGBB``.

    Raises
    ------
    KeyError
        If the ramp or step does not exist.
    """
    if ref.startswith("#"):
        hex_to_rgb(ref)
        return ref.upper()
    name, _, step = ref.partition("-")
    steps = ramp(name)
    if step not in steps:
        raise KeyError(f"{name} has no step {step!r}; steps: {', '.join(steps)}")
    return steps[step]


def roles(mode):
    """Return all semantic roles of a theme mode as hex colours.

    Parameters
    ----------
    mode : str
        ``dark`` (the website default), ``light`` (website light theme, mist
        ground) or ``paper`` (white ground, for papers and documents).

    Returns
    -------
    dict
        Role name to ``#RRGGBB``.

    Raises
    ------
    ValueError
        If the mode is unknown.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    return {k: color(v) for k, v in tokens()["roles"][mode].items()}


def role(mode, name):
    """Return one semantic role of a mode as a hex colour.

    Parameters
    ----------
    mode : str
        Theme mode, see :func:`roles`.
    name : str
        Role name, for example ``"link"``.

    Returns
    -------
    str
        ``#RRGGBB``.
    """
    return roles(mode)[name]


def palette(mode="paper"):
    """Return the 8-colour figure palette for a mode.

    Parameters
    ----------
    mode : str
        ``paper`` and ``light`` use the light-ground palette, ``dark`` the
        dark-ground one.

    Returns
    -------
    list of tuple
        ``(name, hex)`` pairs in cycle order; colour 1 is signal, colour 2 magma.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    p = tokens()["palette"]
    key = "dark" if mode == "dark" else "light"
    return list(zip(p["names"], [h.upper() for h in p[key]], strict=True))
