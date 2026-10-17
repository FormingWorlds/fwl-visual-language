"""Command line: ``python -m fwl_visual_language build [DIR]`` writes every theme file.

``check`` builds into memory and compares with an existing ``themes`` folder; it
exits with status 1 and lists the files that differ or do not belong there, so
a hand edit of a generated file or a token change without a rebuild fails CI.
"""

import argparse
import sys
from pathlib import Path

from . import css, documenter, jupyterbook, latex, mpl

__all__ = ["OUTPUTS", "build", "check", "main"]

OUTPUTS = {
    "css/fwl-tokens.css": css.tokens_css,
    "css/fwl-tailwind-theme.css": css.tailwind_theme_css,
    "css/fwl-fonts.css": css.web_fonts_css,
    "mpl/fwl-paper.mplstyle": lambda: mpl.mplstyle("paper"),
    "mpl/fwl-dark.mplstyle": lambda: mpl.mplstyle("dark"),
    "documenter/fwl.css": documenter.documenter_css,
    "jupyterbook/fwl-jupyterbook.css": jupyterbook.jupyterbook_css,
    "latex/fwl.sty": latex.sty,
}


def build(folder):
    """Write every output file under ``folder``.

    Parameters
    ----------
    folder : str or pathlib.Path
        Output folder; sub-folders are created as needed.

    Returns
    -------
    list of pathlib.Path
        The written files, in the order of :data:`OUTPUTS`.
    """
    folder = Path(folder)
    written = []
    for rel, make in OUTPUTS.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(make(), encoding="utf-8")
        written.append(path)
    return written


def check(folder):
    """Return the outputs under ``folder`` that are missing or differ from a fresh build.

    Parameters
    ----------
    folder : str or pathlib.Path
        Folder that holds a previous build.

    Returns
    -------
    list of str
        Relative paths that are missing, differ, or are not an output (a file
        left behind by a renamed output); empty when ``folder`` is current.
    """
    folder = Path(folder)
    stale = []
    for rel, make in OUTPUTS.items():
        path = folder / rel
        if not path.is_file() or path.read_text(encoding="utf-8", errors="replace") != make():
            stale.append(rel)
    if folder.is_dir():
        # dotfiles (.DS_Store) and caches are not outputs, judged on the path inside folder
        rels = [p.relative_to(folder) for p in folder.rglob("*") if p.is_file()]
        extra = {r.as_posix() for r in rels if not any(x.startswith((".", "__")) for x in r.parts)}
        stale += sorted(extra - set(OUTPUTS))
    return stale


def main(argv=None):
    """Entry point for ``python -m fwl_visual_language`` and ``fwl-visual-language``."""
    parser = argparse.ArgumentParser(prog="fwl-visual-language", description=__doc__)
    parser.add_argument("command", choices=("build", "check"))
    parser.add_argument(
        "folder", nargs="?", default="themes", help="output folder (default: themes)"
    )
    args = parser.parse_args(argv)
    if args.command == "build":
        for path in build(args.folder):
            print(path)
        return 0
    stale = check(args.folder)
    for rel in stale:
        print(f"stale: {rel}", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
