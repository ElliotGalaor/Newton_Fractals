"""Interface de la fractale de Newton.

Un panneau à droite permet de choisir les paramètres (polynôme, pixels, zone du
plan complexe, précision, itérations) puis de lancer le calcul C++ ; l'image se
met à jour dans la même fenêtre.

Le polynôme s'écrit comme une expression : z^3 - 2z + 2, z^5 - 1, (z-1)(z+2i),
3z^4 + (1-i)z, ... Ses racines sont calculées ici (numpy) puis transmises au C++.
Le sélecteur « Racines » permet aussi de donner directement les racines
(1 ; -1 ; 0.5+2i) : le polynôme est alors le produit des (z - racine).

Utilisation :
    python NewtonFractalsDrawing.py
    python NewtonFractalsDrawing.py --bornes -0.3 0.3 -0.3 0.3       (affiche results.txt)
    python NewtonFractalsDrawing.py --enregistrer fractale.png        (image seule, sans fenêtre)
    python NewtonFractalsDrawing.py --exe chemin\\vers\\programme.exe

Dans la fenêtre :
    molette        zoom centré sur la souris
    clic-glisser   déplacer la vue
    h              revenir à la vue de départ
(la fenêtre s'ouvre agrandie, sur tout l'écran)
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import textwrap
import time

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.widgets import Button, TextBox

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_RESULTATS = os.path.join(DOSSIER, "results.txt")
FICHIER_PARAMETRES = os.path.join(DOSSIER, "parametres.json")   # mémorise le dernier calcul

# mode : "polynome" (on saisit p(z)) ou "racines" (on saisit les racines, p(z) = ∏(z - r))
DEFAUTS = {"mode": "polynome", "polynome": "z^3 - 2z + 2", "racines_texte": "",
           "largeur": 1000, "hauteur": 1000, "min_x": -2.0, "max_x": 2.0,
           "min_y": -2.0, "max_y": 2.0, "eps": 1e-6, "iterations": 50}
EXEMPLES = {"polynome": ["z^3 - 2z + 2", "z^3 - 1", "z^4 - 1", "z^5 - 1", "z^6 + z^3 - 1",
                         "z^8 + 15z^4 - 16", "(z^2 + 1)(z^2 - 4)", "z^3 - (1 + 2i)z + 1"],
            "racines": ["1 ; -1 ; i ; -i", "0 ; 1 ; 2", "1 ; -0.5+0.866i ; -0.5-0.866i",
                        "1+i ; 1-i ; -2 ; 0.5i", "-1 ; 1 ; 1.5i ; -1.5i ; 0", "1 ; 1 ; -1",
                        "2 ; 2i ; -2 ; -2i ; 0.3+0.3i"]}
LIBELLES_MODE = {"polynome": "p(z) =   (ex. z^3 - 2z + 2,  (z-1)(z+i),  z^5 - 1)",
                 "racines": "Racines, séparées par « ; »   (ex. 1 ; -1 ; 0.5+2i)"}
DEGRE_MAX = 20

# --- Thème ------------------------------------------------------------------
FOND = "#0e1117"
PANNEAU = "#151922"
CHAMP = "#1f2430"
CHAMP_SURVOL = "#272d3b"
BORDURE = "#343b4d"
TEXTE = "#e8eaf0"
TEXTE_DOUX = "#8b93a7"
ACCENT = "#4cc9f0"
ACCENT_SURVOL = "#7fdcf6"
ERREUR = "#ff6b81"
SUCCES = "#06d6a0"
COULEURS_RACINES = ["#4cc9f0", "#f72585", "#ffd166", "#06d6a0", "#9d7dff", "#ff8c42",
                    "#ef476f", "#118ab2", "#caffbf", "#ffadad", "#a0c4ff", "#fdffb6"]
COULEUR_NON_CONVERGENCE = "#262a36"
AIDE = "molette : zoom   ·   clic-glisser : déplacer   ·   h : vue initiale"


# --- Données ----------------------------------------------------------------
def lire_resultats(chemin):
    """Renvoie le tableau des indices de racine, une ligne par valeur de y."""
    with open(chemin) as f:
        lignes = [l for l in f.read().splitlines() if l.strip()]
    tableau = np.array(" ".join(lignes).split(), dtype=np.int16).reshape(len(lignes), -1)
    return tableau.T  # results.txt contient une ligne par valeur de x


# --- Polynôme ---------------------------------------------------------------
_JETON = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)"   # nombre
                    r"|([zZxX])"                                                      # variable
                    r"|([iIjJ])"                                                      # unité imaginaire
                    r"|(\*\*|[-+*/^()]))")                                            # opérateur


def _evaluer(noeud):
    """Évalue l'expression en polynôme, sans eval : seuls nombres, z, + - * / et puissances entières."""
    P = np.polynomial.Polynomial
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body)
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float, complex)) \
            and not isinstance(noeud.value, bool):
        return P([noeud.value])
    if isinstance(noeud, ast.Name) and noeud.id == "z":
        return P([0, 1])
    if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
        v = _evaluer(noeud.operand)
        return -v if isinstance(noeud.op, ast.USub) else v
    if isinstance(noeud, ast.BinOp):
        g, d = _evaluer(noeud.left), _evaluer(noeud.right)
        if isinstance(noeud.op, ast.Add):
            return g + d
        if isinstance(noeud.op, ast.Sub):
            return g - d
        if isinstance(noeud.op, ast.Mult):
            return g * d
        constante = d.trim().degree() == 0
        if isinstance(noeud.op, ast.Div):
            if not constante or d.coef[0] == 0:
                raise ValueError("Polynôme : on ne peut diviser que par un nombre non nul")
            return g / d.coef[0]
        if isinstance(noeud.op, ast.Pow):
            e = d.coef[0]
            if not constante or np.imag(e) != 0 or np.real(e) != int(np.real(e)) or not 0 <= np.real(e) <= DEGRE_MAX:
                raise ValueError(f"Polynôme : exposant entier entre 0 et {DEGRE_MAX} attendu")
            return g ** int(np.real(e))
    raise ValueError("Polynôme : expression non reconnue")


