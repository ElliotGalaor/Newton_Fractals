"""Visualisations mathématiques : point d'entrée de l'interface Qt.

On arrive sur une page d'accueil qui présente les visualisations disponibles :
fractales de Newton, ensemble de Mandelbrot, graphes de fonctions 2D (à la façon de
GeoGebra) et surfaces 3D. On passe de l'une à l'autre par l'accueil, le bouton
« ← Accueil » ou le menu « Visualisations » (Ctrl+0 à Ctrl+4).
Pour les fractales, le calcul C++ (main.exe) tourne en arrière-plan ; après un zoom
ou un déplacement, la vue est recalculée automatiquement en pleine résolution.

Utilisation :
    python NewtonFractalsDrawing.py                         (page d'accueil)
    python NewtonFractalsDrawing.py --vue graphe2d          (ouvre directement une visualisation)
    python NewtonFractalsDrawing.py --bornes -0.3 0.3 -0.3 0.3   (accueil ; la page Newton affichera results.txt)
    python NewtonFractalsDrawing.py --enregistrer fractale.png    (image de Newton seule, sans fenêtre)
    python NewtonFractalsDrawing.py --exe chemin\\vers\\programme.exe

Dans une visualisation :
    molette        zoom centré sur la souris
    clic-glisser   déplacer la vue
    H              revenir à la vue de l'image calculée
    Entrée         (dans un champ) lancer le calcul

Nécessite PySide6 et pyqtgraph, installés depuis PyPI (python -m pip install pyside6
pyqtgraph) : les DLL Qt de MSYS2 ne sont pas signées et Windows peut les bloquer. Si le
script est lancé avec un Python où Qt ne se charge pas, il se relance tout seul avec un
autre Python où PySide6 fonctionne (par exemple celui de Windows).
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np


def _relancer_avec_un_autre_python():
    """Qt n'a pas pu être chargé avec ce Python (par exemple : DLL de MSYS2 non signées,
    bloquées par le contrôle d'applications de Windows). On cherche un autre Python où
    PySide6 et pyqtgraph fonctionnent, et on relance ce script avec lui."""
    if os.environ.get("NEWTON_FRACTALS_RELANCE"):
        return   # déjà relancé une fois : on n'insiste pas
    candidats = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Python", "bin", "python.exe"),
                 shutil.which("py")]
    for dossier in os.environ.get("PATH", "").split(os.pathsep):
        candidats += [os.path.join(dossier, nom) for nom in ("python.exe", "python3.exe")]
    actuel = os.path.normcase(os.path.abspath(sys.executable))
    vus = set()
    for c in candidats:
        if not c or not os.path.isfile(c):
            continue
        cle = os.path.normcase(os.path.abspath(c))
        if cle == actuel or cle in vus:
            continue
        vus.add(cle)
        try:
            essai = subprocess.run([c, "-c", "import PySide6.QtWidgets, pyqtgraph"],
                                   capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if essai.returncode == 0:
            env = dict(os.environ, NEWTON_FRACTALS_RELANCE="1")
            sys.exit(subprocess.call([c, os.path.abspath(__file__)] + sys.argv[1:], env=env))


try:
    import pyqtgraph  # noqa: F401  (vérifie que pyqtgraph se charge avec ce Qt)
    from PySide6 import QtGui, QtWidgets
except ImportError as erreur_qt:
    _relancer_avec_un_autre_python()
    sys.exit(f"Impossible de charger Qt avec ce Python ({sys.executable}) :\n  {erreur_qt}\n\n"
             "Installe PySide6 et pyqtgraph dans ton Python Windows (leurs DLL sont signées) :\n"
             '  & "$env:LOCALAPPDATA\\Python\\bin\\python.exe" -m pip install pyside6 pyqtgraph\n'
             "puis relance : python NewtonFractalsDrawing.py")

import mandelbrot_calcul as mc
import newton_calcul as nc
from accueil import PageAccueil
from interface_commune import STYLE, sauver_png_rgb
from vue_graphe2d import VueGraphe2D
from vue_mandelbrot import VueMandelbrot
from vue_newton import VueNewton
from vue_surfaces3d import VueSurfaces3D

TITRE = "Visualisations mathématiques"


def preparer_mandelbrot():
    """Paramètres de départ de la page Mandelbrot, et dernier résultat s'il est encore valable."""
    p = dict(mc.DEFAUTS)
    memo = nc.charger_parametres(mc.FICHIER_PARAMETRES)
    if memo:
        p.update({k: memo[k] for k in mc.DEFAUTS if k in memo})
    mu = nc.resultat_memorise(memo, mc.lire_binaire)
    if mu is not None:
        p["hauteur"], p["largeur"] = mu.shape
    return p, mu


