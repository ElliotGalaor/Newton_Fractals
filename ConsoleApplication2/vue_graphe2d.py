"""Page « Graphes 2D » : tracé de fonctions réelles y = f(x), à la façon de GeoGebra."""
import os
import time

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

import expressions as ex
import newton_calcul as nc
from interface_commune import BORDURE, FOND, SUCCES, ERREUR, TEXTE, TEXTE_DOUX, etiquette
from widgets_fonctions import Curseurs, ListeFonctions, barre_titre, charger_etat, sauver_etat, zone_defilante

FICHIER_ETAT = os.path.join(nc.DOSSIER, "graphes2d.json")


def stylo(couleur, epaisseur):
    """Trait d'épaisseur fixe à l'écran, quel que soit le zoom."""
    s = QtGui.QPen(QtGui.QColor(couleur), epaisseur)
    s.setCosmetic(True)
    s.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    s.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    return s


def lisible(v, resolution):
    """Nombre écrit avec juste assez de décimales pour la résolution donnée (taille d'un pixel…)."""
    if resolution < 1e-4 or abs(v) >= 1e6:
        return nc.coordonnee(v, resolution)
    decimales = max(0, int(np.ceil(-np.log10(max(resolution, 1e-300)))))
    texte = f"{v:.{decimales}f}"
    return "0" if float(texte) == 0 else texte
FONCTIONS_DEPART = [{"texte": "f(x) = sin(x)"}, {"texte": "g(x) = x^2/4 - 2"}, {"texte": "h(x) = a exp(-x^2)"}]
VUE_STANDARD = (-10.0, 10.0, -6.0, 6.0)