def _vers_polynome(texte, contexte="Polynôme"):
    """Expression → objet Polynomial de numpy (lève ValueError avec un message clair)."""
    s = texte.strip()
    if not s:
        raise ValueError(f"{contexte} : rien n'est écrit")
    jetons, pos = [], 0
    while pos < len(s):
        m = _JETON.match(s, pos)
        if not m:
            reste = s[pos:].strip()
            if not reste:
                break
            raise ValueError(f"{contexte} : caractère inattendu « {reste[0]} »")
        pos = m.end()
        nombre, variable, imaginaire, operateur = m.groups()
        if nombre:
            jetons.append(("valeur", nombre))
        elif variable:
            jetons.append(("valeur", "z"))
        elif imaginaire:
            jetons.append(("valeur", "1j"))
        else:
            jetons.append(("op", "**" if operateur == "^" else operateur))
    # Multiplication implicite : entre une valeur ou « ) » et une valeur ou « ( »
    morceaux = []
    for k, (genre, v) in enumerate(jetons):
        if k and (genre == "valeur" or v == "(") and (jetons[k - 1][0] == "valeur" or jetons[k - 1][1] == ")"):
            morceaux.append("*")
        morceaux.append(v)
    try:
        arbre = ast.parse(" ".join(morceaux), mode="eval")
    except SyntaxError:
        raise ValueError(f"{contexte} : expression mal écrite")
    try:
        return _evaluer(arbre).trim()
    except ValueError as e:
        raise ValueError(str(e).replace("Polynôme", contexte, 1))


def grouper_racines(valeurs):
    """Regroupe les valeurs presque égales (racine multiple) → [(valeur, multiplicité)], triées.
    np.roots éparpille une racine multiple (≈1e-5 pour une racine triple), d'où la tolérance."""
    groupes = []
    for r in valeurs:
        r = complex(r)
        for g in groupes:
            if abs(g[0] - r) <= 2e-4 * max(1, abs(r)):
                g.append(r)
                break
        else:
            groupes.append([r])
    resultat = []
    for g in groupes:
        v = complex(np.mean(g))
        if abs(v.imag) <= 1e-12 * max(1, abs(v)):
            v = complex(v.real, 0)
        if abs(v.real) <= 1e-12 * max(1, abs(v)):
            v = complex(0, v.imag)
        resultat.append((v, len(g)))
    resultat.sort(key=lambda vm: (round(vm[0].real, 9), round(vm[0].imag, 9)))
    return resultat


def nettoyer(coefs, tolerance=1e-13):
    """Met à zéro les parties réelles / imaginaires négligeables (bruit de calcul)."""
    c = np.array(coefs, dtype=complex)
    m = max(np.abs(c).max(), 1e-300)
    re_, im_ = c.real.copy(), c.imag.copy()
    re_[np.abs(re_) < tolerance * m] = 0
    im_[np.abs(im_) < tolerance * m] = 0
    return re_ + 1j * im_


def lire_polynome(texte):
    """« z^3 - 2z + 2 » → (coefficients du plus haut degré au terme constant, racines distinctes triées).

    Accepte : nombres (2, 0.5, 1e-3), z (ou x), i (unité imaginaire), + - * / ^ (ou **),
    parenthèses, et la multiplication implicite (2z, 3i, z(z+1), (z-1)(z+1))."""
    poly = _vers_polynome(texte)
    degre = poly.degree()
    if degre < 1:
        raise ValueError("Le polynôme doit être de degré 1 au moins (il faut un z)")
    if degre > DEGRE_MAX:
        raise ValueError(f"Degré {degre} trop grand ({DEGRE_MAX} au maximum)")
    coefs = np.asarray(poly.coef, dtype=complex)[::-1]
    return coefs, [v for v, _ in grouper_racines(np.roots(coefs))]


def lire_racines(texte):
    """« 1 ; -1 ; 0.5+2i » (ou « 1, -1, 2i ») → liste des racines, répétitions comprises.

    Séparateur « ; » (la virgule peut alors servir de virgule décimale) ou « , ».
    Chaque racine peut être une petite expression : 1+i, 1/3, (1+i)/2."""
    s = texte.strip()
    if not s:
        raise ValueError("Racines : rien n'est écrit")
    morceaux = [m.replace(",", ".") for m in s.split(";")] if ";" in s else s.split(",")
    racines = []
    for k, m in enumerate(morceaux, 1):
        if not m.strip():
            raise ValueError(f"Racine {k} : vide (séparateur en trop ?)")
        valeur = _vers_polynome(m, f"Racine {k}")
        if valeur.degree() > 0:
            raise ValueError(f"Racine {k} : z n'a pas sa place ici, il faut un nombre")
        racines.append(complex(valeur.coef[0]))
    if len(racines) > DEGRE_MAX:
        raise ValueError(f"{len(racines)} racines : {DEGRE_MAX} au maximum")
    return racines


def depuis_racines(racines):
    """Racines (répétitions comprises) → (coefficients de ∏(z - r), racines distinctes triées)."""
    return nettoyer(np.poly(racines)), [v for v, _ in grouper_racines(racines)]


def texte_racines(coefs):
    """Racines d'un polynôme, écrites pour le champ « Racines » (multiplicités répétées)."""
    morceaux = []
    for v, m in grouper_racines(np.roots(coefs)):
        morceaux += [texte_complexe(v, 10)] * m
    return " ; ".join(morceaux)


def texte_polynome(coefs, chiffres=9):
    """Coefficients (du plus haut degré au terme constant) → « z^3 - 2z + 2 ».
    Ce qui est négligeable devant le plus grand coefficient (< 1e-9) est mis à zéro et
    l'affichage garde 9 chiffres : on efface ainsi le bruit d'arrondi (ex. 2e-10 z^2,
    0.9999999998 z^3 après un passage par les racines)."""
    coefs = nettoyer(coefs, tolerance=1e-9)
    degre = len(coefs) - 1
    termes = []
    for k, c in enumerate(coefs):
        puissance = degre - k
        if c == 0:
            continue
        monome = "" if puissance == 0 else ("z" if puissance == 1 else f"z^{puissance}")
        if c.imag != 0 and c.real != 0:          # coefficient vraiment complexe : entre parenthèses
            signe, corps = "+", f"({texte_complexe(c, chiffres)})" + monome
        else:
            v = c.real if c.imag == 0 else c.imag
            signe = "-" if v < 0 else "+"
            nombre = f"{abs(v):.{chiffres}g}"
            suffixe_i = "" if c.imag == 0 else "i"
            if nombre == "1" and monome and not suffixe_i:
                nombre = ""
            corps = f"{nombre}{suffixe_i}{monome}"
        termes.append((signe, corps))
    if not termes:
        return "0"
    texte = ("-" if termes[0][0] == "-" else "") + termes[0][1]
    for signe, corps in termes[1:]:
        texte += f" {signe} {corps}"
    return texte