class FenetrePrincipale(QtWidgets.QMainWindow):
    """Pages empilées : l'accueil et les visualisations (créées à leur première ouverture)."""

    def __init__(self, args, executable):
        super().__init__()
        self.args = args
        self.executable = executable
        self.vues = {}
        self.pile = QtWidgets.QStackedWidget()
        self.accueil = PageAccueil(self.ouvrir)
        self.pile.addWidget(self.accueil)
        self.setCentralWidget(self.pile)

        menu = self.menuBar().addMenu("&Visualisations")
        for texte, raccourci, action in (("Accueil", "Ctrl+0", self.aller_accueil),
                                         ("Fractales de Newton", "Ctrl+1", lambda: self.ouvrir("newton")),
                                         ("Ensemble de Mandelbrot", "Ctrl+2", lambda: self.ouvrir("mandelbrot")),
                                         ("Graphes 2D", "Ctrl+3", lambda: self.ouvrir("graphe2d")),
                                         ("Surfaces 3D", "Ctrl+4", lambda: self.ouvrir("surfaces3d"))):
            a = QtGui.QAction(texte, self)
            a.setShortcut(QtGui.QKeySequence(raccourci))
            a.triggered.connect(action)
            menu.addAction(a)
            if texte in ("Accueil", "Ensemble de Mandelbrot"):
                menu.addSeparator()
        menu.addSeparator()
        quitter = QtGui.QAction("Quitter", self)
        quitter.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        quitter.triggered.connect(self.close)
        menu.addAction(quitter)
        self.aller_accueil()

    def creer_vue(self, nom):
        if nom == "newton":
            p, indices = nc.preparer(self.args)
            return VueNewton(self, p, indices, self.executable)
        if nom == "mandelbrot":
            p, mu = preparer_mandelbrot()
            return VueMandelbrot(self, p, mu, self.executable)
        if nom == "graphe2d":
            return VueGraphe2D(self)
        return VueSurfaces3D(self)

    def ouvrir(self, nom):
        if nom not in self.vues:
            self.vues[nom] = self.creer_vue(nom)
            self.pile.addWidget(self.vues[nom])
        vue = self.vues[nom]
        self.pile.setCurrentWidget(vue)
        self.setWindowTitle(f"{vue.NOM} — {TITRE}")
        self.statusBar().showMessage("Survole l'image pour voir les coordonnées et la valeur calculée.")

    def aller_accueil(self):
        self.pile.setCurrentWidget(self.accueil)
        self.setWindowTitle(TITRE)
        self.statusBar().showMessage("Choisis une visualisation.")


# --- Lancement ----------------------------------------------------------------
def lire_arguments():
    p = argparse.ArgumentParser(description=TITRE)
    p.add_argument("--vue", choices=("accueil", "newton", "mandelbrot", "graphe2d", "surfaces3d"), default=None,
                   help="page ouverte au lancement (par défaut : l'accueil)")
    p.add_argument("--fichier", default=nc.FICHIER_RESULTATS, help="résultat de Newton à afficher (results.txt ou .bin)")
    p.add_argument("--bornes", nargs=4, type=float, metavar=("MIN_X", "MAX_X", "MIN_Y", "MAX_Y"),
                   help="zone du plan complexe de --fichier (affiché à l'ouverture de la page Newton)")
    p.add_argument("--eps", type=float, help="précision utilisée pour --fichier")
    p.add_argument("--iterations", type=int, help="nombre d'itérations utilisé pour --fichier")
    p.add_argument("--polynome", help="polynôme utilisé pour --fichier, ex. \"z^3 - 2z + 2\"")
    p.add_argument("--exe", help="chemin du programme C++ compilé (sinon recherche automatique)")
    p.add_argument("--enregistrer", metavar="IMAGE.png",
                   help="enregistre l'image de Newton (--fichier) dans ce fichier, sans ouvrir la fenêtre")
    return p.parse_args()


def main():
    args = lire_arguments()
    app = QtWidgets.QApplication(sys.argv)

    if args.enregistrer:
        p, indices = nc.preparer(args)
        if indices is None:
            indices = nc.lire_fichier_resultat(args.fichier)
        if not sauver_png_rgb(nc.table_couleurs()[np.clip(indices, 0, 255)], args.enregistrer):
            sys.exit(f"Enregistrement impossible : {args.enregistrer}")
        print(f"Image enregistree : {args.enregistrer}")
        return

    app.setStyleSheet(STYLE)
    fenetre = FenetrePrincipale(args, nc.trouver_executable(args.exe))
    # On arrive toujours sur l'accueil (même lancé par main.exe : la page Newton affichera
    # alors son résultat à l'ouverture), sauf si --vue demande une page précise
    if args.vue and args.vue != "accueil":
        fenetre.ouvrir(args.vue)
    fenetre.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