class VueGraphe2D(QtWidgets.QWidget):
    NOM = "Graphes 2D"

    def __init__(self, principale):
        super().__init__()
        self.principale = principale
        self.courbes = []                 # (élément tracé, expression, nom, couleur)
        etat = charger_etat(FICHIER_ETAT) or {}
        self.minuteur_sauvegarde = QtCore.QTimer(self)
        self.minuteur_sauvegarde.setSingleShot(True)
        self.minuteur_sauvegarde.setInterval(800)
        self.minuteur_sauvegarde.timeout.connect(self.sauvegarder)
        self.construire_interface(etat)

        x0, x1, y0, y1 = etat.get("vue", VUE_STANDARD)
        self.vb.setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0)
        self.fonctions_changees()

    # -- Construction --------------------------------------------------------
    def construire_interface(self, etat):
        disposition = QtWidgets.QHBoxLayout(self)
        disposition.setContentsMargins(20, 10, 14, 6)
        disposition.setSpacing(18)

        gauche = QtWidgets.QVBoxLayout()
        gauche.setSpacing(4)
        gauche.addLayout(barre_titre(self.NOM, self.principale))
        gauche.addWidget(etiquette("Courbes y = f(x)   ·   écris une fonction à droite, elle s'affiche à la frappe", "ligne1"))
        self.label_infos = etiquette("", "infos")
        gauche.addWidget(self.label_infos)
        gauche.addSpacing(4)

        self.plot = pg.PlotWidget(background=FOND)
        self.plot.hideButtons()
        self.plot.setMenuEnabled(False)
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        police = QtGui.QFont()
        police.setPointSize(9)
        for nom in ("bottom", "left"):
            axe = self.plot.getAxis(nom)
            axe.setPen(pg.mkPen(BORDURE))
            axe.setTextPen(pg.mkPen(TEXTE_DOUX))
            axe.setStyle(tickFont=police)
        self.vb = self.plot.getViewBox()
        self.vb.disableAutoRange()
        # Dans la zone de tracé, uniquement des éléments Qt de base : les éléments de pyqtgraph
        # (courbes, lignes, points) ne s'y dessinent pas avec le PySide6 6.9 de MSYS2.
        # Axes passant par l'origine, comme dans GeoGebra (recalés à chaque changement de vue)
        self.axes_origine = []
        for _ in range(2):
            ligne = QtWidgets.QGraphicsLineItem()
            ligne.setPen(stylo(TEXTE_DOUX, 1.2))
            self.vb.addItem(ligne, ignoreBounds=True)
            self.axes_origine.append(ligne)
        self.legende = self.plot.addLegend(offset=(12, 12), labelTextColor=TEXTE,
                                           brush=pg.mkBrush(21, 25, 34, 220), pen=pg.mkPen(BORDURE))
        # Point qui suit la courbe la plus proche du curseur (taille fixe à l'écran)
        self.point = QtWidgets.QGraphicsEllipseItem(-6, -6, 12, 12)
        self.point.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.point.setPen(stylo(FOND, 2))
        self.point.setZValue(10)
        self.point.hide()
        self.vb.addItem(self.point, ignoreBounds=True)
        self.vb.sigRangeChanged.connect(self.vue_changee)
        self.plot.scene().sigMouseMoved.connect(self.souris_bougee)
        gauche.addWidget(self.plot, 1)
        disposition.addLayout(gauche, 1)

        panneau, v = zone_defilante()
        v.addWidget(etiquette("Fonctions", "entete"))
        v.addWidget(etiquette("Exemples : sin(x),  x^2 - 3,  2x exp(-x),  f(x) = a sin(b x),  1/x,  sqrt(4 - x²)",
                              "libelle"))
        self.liste = ListeFonctions(("x",), ex.EXEMPLES_2D, etat.get("fonctions", FONCTIONS_DEPART))
        self.liste.changee.connect(self.fonctions_changees)
        v.addWidget(self.liste)

        v.addSpacing(10)
        self.titre_parametres = etiquette("PARAMÈTRES", "section")
        v.addWidget(self.titre_parametres)
        self.curseurs = Curseurs(etat.get("parametres"))
        self.curseurs.changes.connect(self.redessiner)
        v.addWidget(self.curseurs)

        v.addSpacing(10)
        v.addWidget(etiquette("AFFICHAGE", "section"))
        self.case_orthonorme = QtWidgets.QCheckBox("Repère orthonormé (même échelle sur les deux axes)")
        self.case_orthonorme.setChecked(etat.get("orthonorme", True))
        self.case_orthonorme.toggled.connect(self.vb.setAspectLocked)
        self.vb.setAspectLocked(self.case_orthonorme.isChecked())
        v.addWidget(self.case_orthonorme)
        self.case_grille = QtWidgets.QCheckBox("Grille")
        self.case_grille.setChecked(etat.get("grille", True))
        self.case_grille.toggled.connect(lambda c: self.plot.showGrid(x=c, y=c, alpha=0.12))
        self.plot.showGrid(x=self.case_grille.isChecked(), y=self.case_grille.isChecked(), alpha=0.12)
        v.addWidget(self.case_grille)
        ligne = QtWidgets.QHBoxLayout()
        for texte, action in (("Vue standard", self.vue_standard), ("Ajuster aux courbes", self.ajuster),
                              ("Export PNG", self.exporter)):
            b = QtWidgets.QPushButton(texte)
            b.clicked.connect(lambda _=False, a=action: a())
            ligne.addWidget(b)
        v.addLayout(ligne)
        self.label_statut = QtWidgets.QLabel("")
        self.label_statut.setWordWrap(True)
        v.addWidget(self.label_statut)
        v.addStretch(1)
        v.addWidget(etiquette("Molette : zoom   ·   clic-glisser : déplacer\n"
                              "Variables : x · paramètres : toute autre lettre (a, b, k…)\n"
                              "Fonctions : sin cos tan exp ln log sqrt abs floor…   ·   π, e", "aide"))
        disposition.addWidget(panneau)

    # -- Mise à jour -----------------------------------------------------------
    def fonctions_changees(self):
        self.curseurs.mettre_a_jour(self.liste.parametres())
        self.titre_parametres.setVisible(bool(self.liste.parametres()))
        # Recrée les courbes (couleur, nom, visibilité ont pu changer)
        for courbe, *_ in self.courbes:
            self.vb.removeItem(courbe)
        self.legende.clear()
        self.courbes = []
        for expression, couleur, visible, nom in self.liste.fonctions():
            if not visible:
                continue
            courbe = QtWidgets.QGraphicsPathItem()
            courbe.setPen(stylo(couleur, 2.5))
            self.vb.addItem(courbe, ignoreBounds=True)
            # (élément jamais tracé : il ne sert qu'à dessiner l'échantillon de la légende)
            self.legende.addItem(pg.PlotDataItem(pen=pg.mkPen(couleur, width=2.5)), f"{nom}(x) = {expression.corps}")
            self.courbes.append((courbe, expression, nom, couleur))
        self.redessiner()

    def vue_changee(self, *_):
        self.redessiner()

    def redessiner(self):
        """Recalcule les courbes sur la largeur visible (toujours nettes, quel que soit le zoom)."""
        (x0, x1), (y0, y1) = self.vb.viewRange()
        marge = (x1 - x0) * 0.05
        parametres = self.curseurs.valeurs_actuelles()
        n = int(min(4000, max(800, self.vb.width() * 2)))
        for courbe, expression, *_ in self.courbes:
            x, y = ex.echantillonner_courbe(expression, x0 - marge, x1 + marge, y1 - y0, parametres, n)
            # Les valeurs très loin de la vue sont ramenées à son bord (Qt dessine mal les grands nombres)
            y = np.clip(y, y0 - 10 * (y1 - y0), y1 + 10 * (y1 - y0))
            courbe.setPath(pg.functions.arrayToQPath(x, y, connect="finite"))
        self.axes_origine[0].setLine(x0 - marge, 0, x1 + marge, 0)
        self.axes_origine[1].setLine(0, y0 - marge, 0, y1 + marge)
        rx, ry = (x1 - x0) / 200, (y1 - y0) / 200
        self.label_infos.setText(f"x ∈ [{lisible(x0, rx)}, {lisible(x1, rx)}]   ·   y ∈ [{lisible(y0, ry)}, "
                                 f"{lisible(y1, ry)}]   ·   {len(self.courbes)} courbe(s)")
        self.minuteur_sauvegarde.start()

    def souris_bougee(self, pos):
        """Coordonnées sous la souris ; un point suit la courbe la plus proche."""
        if not self.isVisible() or not self.vb.sceneBoundingRect().contains(pos):
            return
        p = self.vb.mapSceneToView(pos)
        (x0, x1), (y0, y1) = self.vb.viewRange()
        px = (x1 - x0) / max(self.vb.width(), 1)      # taille d'un pixel
        py = (y1 - y0) / max(self.vb.height(), 1)
        texte = f"x = {lisible(p.x(), px)}    y = {lisible(p.y(), py)}"
        parametres = self.curseurs.valeurs_actuelles()
        meilleur, distance_min = None, None
        valeurs = []
        for courbe, expression, nom, couleur in self.courbes:
            yv = float(expression.evaluer(dict(parametres, x=np.array([p.x()])))[0])
            if np.isfinite(yv):
                valeurs.append(f"{nom}({lisible(p.x(), px)}) = {lisible(yv, py / 10)}")
                d = abs(yv - p.y())
                if distance_min is None or d < distance_min:
                    meilleur, distance_min = (p.x(), yv, couleur), d
        if valeurs:
            texte += "     ·     " + "     ".join(valeurs)
        # Le point n'apparaît que si la courbe est proche du curseur (moins de 40 pixels)
        pixel_y = (y1 - y0) / max(self.vb.height(), 1)
        if meilleur and distance_min <= 40 * pixel_y:
            self.point.setPos(meilleur[0], meilleur[1])
            self.point.setBrush(QtGui.QColor(meilleur[2]))
            self.point.show()
        else:
            self.point.hide()
        self.principale.statusBar().showMessage(texte)

    # -- Actions ---------------------------------------------------------------
    def vue_standard(self):
        x0, x1, y0, y1 = VUE_STANDARD
        self.vb.setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0)

    def ajuster(self):
        """Cadre les courbes visibles dans la largeur actuelle (sans les valeurs extrêmes)."""
        (x0, x1), _ = self.vb.viewRange()
        parametres = self.curseurs.valeurs_actuelles()
        ys = [expression.evaluer(dict(parametres, x=np.linspace(x0, x1, 2000))) for _, expression, *_ in self.courbes]
        ys = np.concatenate([y[np.isfinite(y)] for y in ys]) if ys else np.array([])
        if ys.size == 0:
            self.statut("Aucune courbe à cadrer.")
            return
        bas, haut = np.percentile(ys, [2, 98])
        if haut - bas < 1e-9:
            bas, haut = bas - 1, haut + 1
        marge = (haut - bas) * 0.1
        self.case_orthonorme.setChecked(False)   # sinon la hauteur imposerait la largeur
        self.vb.setRange(xRange=(x0, x1), yRange=(bas - marge, haut + marge), padding=0)
        self.statut("Vue ajustée aux courbes (repère orthonormé désactivé).")

    def exporter(self):
        defaut = os.path.join(nc.DOSSIER, time.strftime("graphe_%Y%m%d_%H%M%S.png"))
        chemin, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Enregistrer l'image", defaut, "Images PNG (*.png)")
        if not chemin:
            return
        if self.plot.grab().save(chemin):
            self.statut(f"Image enregistrée : {os.path.basename(chemin)}", SUCCES)
        else:
            self.statut(f"Enregistrement impossible : {chemin}", ERREUR)

    def statut(self, texte, couleur=TEXTE_DOUX):
        self.label_statut.setText(texte)
        self.label_statut.setStyleSheet(f"color: {couleur};")

    def sauvegarder(self):
        (x0, x1), (y0, y1) = self.vb.viewRange()
        sauver_etat(FICHIER_ETAT, {"fonctions": self.liste.etat(), "parametres": self.curseurs.valeurs,
                                   "vue": [x0, x1, y0, y1], "orthonorme": self.case_orthonorme.isChecked(),
                                   "grille": self.case_grille.isChecked()})