def texte_complexe(z, chiffres=3):
    """0.885-0.59i, -1.77, 2i"""
    re_, im_ = z.real, z.imag
    if im_ == 0:
        return f"{re_:.{chiffres}g}"
    im_txt = "" if abs(abs(im_) - 1) < 1e-12 else f"{abs(im_):.{chiffres}g}"
    if abs(re_) < 1e-12 * max(1, abs(z)):
        return f"{'-' if im_ < 0 else ''}{im_txt}i"
    return f"{re_:.{chiffres}g}{'-' if im_ < 0 else '+'}{im_txt}i"


def charger_parametres():
    try:
        with open(FICHIER_PARAMETRES) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sauvegarder_parametres(p):
    try:
        memo = dict(p, fichier_date=os.path.getmtime(FICHIER_RESULTATS))
        with open(FICHIER_PARAMETRES, "w") as f:
            json.dump(memo, f, indent=2)
    except OSError:
        pass


def trouver_executable(chemin=None):
    """Cherche le programme C++ compilé (makefile ou Visual Studio) ; prend le plus récent."""
    if chemin:
        return os.path.abspath(chemin) if os.path.isfile(chemin) else None
    candidats = ["main.exe", "main",
                 os.path.join("..", "x64", "Release", "ConsoleApplication2.exe"),
                 os.path.join("x64", "Release", "ConsoleApplication2.exe"),
                 os.path.join("..", "Release", "ConsoleApplication2.exe"),
                 os.path.join("..", "x64", "Debug", "ConsoleApplication2.exe"),
                 os.path.join("..", "Debug", "ConsoleApplication2.exe")]
    trouves = [os.path.join(DOSSIER, c) for c in candidats if os.path.isfile(os.path.join(DOSSIER, c))]
    return max(trouves, key=os.path.getmtime) if trouves else None


def environnement_calcul():
    """Ajoute au PATH le dossier des DLL de MinGW (OpenMP), si on le trouve."""
    env = dict(os.environ)
    dossiers = [os.path.dirname(shutil.which("g++") or ""), r"C:\msys64\ucrt64\bin"]
    for d in dossiers:
        if d and os.path.isdir(d):
            env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env


