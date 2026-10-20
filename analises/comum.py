"""Conexão e estilo dos gráficos, compartilhados pelos notebooks.

Os notebooks só leem o que o pipeline já gravou no Postgres: nenhuma regra
de limpeza mora aqui, para o número do notebook ser o mesmo do painel.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

# Paleta categórica validada para daltonismo (fundo claro).
AZUL, LARANJA, VERDE, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#8a8a92"

motor = create_engine(
    "postgresql+psycopg://{u}:{s}@{h}:{p}/{d}".format(
        u=os.getenv("PGUSER", "ferrovias"),
        s=os.getenv("PGPASSWORD", "ferrovias"),
        h=os.getenv("PGHOST", "localhost"),
        p=os.getenv("PGPORT", "5436"),
        d=os.getenv("PGDATABASE", "ferrovias"),
    )
)


def sql(consulta):
    return pd.read_sql(consulta, motor)


plt.rcParams.update({
    "figure.figsize": (10, 3.6),
    "figure.dpi": 110,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": "#e6e5e1",
    "grid.linewidth": 0.8,
    "axes.edgecolor": "#c9c8c3",
    "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e",
    "ytick.color": "#52514e",
    "ytick.left": False,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "legend.frameon": False,
})


def milhoes(eixo):
    eixo.yaxis.set_major_formatter(lambda v, _: f"{v / 1e6:,.0f}".replace(",", "."))
