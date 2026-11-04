"""Logique de l'ensemble de Mandelbrot, sans interface graphique.

L'ensemble de Mandelbrot est l'ensemble des points c du plan complexe pour lesquels
la suite z₀ = 0, zₙ₊₁ = zₙ² + c reste bornée. Le moteur C++ (main.exe --mandelbrot)
renvoie pour chaque pixel le nombre d'itérations « lissé » avant divergence (-1 pour
les points de l'ensemble) ; ici on le transforme en couleurs.
"""
import os

import numpy as np

import newton_calcul as nc

FICHIER_BINAIRE = os.path.join(nc.DOSSIER, "results_mandelbrot.bin")
FICHIER_PARAMETRES = os.path.join(nc.DOSSIER, "parametres_mandelbrot.json")

DEFAUTS = {"largeur": 1000, "hauteur": 800, "min_x": -2.5, "max_x": 1.0,
           "min_y": -1.4, "max_y": 1.4, "iterations": 500,
           "palette": "Océan", "densite": 1.0, "decalage": 0.0, "iterations_auto": True}

CHAMPS = nc.CHAMPS_FENETRE + [("iterations", "Itérations max", int)]

# Lieux célèbres : (nom, centre x, centre y, largeur de la vue)
LIEUX = [("Vue d'ensemble", -0.75, 0.0, 3.5),
         ("Vallée des hippocampes", -0.7436447860, 0.1318252536, 0.0003),
         ("Vallée des éléphants", 0.2850, 0.0110, 0.012),
         ("Spirale double", -0.7453, 0.1127, 0.0065),
         ("Mini-Mandelbrot", -1.7549, 0.0, 0.035),
         ("Point de Misiurewicz", -0.10109636, 0.95628651, 0.004),
         ("Zoom profond (1e-10)", -0.743643887037151, 0.131825904205330, 2e-10)]

COULEUR_INTERIEUR = (5, 6, 10)

# Palettes cycliques : couleurs de contrôle (#rrggbb), interpolées en 1024 teintes
_PALETTES = {
    "Océan": ["#000764", "#206bcb", "#edffff", "#ffaa00", "#000200"],
    "Feu": ["#000000", "#7f0000", "#ff4500", "#ffd700", "#ffffe0", "#ff8c00", "#3a0000"],
    "Néon": ["#0e1117", "#4cc9f0", "#9d7dff", "#f72585", "#ffd166", "#0e1117"],
    "Glace": ["#02010a", "#1b3a6b", "#6fb7e8", "#ffffff", "#a0c4ff", "#10183a"],
    "Forêt": ["#020a04", "#145a32", "#7dcea0", "#f9e79f", "#784212", "#0b0f05"],
    "Gris": ["#000000", "#ffffff", "#000000"],
}
NOMS_PALETTES = list(_PALETTES)


def _degrade(couleurs, n=1024):
    points = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in couleurs], dtype=float)
    if not np.allclose(points[0], points[-1]):
        points = np.vstack([points, points[:1]])       # boucle : la dernière couleur rejoint la première
    t = np.linspace(0, len(points) - 1, n, endpoint=False)
    k = np.floor(t).astype(int)
    f = (t - k)[:, None]
    return np.round(points[k] * (1 - f) + points[np.minimum(k + 1, len(points) - 1)] * f).astype(np.uint8)


TABLES = {nom: _degrade(c) for nom, c in _PALETTES.items()}


def colorer(mu, palette="Océan", densite=1.0, decalage=0.0):
    """Itérations lissées (une ligne par y) → image RGB uint8 de même forme.

    La teinte suit le logarithme du nombre d'itérations : le nombre de bandes de
    couleur reste à peu près le même quel que soit le niveau de zoom."""
    table = TABLES.get(palette, TABLES["Océan"])
    dedans = mu < 0
    t = np.log1p(np.maximum(mu, 0)) * densite + decalage
    idx = (np.mod(t, 1.0) * len(table)).astype(np.int64) % len(table)
    rgb = table[idx]
    rgb[dedans] = COULEUR_INTERIEUR
    return rgb


def apercu_palette(palette, largeur=256, hauteur=1):
    """Bande RGB montrant la palette (pour l'interface)."""
    return np.repeat(TABLES[palette][np.linspace(0, 1023, largeur).astype(int)][None], hauteur, axis=0)


def lire_binaire(chemin):
    """Lit le résultat de main.exe --mandelbrot ; renvoie un tableau float32, une ligne par y.
    Format : dim_x et dim_y en int32 little-endian, puis un float32 par pixel, ligne par ligne selon x."""
    with open(chemin, "rb") as f:
        dim_x, dim_y = np.frombuffer(f.read(8), dtype="<i4")
        valeurs = np.frombuffer(f.read(), dtype="<f4")
    if valeurs.size != dim_x * dim_y:
        raise ValueError(f"fichier incomplet ({valeurs.size} pixels au lieu de {dim_x * dim_y})")
    return valeurs.reshape(dim_x, dim_y).T


def arguments_calcul(p, fichier_binaire):
    return ["--mandelbrot", "--taille", str(p["largeur"]), str(p["hauteur"]),
            "--bornes", repr(p["min_x"]), repr(p["max_x"]), repr(p["min_y"]), repr(p["max_y"]),
            "--iterations", str(p["iterations"]), "--binaire", fichier_binaire]


def verifier_parametres(p):
    nc.verifier_fenetre(p)
    if not 1 <= p["iterations"] <= 1_000_000:
        raise ValueError("Itérations : entre 1 et 1 000 000")


def iterations_pour_zoom(largeur_vue):
    """Plus on zoome, plus il faut d'itérations pour voir les détails du bord."""
    profondeur = max(0.0, np.log10(3.5 / max(largeur_vue, 1e-300)))
    return int(min(100_000, round(250 + 220 * profondeur ** 1.25)))


def calcul_apercu(largeur=320, hauteur=200, iterations=200):
    """Petit calcul numpy, sans le moteur C++ (aperçu de la page d'accueil)."""
    x = np.linspace(-2.4, 0.9, largeur)
    y = np.linspace(-1.03, 1.03, hauteur)
    c = x[None, :] + 1j * y[:, None]
    z = np.zeros_like(c)
    mu = np.full(c.shape, -1.0)
    actifs = np.ones(c.shape, dtype=bool)
    with np.errstate(all="ignore"):
        for n in range(iterations):
            z[actifs] = z[actifs] ** 2 + c[actifs]
            sortis = actifs & (np.abs(z) > 256)
            mu[sortis] = np.maximum(0, n + 2 - np.log2(np.log(np.abs(z[sortis]))))
            actifs &= ~sortis
    return np.maximum(mu, -1)