# --- Dessin -----------------------------------------------------------------
def hex_vers_rgb(couleur):
    return [int(couleur[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def colorer(indices):
    """Transforme les indices (-1, 1, 2, ...) en image RGB."""
    nb_racines = max(int(indices.max()), 1)
    palette = [hex_vers_rgb(COULEUR_NON_CONVERGENCE)]
    palette += [hex_vers_rgb(COULEURS_RACINES[k % len(COULEURS_RACINES)]) for k in range(nb_racines)]
    return np.array(palette)[np.clip(indices, 0, None)]


def styliser_axes(ax):
    for cote in ax.spines.values():
        cote.set_visible(False)
    ax.tick_params(colors=TEXTE_DOUX, labelsize=9, length=3)
    ax.set_xlabel("Re(z)", color=TEXTE_DOUX, fontsize=10)
    ax.set_ylabel("Im(z)", color=TEXTE_DOUX, fontsize=10)


def creer_legende(fig, indices, x_centre, y, racines=None):
    """Couleur de chaque bassin d'attraction (valeur de la racine) et part de l'image qu'il occupe."""
    total = indices.size
    nb = len(racines) if racines else max(int(indices.max()), 1)
    elements = []
    for k in range(1, nb + 1):
        part = 100 * np.count_nonzero(indices == k) / total
        nom = texte_complexe(racines[k - 1]) if racines else f"Racine {k}"
        elements.append(Patch(color=COULEURS_RACINES[(k - 1) % len(COULEURS_RACINES)],
                              label=f"{nom}  ({part:.1f} %)"))
    non_conv = np.count_nonzero(indices < 1)
    if non_conv:
        elements.append(Patch(color=COULEUR_NON_CONVERGENCE,
                              label=f"Pas de convergence  ({100 * non_conv / total:.1f} %)"))
    beaucoup = len(elements) > 8
    return fig.legend(handles=elements, loc="center", bbox_to_anchor=(x_centre, y),
                      ncol=min(len(elements), 6 if beaucoup else 4), frameon=False, labelcolor=TEXTE,
                      fontsize=8 if beaucoup else 9.5, handlelength=1.2, handleheight=1.2,
                      columnspacing=1.4 if beaucoup else 1.8)


# --- Nombres en écriture scientifique -------------------------------------------
# Un double a ~16 chiffres significatifs : en dessous de cet écart relatif entre
# min et max, les pixels ne sont plus distinguables et le calcul n'a plus de sens.
ECART_RELATIF_MIN = 1e-12


def nombre_sci(v, chiffres=17):
    """Écriture scientifique compacte : 1.25e-10, -2e0, 3.0517578125e-5."""
    if v == 0:
        return "0"
    mantisse, exposant = f"{v:.{chiffres - 1}e}".split("e")
    if "." in mantisse:
        mantisse = mantisse.rstrip("0").rstrip(".")
    return f"{mantisse}e{int(exposant)}"


def intervalle_sci(a, b, precision=1e-6):
    """Écrit a et b avec le moins de chiffres possible, mais assez pour que
    a < b reste vrai et que l'écart b - a soit juste (à 1e-6 près en relatif).
    Au pire on utilise 17 chiffres, ce qui conserve le double exactement."""
    for n in range(4, 18):
        ta, tb = nombre_sci(a, n), nombre_sci(b, n)
        ra, rb = float(ta), float(tb)
        if rb > ra and abs((rb - ra) - (b - a)) <= precision * (b - a):
            return ta, tb
    return nombre_sci(a, 17), nombre_sci(b, 17)


def ecart_trop_petit(a, b):
    return (b - a) <= ECART_RELATIF_MIN * max(abs(a), abs(b), 1e-300)


def coordonnee(v, ecart):
    """Valeur avec juste assez de chiffres pour être lisible à l'échelle « ecart »."""
    if v == 0 or ecart <= 0:
        return nombre_sci(v, 6)
    chiffres = int(np.ceil(np.log10(abs(v) / ecart))) + 2 if abs(v) > ecart else 4
    return nombre_sci(v, min(max(chiffres, 4), 17))


def sous_titre(p):
    taille = f"{p['largeur']} × {p['hauteur']} px"
    re_min, re_max = intervalle_sci(p["min_x"], p["max_x"], 1e-3)
    im_min, im_max = intervalle_sci(p["min_y"], p["max_y"], 1e-3)
    texte = f"{taille}   ·   Re ∈ [{re_min}, {re_max}]   ·   Im ∈ [{im_min}, {im_max}]"
    if len(texte) <= 80:
        return texte
    # Zoom profond : centre et largeur de la vue, plus lisibles que deux bornes presque égales
    lx, ly = p["max_x"] - p["min_x"], p["max_y"] - p["min_y"]
    cx, cy = (p["min_x"] + p["max_x"]) / 2, (p["min_y"] + p["max_y"]) / 2
    centre = f"{coordonnee(cx, lx / 1000)} {'+' if cy >= 0 else '-'} {coordonnee(abs(cy), ly / 1000)}i"
    return f"{taille}   ·   centre {centre}   ·   largeur {nombre_sci(lx, 3)} × {nombre_sci(ly, 3)}"


def polynome_de(p):
    """(coefficients, racines distinctes) du polynôme des paramètres, selon le mode de saisie."""
    if p.get("mode") == "racines":
        return depuis_racines(lire_racines(p.get("racines_texte", "")))
    return lire_polynome(p.get("polynome", DEFAUTS["polynome"]))


def racines_de(p):
    """Racines du polynôme des paramètres, ou None s'il est illisible."""
    try:
        return polynome_de(p)[1]
    except ValueError:
        return None


def titre_polynome(p, longueur_max=95):
    """« p(z) = z^3 - 2z + 2 », ou en mode racines la forme factorisée « p(z) = (z - 1)(z + i) »."""
    if p.get("mode") == "racines":
        try:
            facteurs = []
            for v, m in grouper_racines(lire_racines(p.get("racines_texte", ""))):
                if v == 0:
                    f = "z"
                elif v.imag == 0:
                    f = f"(z {'-' if v.real > 0 else '+'} {abs(v.real):.4g})"
                elif v.real == 0:
                    f = f"(z {'-' if v.imag > 0 else '+'} {texte_complexe(complex(0, abs(v.imag)), 4)})"
                else:
                    f = f"(z - ({texte_complexe(v, 4)}))"
                facteurs.append(f + (f"^{m}" if m > 1 else ""))
            texte = "p(z) = " + "".join(facteurs)
        except ValueError:
            texte = "racines : " + p.get("racines_texte", "")
    else:
        texte = "p(z) = " + p.get("polynome", DEFAUTS["polynome"])
    return texte if len(texte) <= longueur_max else texte[:longueur_max - 1] + "…"


def exporter_image(indices, p, chemin):
    """Enregistre la fractale seule (sans le panneau) dans un fichier image."""
    fig = Figure(figsize=(9, 10), facecolor=FOND)
    ax = fig.add_axes([0.11, 0.14, 0.83, 0.70], facecolor=FOND)
    ax.imshow(colorer(indices), extent=[p["min_x"], p["max_x"], p["min_y"], p["max_y"]],
              origin="lower", interpolation="antialiased")
    styliser_axes(ax)
    fig.text(0.11, 0.945, "Fractale de Newton", color=TEXTE, fontsize=20, fontweight="bold")
    fig.text(0.11, 0.912, titre_polynome(p, 80), color=TEXTE, fontsize=11)
    fig.text(0.11, 0.887, sous_titre(p), color=TEXTE_DOUX, fontsize=9.5)
    creer_legende(fig, indices, 0.525, 0.05, racines_de(p))
    fig.savefig(chemin, dpi=150, facecolor=FOND)


# --- Navigation (zoom, déplacement) -------------------------------------------
class Navigation:
    """Zoom à la molette et déplacement au clic-glisser."""

    def __init__(self, ax, quand_limite=None):
        self.ax = ax
        self.quand_limite = quand_limite   # appelé quand on ne peut plus zoomer
        self.canvas = ax.figure.canvas
        self.vue_initiale_memorisee = False
        self.depart = None
        self.canvas.mpl_connect("scroll_event", self.molette)
        self.canvas.mpl_connect("button_press_event", self.appui)
        self.canvas.mpl_connect("motion_notify_event", self.mouvement)
        self.canvas.mpl_connect("button_release_event", self.relache)

    def barre(self):
        return getattr(self.canvas, "toolbar", None)

    def reinitialiser(self):
        """Après un nouveau calcul : la vue de départ devient celle de la nouvelle image."""
        tb = self.barre()
        if tb is not None and hasattr(tb, "update"):
            tb.update()
        self.vue_initiale_memorisee = False

    def memoriser_vue(self):
        # Alimente l'historique de la barre d'outils, pour que « h » et les flèches marchent
        tb = self.barre()
        if tb is not None and hasattr(tb, "push_current"):
            tb.push_current()

    def avant_changement(self):
        if not self.vue_initiale_memorisee:
            self.memoriser_vue()
            self.vue_initiale_memorisee = True

    def molette(self, e):
        if e.inaxes is not self.ax or e.xdata is None or not self.ax.axison:
            return
        f = 1 / 1.25 if e.button == "up" else 1.25
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        nx0, nx1 = e.xdata - (e.xdata - x0) * f, e.xdata + (x1 - e.xdata) * f
        ny0, ny1 = e.ydata - (e.ydata - y0) * f, e.ydata + (y1 - e.ydata) * f
        if f < 1 and (ecart_trop_petit(nx0, nx1) or ecart_trop_petit(ny0, ny1)):
            if self.quand_limite:
                self.quand_limite()
            return
        self.avant_changement()
        self.ax.set_xlim(nx0, nx1)
        self.ax.set_ylim(ny0, ny1)
        self.memoriser_vue()
        self.canvas.draw_idle()

    def appui(self, e):
        tb = self.barre()
        if e.button != 1 or e.inaxes is not self.ax or not self.ax.axison \
                or (tb is not None and getattr(tb, "mode", "")):
            return  # on laisse la main aux outils loupe / déplacement de la barre s'ils sont actifs
        self.avant_changement()
        self.depart = (e.x, e.y, self.ax.get_xlim(), self.ax.get_ylim())

    def mouvement(self, e):
        if self.depart is None:
            return
        x, y, (x0, x1), (y0, y1) = self.depart
        dx = (e.x - x) * (x1 - x0) / self.ax.bbox.width
        dy = (e.y - y) * (y1 - y0) / self.ax.bbox.height
        self.ax.set_xlim(x0 - dx, x1 - dx)
        self.ax.set_ylim(y0 - dy, y1 - dy)
        self.canvas.draw_idle()

    def relache(self, e):
        if self.depart is not None:
            self.depart = None
            self.memoriser_vue()


# --- Application --------------------------------------------------------------
CHAMPS = [  # (clé, libellé, type)
    ("largeur", "Largeur (px)", int), ("hauteur", "Hauteur (px)", int),
    ("min_x", "Re min", float), ("max_x", "Re max", float),
    ("min_y", "Im min", float), ("max_y", "Im max", float),
    ("eps", "Précision (eps)", float), ("iterations", "Itérations max", int),
]


class Application:
    def __init__(self, parametres, indices, executable):
        self.p = dict(parametres)        # paramètres de l'image affichée
        self.indices = indices
        self.executable = executable
        self.commande = [executable] if executable else None
        self.image = None
        self.legende = None
        self.racines = racines_de(self.p)   # racines du polynôme de l'image affichée
        self.mode = self.p.get("mode", "polynome")   # ce que contient le champ : p(z) ou racines
        self.num_exemple = {"polynome": 0, "racines": -1}

        self.fig = plt.figure(figsize=(13.5, 8.6), facecolor=FOND)
        if self.fig.canvas.manager is not None:
            self.fig.canvas.manager.set_window_title("Fractale de Newton")

        # Zone de l'image
        self.ax = self.fig.add_axes([0.06, 0.13, 0.57, 0.71], facecolor=FOND)
        styliser_axes(self.ax)
        self.ax.format_coord = self.coordonnees
        self.fig.text(0.06, 0.945, "Fractale de Newton", color=TEXTE, fontsize=20, fontweight="bold")
        self.texte_polynome = self.fig.text(0.06, 0.912, "", color=TEXTE, fontsize=11)
        self.texte_sous_titre = self.fig.text(0.06, 0.886, "", color=TEXTE_DOUX, fontsize=9.5)
        self.texte_vide = self.ax.text(0.5, 0.5, "Choisis les paramètres à droite\npuis clique sur « Calculer »",
                                       transform=self.ax.transAxes, ha="center", va="center",
                                       color=TEXTE_DOUX, fontsize=13, linespacing=1.8)
        self.texte_aide = self.fig.text(0.82, 0.04, AIDE, color=TEXTE_DOUX, fontsize=8.5, ha="center",
                                        va="bottom", linespacing=1.6)

        self.construire_panneau()
        self.navigation = Navigation(self.ax, quand_limite=lambda: self.statut(
            "Zoom maximal atteint : au-delà, la précision des nombres (double) "
            "ne permet plus de distinguer les pixels.", ERREUR))

        if indices is not None:
            self.afficher_resultat(indices, self.p)
            self.statut("Résultat chargé depuis results.txt", TEXTE_DOUX)
        else:
            self.ax.set_axis_off()
            self.statut("Prêt." if self.commande else
                        "Programme C++ introuvable : compile-le (make) ou passe --exe.",
                        TEXTE_DOUX if self.commande else ERREUR)

    # -- Fenêtre --
    def agrandir_au_lancement(self):
        """Agrandit la fenêtre (maximisée, avec sa barre de titre) dès qu'elle est affichée."""
        # Un petit délai : la fenêtre doit exister à l'écran avant d'être agrandie
        self._minuteur = self.fig.canvas.new_timer(interval=100)
        self._minuteur.single_shot = True
        self._minuteur.add_callback(self.agrandir)
        self._minuteur.start()

    def agrandir(self):
        manager = self.fig.canvas.manager
        if manager is None:
            return
        fenetre = getattr(manager, "window", None)
        # La méthode dépend de la bibliothèque d'affichage utilisée par matplotlib
        methodes = (lambda: fenetre.state("zoomed"),            # Tk (Windows)
                    lambda: fenetre.attributes("-zoomed", True),  # Tk (Linux)
                    lambda: fenetre.showMaximized(),             # Qt
                    lambda: fenetre.maximize(),                  # GTK
                    lambda: manager.frame.Maximize(True))        # Wx
        for agrandir in methodes:
            try:
                agrandir()
                return
            except Exception:   # méthode absente pour cette bibliothèque : on essaie la suivante
                pass

    # -- Panneau de paramètres --
    def champ(self, cle, rect, texte, taille_police=8.5):
        ax = self.fig.add_axes(rect)
        boite = TextBox(ax, "", initial=texte, color=CHAMP, hovercolor=CHAMP_SURVOL, textalignment="left")
        boite.text_disp.set_color(TEXTE)
        boite.text_disp.set_fontsize(taille_police)
        if hasattr(boite, "cursor"):
            boite.cursor.set_color(TEXTE)
        for cote in ax.spines.values():
            cote.set_color(BORDURE)
        self.champs[cle] = boite

    def construire_panneau(self):
        x0, larg, col2 = 0.685, 0.275, 0.83
        self.fig.patches.append(FancyBboxPatch(
            (0.665, 0.035), 0.31, 0.915, boxstyle="round,pad=0,rounding_size=0.008",
            transform=self.fig.transFigure, facecolor=PANNEAU, edgecolor="#232838", zorder=-1))
        self.fig.text(x0, 0.905, "Paramètres", color=TEXTE, fontsize=14, fontweight="bold")

        def section(y_champ, titre):
            self.fig.text(x0, y_champ + 0.071, titre, color=ACCENT, fontsize=8.5, fontweight="bold")

        def libelle(x, y_champ, texte):
            self.fig.text(x, y_champ + 0.042, texte, color=TEXTE_DOUX, fontsize=9)

        self.champs = {}
        t = self.textes(self.p)

        # Polynôme : sélecteur p(z) / racines, champ large, bouton qui fait défiler des exemples
        y = 0.79
        section(y, "POLYNÔME")
        self.boutons_mode = {
            "polynome": self.bouton([x0 + 0.135, y + 0.064, 0.068, 0.03], "p(z)",
                                    lambda _: self.changer_mode("polynome"), taille=9),
            "racines": self.bouton([x0 + 0.207, y + 0.064, 0.068, 0.03], "Racines",
                                   lambda _: self.changer_mode("racines"), taille=9),
        }
        self.texte_libelle_poly = self.fig.text(x0, y + 0.042, LIBELLES_MODE[self.mode],
                                                color=TEXTE_DOUX, fontsize=9)
        self.champ("polynome", [x0, y, 0.195, 0.036], t["polynome"], taille_police=10)
        self.colorer_boutons_mode()
        self.bouton_exemple = self.bouton([x0 + 0.203, y, 0.072, 0.036], "Exemple ▸", self.exemple_suivant,
                                          taille=8.5)

        # Pixels, fenêtre, convergence : deux champs par ligne
        lignes = [(0.674, "IMAGE", ("largeur", "hauteur")),
                  (0.557, "FENÊTRE DU PLAN COMPLEXE", ("min_x", "max_x")),
                  (0.487, None, ("min_y", "max_y")),
                  (0.369, "CONVERGENCE", ("eps", "iterations"))]
        noms = {cle: nom for cle, nom, _ in CHAMPS}
        for y, titre, cles in lignes:
            if titre:
                section(y, titre)
            for x, cle in zip((x0, col2), cles):
                libelle(x, y, noms[cle])
                self.champ(cle, [x, y, 0.13, 0.036], t[cle])

        self.bouton_vue = self.bouton([x0, 0.29, larg, 0.045], "Recalculer la vue affichée",
                                      self.recalculer_vue)
        petit = (larg - 0.014) / 3
        self.bouton_carre = self.bouton([x0, 0.237, petit, 0.042], "Pixels carrés", self.pixels_carres,
                                        taille=9)
        self.bouton_defaut = self.bouton([x0 + petit + 0.007, 0.237, petit, 0.042], "Par défaut",
                                         self.valeurs_defaut, taille=9)
        self.bouton_export = self.bouton([x0 + 2 * (petit + 0.007), 0.237, petit, 0.042], "Export PNG",
                                         self.enregistrer, taille=9)
        self.bouton_calcul = self.bouton([x0, 0.15, larg, 0.06], "Calculer", self.calculer,
                                         couleur=ACCENT, survol=ACCENT_SURVOL, texte=FOND, taille=13)
        self.texte_statut = self.fig.text(x0, 0.128, "", color=TEXTE_DOUX, fontsize=9.5, va="top")

    def bouton(self, rect, libelle, action, couleur=CHAMP, survol=CHAMP_SURVOL, texte=TEXTE, taille=10):
        ax = self.fig.add_axes(rect)
        b = Button(ax, libelle, color=couleur, hovercolor=survol)
        b.label.set_color(texte)
        b.label.set_fontsize(taille)
        if couleur == ACCENT:
            b.label.set_fontweight("bold")
        for cote in ax.spines.values():
            cote.set_color(BORDURE if couleur == CHAMP else couleur)
        b.on_clicked(action)
        return b

    @staticmethod
    def textes(valeurs):
        """Texte de chaque champ. Les bornes sont écrites par paires (min, max) en
        écriture scientifique, avec assez de chiffres pour rester distinctes."""
        t = {}
        for cle, v in valeurs.items():
            if cle == "polynome":
                # Le champ contient p(z) ou la liste des racines, selon le mode
                t[cle] = str(valeurs.get("racines_texte", "") if valeurs.get("mode") == "racines" else v)
            elif cle in ("largeur", "hauteur", "iterations"):
                t[cle] = str(int(v))
            elif cle == "eps":
                t[cle] = nombre_sci(v, 6)
        for a, b in (("min_x", "max_x"), ("min_y", "max_y")):
            if a in valeurs and b in valeurs:
                t[a], t[b] = intervalle_sci(valeurs[a], valeurs[b])
            else:
                for c in (a, b):
                    if c in valeurs:
                        t[c] = nombre_sci(valeurs[c])
        return t

    def ecrire(self, cle, texte):
        """Change le texte d'un champ sans y laisser un curseur de saisie affiché."""
        boite = self.champs[cle]
        boite.set_val(texte)
        if hasattr(boite, "cursor") and not getattr(boite, "capturekeystrokes", False):
            boite.cursor.set_visible(False)

    def remplir(self, valeurs):
        for cle, texte in self.textes(valeurs).items():
            if cle in self.champs:
                self.ecrire(cle, texte)

    def lire_polynome_saisi(self):
        """Lit le champ polynôme selon le mode. Renvoie les deux écritures (p(z) et racines),
        les coefficients et les racines distinctes ; lève ValueError si illisible."""
        texte = " ".join(self.champs["polynome"].text.split())
        if self.mode == "racines":
            coefs, racines = depuis_racines(lire_racines(texte))
            return {"mode": "racines", "racines_texte": texte, "polynome": texte_polynome(coefs),
                    "coefs": coefs, "racines": racines}
        coefs, racines = lire_polynome(texte)
        return {"mode": "polynome", "polynome": texte, "racines_texte": texte_racines(coefs),
                "coefs": coefs, "racines": racines}

    def colorer_boutons_mode(self):
        for mode, b in self.boutons_mode.items():
            actif = mode == self.mode
            b.color = ACCENT if actif else CHAMP
            b.hovercolor = ACCENT_SURVOL if actif else CHAMP_SURVOL
            b.ax.set_facecolor(b.color)
            b.label.set_color(FOND if actif else TEXTE)
            b.label.set_fontweight("bold" if actif else "normal")

    def changer_mode(self, mode, texte=None):
        """Passe le champ en saisie de p(z) ou de racines, en convertissant ce qui est écrit."""
        if mode == self.mode and texte is None:
            return
        if texte is None:
            try:
                saisi = self.lire_polynome_saisi()
            except ValueError as e:
                if self.champs["polynome"].text.strip():
                    self.statut(f"{e}\n(corrige le champ avant de changer de mode)", ERREUR)
                    return
                saisi = {"polynome": "", "racines_texte": ""}
            texte = saisi["racines_texte"] if mode == "racines" else saisi["polynome"]
        self.mode = mode
        self.texte_libelle_poly.set_text(LIBELLES_MODE[mode])
        self.colorer_boutons_mode()
        self.ecrire("polynome", texte)
        self.statut("Saisie des racines : p(z) = produit des (z - racine)" if mode == "racines"
                    else "Saisie du polynôme p(z)", TEXTE_DOUX)

    def lire_champs(self):
        """Lit et vérifie les champs ; lève ValueError avec un message clair."""
        p = self.lire_polynome_saisi()
        for cle, libelle, type_ in CHAMPS:
            texte = self.champs[cle].text.strip().replace(",", ".")
            try:
                p[cle] = type_(float(texte)) if type_ is int else float(texte)
            except ValueError:
                raise ValueError(f"« {libelle} » : nombre invalide")
        if not (1 <= p["largeur"] <= 20000 and 1 <= p["hauteur"] <= 20000):
            raise ValueError("La taille doit être entre 1 et 20000 pixels")
        if p["largeur"] * p["hauteur"] > 50_000_000:
            raise ValueError("Image trop grande (50 millions de pixels max)")
        if p["min_x"] >= p["max_x"] or p["min_y"] >= p["max_y"]:
            raise ValueError("Il faut min < max pour Re et pour Im")
        if ecart_trop_petit(p["min_x"], p["max_x"]) or ecart_trop_petit(p["min_y"], p["max_y"]):
            raise ValueError("Zoom trop profond : la précision des nombres (double, ~16 chiffres) "
                             "ne permet plus de distinguer les pixels")
        if p["eps"] <= 0:
            raise ValueError("La précision doit être positive")
        if not 1 <= p["iterations"] <= 1_000_000:
            raise ValueError("Itérations : entre 1 et 1 000 000")
        return p

    def statut(self, texte, couleur=TEXTE_DOUX):
        # Retour à la ligne pour rester dans le panneau
        texte = "\n".join(textwrap.fill(l, 46) for l in texte.splitlines())
        self.texte_statut.set_text(texte)
        # Un long message prend la place de l'aide, qui revient au message suivant
        if hasattr(self, "texte_aide"):
            self.texte_aide.set_visible(texte.count("\n") < 2)
        self.texte_statut.set_color(couleur)
        self.fig.canvas.draw_idle()

    # -- Actions --
    def calculer(self, _=None):
        if not self.commande:
            self.statut("Programme C++ introuvable : compile-le (make)\nou passe --exe au script.", ERREUR)
            return
        try:
            p = self.lire_champs()
        except ValueError as e:
            self.statut(str(e), ERREUR)
            return

        self.statut("Calcul en cours…", ACCENT)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        args = ["--taille", str(p["largeur"]), str(p["hauteur"]),
                "--bornes", repr(p["min_x"]), repr(p["max_x"]), repr(p["min_y"]), repr(p["max_y"]),
                "--eps", repr(p["eps"]), "--iterations", str(p["iterations"])]
        for option, valeurs in (("--coefs", p["coefs"]), ("--racines", p["racines"])):
            args += [option, str(len(valeurs))]
            for v in valeurs:
                args += [repr(float(v.real)), repr(float(v.imag))]
        debut = time.perf_counter()
        try:
            r = subprocess.run(self.commande + args, cwd=DOSSIER, env=environnement_calcul(),
                               capture_output=True, text=True)
        except OSError as e:
            self.statut(f"Impossible de lancer le programme :\n{e}", ERREUR)
            return
        if r.returncode != 0:
            message = (r.stderr or r.stdout).strip().splitlines()
            self.statut("Erreur du programme C++ :\n" + (message[0] if message else f"code {r.returncode}"), ERREUR)
            return
        try:
            indices = lire_resultats(FICHIER_RESULTATS)
        except (OSError, ValueError) as e:
            self.statut(f"Lecture de results.txt impossible :\n{e}", ERREUR)
            return
        duree = time.perf_counter() - debut

        self.afficher_resultat(indices, p)
        sauvegarder_parametres({k: v for k, v in p.items() if k not in ("coefs", "racines")})
        self.statut(f"Terminé en {duree:.2f} s   ·   {len(p['racines'])} racine(s)", SUCCES)

    def exemple_suivant(self, _=None):
        """Met l'exemple suivant (polynôme ou racines, selon le mode) dans le champ, sans calculer."""
        liste = EXEMPLES[self.mode]
        n = (self.num_exemple[self.mode] + 1) % len(liste)
        if liste[n] == self.champs["polynome"].text.strip():
            n = (n + 1) % len(liste)
        self.num_exemple[self.mode] = n
        self.ecrire("polynome", liste[n])
        self.statut("Exemple choisi : clique sur Calculer", TEXTE_DOUX)

    def recalculer_vue(self, _=None):
        """Recalcule en pleine résolution la zone actuellement affichée (après un zoom)."""
        if self.indices is None:
            self.statut("Lance d'abord un calcul.", TEXTE_DOUX)
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        self.remplir({"min_x": x0, "max_x": x1, "min_y": y0, "max_y": y1})
        self.pixels_carres(silencieux=True)
        self.calculer()

    def pixels_carres(self, _=None, silencieux=False):
        """Ajuste la hauteur pour que les pixels soient carrés (pas de déformation)."""
        try:
            p = self.lire_champs()
        except ValueError as e:
            self.statut(str(e), ERREUR)
            return
        hauteur = max(1, round(p["largeur"] * (p["max_y"] - p["min_y"]) / (p["max_x"] - p["min_x"])))
        self.ecrire("hauteur", str(min(hauteur, 20000)))
        if not silencieux:
            self.statut(f"Hauteur ajustée à {hauteur} px", TEXTE_DOUX)

    def valeurs_defaut(self, _=None):
        self.remplir({k: v for k, v in DEFAUTS.items() if k not in ("mode", "polynome", "racines_texte")})
        self.changer_mode("polynome", texte=DEFAUTS["polynome"])
        self.statut("Valeurs par défaut remises (clique sur Calculer)", TEXTE_DOUX)

    def enregistrer(self, _=None):
        if self.indices is None:
            self.statut("Rien à enregistrer pour l'instant.", TEXTE_DOUX)
            return
        nom = time.strftime("fractale_%Y%m%d_%H%M%S.png")
        try:
            exporter_image(self.indices, self.p, os.path.join(DOSSIER, nom))
        except OSError as e:
            self.statut(f"Enregistrement impossible :\n{e}", ERREUR)
            return
        self.statut(f"Image enregistrée : {nom}", SUCCES)

    # -- Affichage --
    def afficher_resultat(self, indices, p):
        self.indices = indices
        self.p = {k: v for k, v in p.items() if k not in ("coefs", "racines")}
        self.p["hauteur"], self.p["largeur"] = indices.shape
        self.racines = p["racines"] if "racines" in p else racines_de(self.p)
        etendue = [p["min_x"], p["max_x"], p["min_y"], p["max_y"]]

        self.texte_vide.set_visible(False)
        self.ax.set_axis_on()
        if self.image is None:
            self.image = self.ax.imshow(colorer(indices), extent=etendue, origin="lower",
                                        interpolation="antialiased")
        else:
            self.image.set_data(colorer(indices))
            self.image.set_extent(etendue)
        self.ax.set_xlim(etendue[0], etendue[1])
        self.ax.set_ylim(etendue[2], etendue[3])

        if self.legende is not None:
            self.legende.remove()
        self.legende = creer_legende(self.fig, indices, 0.345, 0.04, self.racines)
        self.texte_polynome.set_text(titre_polynome(self.p))
        self.texte_sous_titre.set_text(sous_titre(self.p))
        self.navigation.reinitialiser()
        self.fig.canvas.draw_idle()

    def coordonnees(self, x, y):
        """Texte de la barre d'état : point sous la souris et racine vers laquelle il converge."""
        # Assez de chiffres pour distinguer deux pixels voisins, même après un zoom profond
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        ex = (x1 - x0) / max(self.ax.bbox.width, 1)
        ey = (y1 - y0) / max(self.ax.bbox.height, 1)
        texte = f"z = {coordonnee(x, ex)} {'+' if y >= 0 else '-'} {coordonnee(abs(y), ey)}i"
        if self.indices is None:
            return texte
        p = self.p
        hauteur, largeur = self.indices.shape
        i = int((x - p["min_x"]) / (p["max_x"] - p["min_x"]) * largeur)
        j = int((y - p["min_y"]) / (p["max_y"] - p["min_y"]) * hauteur)
        if 0 <= i < largeur and 0 <= j < hauteur:
            k = self.indices[j, i]
            if k < 1:
                texte += "   →   pas de convergence"
            elif self.racines and k <= len(self.racines):
                texte += f"   →   racine {k} = {texte_complexe(self.racines[k - 1], 6)}"
            else:
                texte += f"   →   racine {k}"
        return texte


# --- Lancement ----------------------------------------------------------------
def lire_arguments():
    p = argparse.ArgumentParser(description="Interface de la fractale de Newton")
    p.add_argument("--fichier", default=FICHIER_RESULTATS, help="fichier produit par le programme C++")
    p.add_argument("--bornes", nargs=4, type=float, metavar=("MIN_X", "MAX_X", "MIN_Y", "MAX_Y"),
                   help="zone du plan complexe de results.txt (sinon : celle du dernier calcul)")
    p.add_argument("--eps", type=float, help="précision utilisée pour results.txt")
    p.add_argument("--iterations", type=int, help="nombre d'itérations utilisé pour results.txt")
    p.add_argument("--polynome", help="polynôme utilisé pour results.txt, ex. \"z^3 - 2z + 2\"")
    p.add_argument("--exe", help="chemin du programme C++ compilé (sinon recherche automatique)")
    p.add_argument("--enregistrer", metavar="IMAGE.png",
                   help="enregistre l'image de results.txt dans ce fichier, sans ouvrir la fenêtre")
    return p.parse_args()


def preparer(args):
    """Choisit les paramètres de départ et charge results.txt si on sait à quoi il correspond."""
    p = dict(DEFAUTS)
    memo = charger_parametres()
    if memo:
        p.update({k: memo[k] for k in DEFAUTS if k in memo})

    indices = None
    existe = os.path.isfile(args.fichier)
    if args.bornes:
        # Lancé par le programme C++ : on connaît la zone de results.txt
        p["min_x"], p["max_x"], p["min_y"], p["max_y"] = args.bornes
        if args.eps is not None:
            p["eps"] = args.eps
        if args.iterations is not None:
            p["iterations"] = args.iterations
        if args.polynome:
            p["mode"], p["polynome"] = "polynome", args.polynome
        if existe:
            indices = lire_resultats(args.fichier)
    elif memo and existe and abs(os.path.getmtime(args.fichier) - memo.get("fichier_date", -1)) < 1e-3:
        # results.txt n'a pas changé depuis le dernier calcul lancé par l'interface
        indices = lire_resultats(args.fichier)
    if indices is not None:
        p["hauteur"], p["largeur"] = indices.shape
    return p, indices


def main():
    args = lire_arguments()
    p, indices = preparer(args)

    if args.enregistrer:
        if indices is None:
            indices = lire_resultats(args.fichier)
        exporter_image(indices, p, args.enregistrer)
        print(f"Image enregistree : {args.enregistrer}")
        return

    app = Application(p, indices, trouver_executable(args.exe))
    app.agrandir_au_lancement()
    plt.show()


if __name__ == "__main__":
    main()
