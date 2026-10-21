"""Plot Figure 1 of the thesis from data/cooling.csv into figures/cooling.pdf.

Run from the thesis folder: ``python scripts/plot_cooling.py``. Needs matplotlib,
numpy and the lab figure style fwl-mpl
(``pip install "fwl-mpl @ git+https://github.com/FormingWorlds/fwl-mpl"``).
"""

from pathlib import Path

import fwl_mpl
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parents[1]


def main():
    """Read the table and write the figure."""
    data = np.genfromtxt(HERE / "data" / "cooling.csv", delimiter=",", names=True, skip_header=1)
    fwl_mpl.use()
    fig, ax = plt.subplots(figsize=(5, 3))
    for case in data.dtype.names[1:]:
        ax.plot(data["time_myr"], data[case], label=case.replace("_", " "))
    ax.set_xlabel("Time (Myr)")
    ax.set_ylabel("Surface temperature (K)")
    ax.legend(frameon=False)
    fig.savefig(HERE / "figures" / "cooling.pdf", metadata={"CreationDate": None})


if __name__ == "__main__":
    main()
