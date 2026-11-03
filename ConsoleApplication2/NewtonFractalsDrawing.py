"""Interface de la fractale de Newton.

Un panneau à droite permet de choisir les paramètres (pixels, zone du plan
complexe, précision, itérations) puis de lancer le calcul C++ ; l'image se met
à jour dans la même fenêtre.

Utilisation :
    python NewtonFractalsDrawing.py
    python NewtonFractalsDrawing.py --bornes -0.3 0.3 -0.3 0.3       (affiche results.txt)
    python NewtonFractalsDrawing.py --enregistrer fractale.png        (image seule, sans fenêtre)
    python NewtonFractalsDrawing.py --exe chemin\\vers\\programme.exe

Dans la fenêtre :
    molette        zoom centré sur la souris
    clic-glisser   déplacer la vue
    h              revenir à la vue de départ
"""
import argparse
import json
import os
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

DEFAUTS = {"largeur": 1000, "hauteur": 1000, "min_x": -2.0, "max_x": 2.0,
           "min_y": -2.0, "max_y": 2.0, "eps": 1e-6, "iterations": 50}

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
COULEURS_RACINES = ["#4cc9f0", "#f72585", "#ffd166", "#06d6a0",
                    "#9d7dff", "#ff8c42", "#ef476f", "#118ab2"]
COULEUR_NON_CONVERGENCE = "#262a36"
AIDE = "molette : zoom   ·   clic-glisser : déplacer   ·   h : vue initiale"


# --- Données ----------------------------------------------------------------
def lire_resultats(chemin):
    """Renvoie le tableau des indices de racine, une ligne par valeur de y."""
    with open(chemin) as f:
        lignes = [l for l in f.read().splitlines() if l.strip()]
    tableau = np.array(" ".join(lignes).split(), dtype=np.int16).reshape(len(lignes), -1)
    return tableau.T  # results.txt contient une ligne par valeur de x


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


def creer_legende(fig, indices, x_centre, y):
    """Couleur de chaque bassin d'attraction et part de l'image qu'il occupe."""
    total = indices.size
    elements = []
    for k in range(1, max(int(indices.max()), 1) + 1):
        part = 100 * np.count_nonzero(indices == k) / total
        elements.append(Patch(color=COULEURS_RACINES[(k - 1) % len(COULEURS_RACINES)],
                              label=f"Racine {k}  ({part:.1f} %)"))
    non_conv = np.count_nonzero(indices < 1)
    if non_conv:
        elements.append(Patch(color=COULEUR_NON_CONVERGENCE,
                              label=f"Pas de convergence  ({100 * non_conv / total:.1f} %)"))
    return fig.legend(handles=elements, loc="center", bbox_to_anchor=(x_centre, y),
                      ncol=min(len(elements), 4), frameon=False, labelcolor=TEXTE, fontsize=10,
                      handlelength=1.2, handleheight=1.2, columnspacing=1.8)


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


def exporter_image(indices, p, chemin):
    """Enregistre la fractale seule (sans le panneau) dans un fichier image."""
    fig = Figure(figsize=(9, 10), facecolor=FOND)
    ax = fig.add_axes([0.11, 0.15, 0.83, 0.72], facecolor=FOND)
    ax.imshow(colorer(indices), extent=[p["min_x"], p["max_x"], p["min_y"], p["max_y"]],
              origin="lower", interpolation="antialiased")
    styliser_axes(ax)
    fig.text(0.11, 0.945, "Fractale de Newton", color=TEXTE, fontsize=20, fontweight="bold")
    fig.text(0.11, 0.912, sous_titre(p), color=TEXTE_DOUX, fontsize=10)
    creer_legende(fig, indices, 0.525, 0.05)
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

        self.fig = plt.figure(figsize=(13.5, 8.6), facecolor=FOND)
        if self.fig.canvas.manager is not None:
            self.fig.canvas.manager.set_window_title("Fractale de Newton")

        # Zone de l'image
        self.ax = self.fig.add_axes([0.06, 0.15, 0.57, 0.72], facecolor=FOND)
        styliser_axes(self.ax)
        self.ax.format_coord = self.coordonnees
        self.fig.text(0.06, 0.945, "Fractale de Newton", color=TEXTE, fontsize=20, fontweight="bold")
        self.texte_sous_titre = self.fig.text(0.06, 0.912, "", color=TEXTE_DOUX, fontsize=10)
        self.texte_vide = self.ax.text(0.5, 0.5, "Choisis les paramètres à droite\npuis clique sur « Calculer »",
                                       transform=self.ax.transAxes, ha="center", va="center",
                                       color=TEXTE_DOUX, fontsize=13, linespacing=1.8)
        self.fig.text(0.345, 0.02, AIDE, color=TEXTE_DOUX, fontsize=9, ha="center")

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

    # -- Panneau de paramètres --
    def construire_panneau(self):
        x0, larg, col2 = 0.685, 0.27, 0.83
        self.fig.patches.append(FancyBboxPatch(
            (0.665, 0.05), 0.31, 0.89, boxstyle="round,pad=0,rounding_size=0.008",
            transform=self.fig.transFigure, facecolor=PANNEAU, edgecolor="#232838", zorder=-1))
        self.fig.text(x0, 0.895, "Paramètres", color=TEXTE, fontsize=14, fontweight="bold")

        self.champs = {}
        textes_initiaux = self.textes(self.p)
        sections = {"largeur": (0.845, "IMAGE"), "min_x": (0.725, "FENÊTRE DU PLAN COMPLEXE"),
                    "eps": (0.535, "CONVERGENCE")}
        y_ligne = {"largeur": 0.775, "min_x": 0.655, "min_y": 0.585, "eps": 0.465}
        y = None
        for n, (cle, libelle, _) in enumerate(CHAMPS):
            if cle in sections:
                ys, titre = sections[cle]
                self.fig.text(x0, ys, titre, color=ACCENT, fontsize=8.5, fontweight="bold")
            if cle in y_ligne:
                y = y_ligne[cle]
            x = x0 if n % 2 == 0 else col2
            self.fig.text(x, y + 0.042, libelle, color=TEXTE_DOUX, fontsize=9)
            ax = self.fig.add_axes([x, y, 0.13, 0.036])
            boite = TextBox(ax, "", initial=textes_initiaux[cle], color=CHAMP, hovercolor=CHAMP_SURVOL,
                            textalignment="left")
            boite.text_disp.set_color(TEXTE)
            boite.text_disp.set_fontsize(8.5)
            if hasattr(boite, "cursor"):
                boite.cursor.set_color(TEXTE)
            for cote in ax.spines.values():
                cote.set_color(BORDURE)
            self.champs[cle] = boite

        self.bouton_vue = self.bouton([x0, 0.37, larg, 0.048], "Recalculer la vue affichée",
                                      self.recalculer_vue)
        self.bouton_carre = self.bouton([x0, 0.31, 0.13, 0.044], "Pixels carrés", self.pixels_carres)
        self.bouton_defaut = self.bouton([col2 - 0.005, 0.31, 0.13, 0.044], "Valeurs par défaut",
                                         self.valeurs_defaut)
        self.bouton_calcul = self.bouton([x0, 0.215, larg, 0.065], "Calculer", self.calculer,
                                         couleur=ACCENT, survol=ACCENT_SURVOL, texte=FOND, taille=13)
        self.bouton_export = self.bouton([x0, 0.075, larg, 0.044], "Enregistrer l'image (PNG)",
                                         self.enregistrer)
        self.texte_statut = self.fig.text(x0, 0.175, "", color=TEXTE_DOUX, fontsize=9.5, va="top")

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
            if cle in ("largeur", "hauteur", "iterations"):
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

    def lire_champs(self):
        """Lit et vérifie les champs ; lève ValueError avec un message clair."""
        p = {}
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
        lignes = [textwrap.fill(l, 46) for l in texte.splitlines()]
        self.texte_statut.set_text("\n".join(lignes))
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
        sauvegarder_parametres(p)
        self.statut(f"Terminé en {duree:.2f} s", SUCCES)

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
        self.remplir(DEFAUTS)
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
        self.p = dict(p)
        self.p["hauteur"], self.p["largeur"] = indices.shape
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
        self.legende = creer_legende(self.fig, indices, 0.345, 0.065)
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
            texte += f"   →   racine {k}" if k >= 1 else "   →   pas de convergence"
        return texte


# --- Lancement ----------------------------------------------------------------
def lire_arguments():
    p = argparse.ArgumentParser(description="Interface de la fractale de Newton")
    p.add_argument("--fichier", default=FICHIER_RESULTATS, help="fichier produit par le programme C++")
    p.add_argument("--bornes", nargs=4, type=float, metavar=("MIN_X", "MAX_X", "MIN_Y", "MAX_Y"),
                   help="zone du plan complexe de results.txt (sinon : celle du dernier calcul)")
    p.add_argument("--eps", type=float, help="précision utilisée pour results.txt")
    p.add_argument("--iterations", type=int, help="nombre d'itérations utilisé pour results.txt")
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

    Application(p, indices, trouver_executable(args.exe))
    plt.show()


if __name__ == "__main__":
    main()
