"""Page « Surfaces 3D » : surfaces z = f(x, y) et équations en x, y, z (sphère…) dans R³,
manipulables à la souris."""
import os
import sys
import time
import warnings

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

import expressions as ex
import newton_calcul as nc
from interface_commune import ERREUR, SUCCES, TEXTE_DOUX, etiquette
from widgets_fonctions import Curseurs, ListeFonctions, barre_titre, charger_etat, sauver_etat, zone_defilante

try:
    import pyqtgraph.opengl as gl
    ERREUR_OPENGL = None
except Exception as e:   # PyOpenGL absent, ou OpenGL indisponible
    gl = None
    ERREUR_OPENGL = e

FICHIER_ETAT = os.path.join(nc.DOSSIER, "surfaces3d.json")
RESOLUTION_EQUATIONS = 120   # points par côté de la grille 3D des équations (120³ ≈ 1,7 million de points)
RESOLUTION_APERCU = 56       # pendant qu'un curseur bouge : aperçu rapide
FONCTIONS_DEPART = [{"texte": "z = sin(x) cos(y)"}]
DOMAINE = {"min_x": -5.0, "max_x": 5.0, "min_y": -5.0, "max_y": 5.0, "resolution": 120, "limite_z": 5.0}
CHAMPS = [("min_x", "x min", float), ("max_x", "x max", float), ("min_y", "y min", float),
          ("max_y", "y max", float), ("resolution", "Points par côté", int), ("limite_z", "z entre ± (coupure)", float)]

# Dégradé pour la coloration selon la hauteur (bas → haut)
_DEGRADE_HAUTEUR = np.array([[0x2b, 0x1e, 0x6e], [0x11, 0x8a, 0xb2], [0x06, 0xd6, 0xa0],
                             [0xff, 0xd1, 0x66], [0xf7, 0x25, 0x85]], dtype=float) / 255


def couleurs_hauteur(z, z0, z1):
    t = np.clip((z - z0) / max(z1 - z0, 1e-12), 0, 1) * (len(_DEGRADE_HAUTEUR) - 1)
    k = np.minimum(np.floor(t).astype(int), len(_DEGRADE_HAUTEUR) - 2)
    f = (t - k)[..., None]
    return _DEGRADE_HAUTEUR[k] * (1 - f) + _DEGRADE_HAUTEUR[k + 1] * f


def hex_rgb(couleur):
    return np.array([int(couleur[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255


class VueSurfaces3D(QtWidgets.QWidget):
    NOM = "Surfaces 3D"

    def __init__(self, principale):
        super().__init__()
        self.principale = principale
        self.surfaces = []
        etat = charger_etat(FICHIER_ETAT) or {}
        self.domaine = dict(DOMAINE, **{k: etat[k] for k in DOMAINE if k in etat})
        self.minuteur = QtCore.QTimer(self)   # regroupe les mises à jour pendant la frappe
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(60)
        self.minuteur.timeout.connect(self.redessiner)
        # Pendant qu'un curseur bouge (ou s'anime), les équations sont calculées en aperçu
        # rapide ; la pleine résolution revient peu après le dernier mouvement
        self.apercu_rapide = False
        self.minuteur_qualite = QtCore.QTimer(self)
        self.minuteur_qualite.setSingleShot(True)
        self.minuteur_qualite.setInterval(450)
        self.minuteur_qualite.timeout.connect(self.pleine_resolution)
        self.construire_interface(etat)
        if gl is not None:
            self.vue_par_defaut()
            self.fonctions_changees()

    # -- Construction --------------------------------------------------------
    def construire_interface(self, etat):
        disposition = QtWidgets.QHBoxLayout(self)
        disposition.setContentsMargins(20, 10, 14, 6)
        disposition.setSpacing(18)

        gauche = QtWidgets.QVBoxLayout()
        gauche.setSpacing(4)
        gauche.addLayout(barre_titre(self.NOM, self.principale))
        gauche.addWidget(etiquette("Surfaces z = f(x, y)   ·   glisser : tourner   ·   molette : zoom   ·   "
                                   "clic-molette (ou Ctrl+glisser) : déplacer", "ligne1"))
        self.label_infos = etiquette("", "infos")
        gauche.addWidget(self.label_infos)
        gauche.addSpacing(4)
        if gl is None:
            # Commande pour le Python réellement utilisé (pas forcément celui que « python » désigne)
            if "msys64" in sys.executable.lower():
                commande = "pacman -S mingw-w64-ucrt-x86_64-python-pyopengl"
            else:
                commande = f'& "{sys.executable}" -m pip install PyOpenGL'
            message = etiquette("La 3D a besoin de PyOpenGL, qui n'a pas pu être chargé :\n"
                                f"{ERREUR_OPENGL}\n\nInstalle-le pour ce Python, puis relance :\n"
                                f"    {commande}", "accroche")
            message.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            message.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            gauche.addWidget(message, 1)
        else:
            self.vue3d = gl.GLViewWidget()
            self.vue3d.setBackgroundColor((14, 17, 23))
            gauche.addWidget(self.vue3d, 1)
            self.grille = gl.GLGridItem()
            self.grille.setColor((139, 147, 167, 60))
            self.vue3d.addItem(self.grille)
            self.axes = []
        disposition.addLayout(gauche, 1)

        panneau, v = zone_defilante()
        v.addWidget(etiquette("Surfaces", "entete"))
        v.addWidget(etiquette("Fonctions : sin(x) cos(y),  x^2 - y^2,  z = a sin(sqrt(x²+y²))\n"
                              "Équations : x² + y² + z² = 9 (sphère),  x² + y² = 4,  x² + y² - z² = 1",
                              "libelle"))
        self.liste = ListeFonctions(("x", "y"), ex.EXEMPLES_3D, etat.get("fonctions", FONCTIONS_DEPART),
                                    equations=True)
        self.liste.changee.connect(self.fonctions_changees)
        v.addWidget(self.liste)

        v.addSpacing(10)
        self.titre_parametres = etiquette("PARAMÈTRES", "section")
        v.addWidget(self.titre_parametres)
        self.curseurs = Curseurs(etat.get("parametres"))
        self.curseurs.changes.connect(self.parametres_changes)
        v.addWidget(self.curseurs)

        v.addSpacing(10)
        v.addWidget(etiquette("DOMAINE", "section"))
        grille = QtWidgets.QGridLayout()
        grille.setHorizontalSpacing(12)
        grille.setVerticalSpacing(3)
        self.champs = {}
        for n, (cle, libelle, type_) in enumerate(CHAMPS):
            ligne, col = 2 * (n // 2), n % 2
            grille.addWidget(etiquette(libelle, "libelle"), ligne, col)
            champ = QtWidgets.QLineEdit(str(int(self.domaine[cle])) if type_ is int else f"{self.domaine[cle]:g}")
            champ.returnPressed.connect(self.domaine_change)
            champ.editingFinished.connect(self.domaine_change)
            grille.addWidget(champ, ligne + 1, col)
            self.champs[cle] = champ
        v.addLayout(grille)

        v.addSpacing(10)
        v.addWidget(etiquette("AFFICHAGE", "section"))
        self.case_hauteur = QtWidgets.QCheckBox("Couleur selon la hauteur")
        self.case_hauteur.setChecked(etat.get("couleur_hauteur", False))
        self.case_fil = QtWidgets.QCheckBox("Fil de fer")
        self.case_fil.setChecked(etat.get("fil_de_fer", False))
        self.case_axes = QtWidgets.QCheckBox("Axes et grille")
        self.case_axes.setChecked(etat.get("axes", True))
        for case in (self.case_hauteur, self.case_fil, self.case_axes):
            case.toggled.connect(lambda _: self.minuteur.start())
            v.addWidget(case)
        ligne = QtWidgets.QHBoxLayout()
        for texte, action in (("Vue par défaut", self.vue_par_defaut), ("Vue de dessus", self.vue_dessus),
                              ("Export PNG", self.exporter)):
            b = QtWidgets.QPushButton(texte)
            b.clicked.connect(lambda _=False, a=action: a())
            ligne.addWidget(b)
        v.addLayout(ligne)
        self.label_statut = QtWidgets.QLabel("")
        self.label_statut.setWordWrap(True)
        v.addWidget(self.label_statut)
        v.addStretch(1)
        v.addWidget(etiquette("Fonction z = f(x, y) : variables x, y · équation (avec =) : x, y et z\n"
                              "Paramètres : toute autre lettre (a, b, k…)\n"
                              "Fonctions : sin cos tan exp ln log sqrt abs…   ·   π, e", "aide"))
        disposition.addWidget(panneau)

    # -- Mise à jour -----------------------------------------------------------
    def fonctions_changees(self):
        noms = self.liste.parametres()
        self.curseurs.mettre_a_jour(noms)
        self.titre_parametres.setVisible(bool(noms))
        self.minuteur.start()

    def parametres_changes(self):
        self.apercu_rapide = True
        # (sans relancer le délai s'il court déjà : pendant une animation, les changements
        # arrivent toutes les 40 ms et le redessin n'aurait sinon jamais lieu)
        if not self.minuteur.isActive():
            self.minuteur.start()
        self.minuteur_qualite.start()   # redémarre : la pleine résolution attend la fin du mouvement

    def pleine_resolution(self):
        self.apercu_rapide = False
        self.redessiner()

    def domaine_change(self):
        try:
            d = {cle: (int(float(self.champs[cle].text().replace(",", "."))) if t is int
                       else float(self.champs[cle].text().replace(",", ".")))
                 for cle, _, t in CHAMPS}
            if d["min_x"] >= d["max_x"] or d["min_y"] >= d["max_y"]:
                raise ValueError("il faut min < max")
            if not 10 <= d["resolution"] <= 400:
                raise ValueError("points par côté : entre 10 et 400")
            if d["limite_z"] <= 0:
                raise ValueError("la coupure de z doit être positive")
        except ValueError as e:
            self.statut(f"Domaine : {e}", ERREUR)
            return
        if d != self.domaine:
            self.domaine = d
            self.statut("")
            self.minuteur.start()

    def redessiner(self):
        if gl is None:
            return
        for item in self.surfaces + self.axes:
            self.vue3d.removeItem(item)
        self.surfaces, self.axes = [], []
        d = self.domaine
        n = d["resolution"]
        xs = np.linspace(d["min_x"], d["max_x"], n)
        ys = np.linspace(d["min_y"], d["max_y"], n)
        X, Y = np.meshgrid(xs, ys, indexing="ij")    # GLSurfacePlotItem : z[i, j] au point (xs[i], ys[j])
        parametres = self.curseurs.valeurs_actuelles()
        limite = d["limite_z"]
        z_vus = []
        for expression, couleur, visible, _nom in self.liste.fonctions():
            if not visible:
                continue
            if expression.implicite:
                surface, z_surface = self.surface_implicite(expression, couleur, parametres)
                if surface is not None:
                    self.vue3d.addItem(surface)
                    self.surfaces.append(surface)
                    z_vus.append(z_surface)
                continue
            Z = expression.evaluer(dict(parametres, x=X, y=Y))
            trous = ~np.isfinite(Z)
            Z = np.clip(np.where(trous, 0.0, Z), -limite, limite)
            z_vus.append(Z[~trous])
            if self.case_hauteur.isChecked():
                rgb = couleurs_hauteur(Z, -limite, limite)
            else:
                # Couleur de la fonction, légèrement modulée par la hauteur pour mieux voir le relief
                t = (Z - Z.min()) / max(np.ptp(Z), 1e-12)
                rgb = hex_rgb(couleur)[None, None, :] * (0.55 + 0.45 * t[..., None])
            alpha = np.where(trous, 0.0, 1.0)[..., None]
            couleurs = np.concatenate([rgb, alpha], axis=-1).astype(np.float32)
            surface = gl.GLSurfacePlotItem(x=xs, y=ys, z=Z, colors=couleurs, shader="shaded",
                                           computeNormals=True, smooth=True,
                                           drawEdges=self.case_fil.isChecked(), edgeColor=(1, 1, 1, 0.25),
                                           glOptions="translucent" if trous.any() else "opaque")
            self.vue3d.addItem(surface)
            self.surfaces.append(surface)

        self.dessiner_axes()
        z_tous = np.concatenate(z_vus) if z_vus else np.array([])
        texte_z = (f"   ·   z ∈ [{z_tous.min():.3g}, {z_tous.max():.3g}]" if z_tous.size else "")
        equations = any(e.implicite for e, _, v, _ in self.liste.fonctions() if v)
        n3 = min(n, RESOLUTION_EQUATIONS)
        texte_grille = f"{n} × {n} points" + (f" (équations : {n3}³)" if equations else "")
        self.label_infos.setText(f"x ∈ [{d['min_x']:g}, {d['max_x']:g}]   ·   y ∈ [{d['min_y']:g}, {d['max_y']:g}]"
                                 f"{texte_z}   ·   {len(self.surfaces)} surface(s), {texte_grille}")
        self.sauvegarder()

    def surface_implicite(self, expression, couleur, parametres):
        """Surface F(x, y, z) = 0 sur le domaine (z entre ± la limite), par la méthode des
        « marching cubes » : F est évaluée sur une grille 3D, et la surface est extraite là
        où F change de signe (pg.isosurface). Renvoie (élément 3D ou None, hauteurs z)."""
        d = self.domaine
        n = min(d["resolution"], RESOLUTION_APERCU if self.apercu_rapide else RESOLUTION_EQUATIONS)
        limite = d["limite_z"]
        bornes = [(d["min_x"], d["max_x"]), (d["min_y"], d["max_y"]), (-limite, limite)]
        axes = [np.linspace(a, b, n) for a, b in bornes]
        X, Y, Z = np.meshgrid(*axes, indexing="ij")
        F = expression.evaluer(dict(parametres, x=X, y=Y, z=Z))
        trous = np.isnan(F)
        if trous.all():
            return None, np.array([])
        F = np.where(trous, np.nanmax(np.abs(F)) + 1.0, F)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore")   # (avertissements sans conséquence de pyqtgraph 0.13 avec numpy 2)
            sommets, faces = pg.isosurface(F, 0.0)
        if not len(faces):
            return None, np.array([])
        # Au bord d'une zone où F n'est pas définie (ex. sqrt d'un négatif), le changement de
        # signe est artificiel : on retire les triangles qui touchent ces cases.
        if trous.any():
            voisins = trous.copy()
            for axe in range(3):
                voisins |= np.roll(trous, 1, axis=axe) | np.roll(trous, -1, axis=axe)
            indices = np.clip(np.floor(sommets).astype(int), 0, n - 1)
            sommet_douteux = voisins[indices[:, 0], indices[:, 1], indices[:, 2]]
            faces = faces[~sommet_douteux[faces].any(axis=1)]
            if not len(faces):
                return None, np.array([])
        # Coordonnées de grille → coordonnées réelles
        sommets = np.asarray(sommets, dtype=float)
        for k, (a, b) in enumerate(bornes):
            sommets[:, k] = a + sommets[:, k] * (b - a) / (n - 1)
        z = sommets[:, 2]
        if self.case_hauteur.isChecked():
            rgb = couleurs_hauteur(z, -limite, limite)
        else:
            t = (z - z.min()) / max(np.ptp(z), 1e-12)
            rgb = hex_rgb(couleur)[None, :] * (0.55 + 0.45 * t[:, None])
        couleurs = np.concatenate([rgb, np.ones((len(z), 1))], axis=1).astype(np.float32)
        maillage = gl.MeshData(vertexes=sommets, faces=faces, vertexColors=couleurs)
        surface = gl.GLMeshItem(meshdata=maillage, smooth=True, shader="shaded",
                                drawEdges=self.case_fil.isChecked(), edgeColor=(1, 1, 1, 0.25), glOptions="opaque")
        return surface, z

    def dessiner_axes(self):
        d = self.domaine
        etendue = max(abs(d["min_x"]), abs(d["max_x"]), abs(d["min_y"]), abs(d["max_y"]))
        self.grille.setVisible(self.case_axes.isChecked())
        pas = 10 ** np.floor(np.log10(max(etendue, 1e-9)))
        self.grille.setSize(2 * etendue, 2 * etendue)
        self.grille.setSpacing(pas, pas)
        if not self.case_axes.isChecked():
            return
        longueur = etendue * 1.15
        for direction, couleur, nom in (((1, 0, 0), (1.0, 0.42, 0.51, 1), "x"), ((0, 1, 0), (0.02, 0.84, 0.63, 1), "y"),
                                        ((0, 0, 1), (0.30, 0.79, 0.94, 1), "z")):
            fin = np.array(direction, dtype=float) * longueur
            ligne = gl.GLLinePlotItem(pos=np.array([-fin, fin]), color=couleur, width=2, antialias=True,
                                      glOptions="opaque")   # (masqué par les surfaces qui sont devant)
            self.vue3d.addItem(ligne)
            self.axes.append(ligne)
            if hasattr(gl, "GLTextItem"):
                texte = gl.GLTextItem(pos=fin * 1.04, text=nom, color=tuple(int(c * 255) for c in couleur))
                self.vue3d.addItem(texte)
                self.axes.append(texte)

    # -- Actions ---------------------------------------------------------------
    def vue_par_defaut(self):
        if gl is None:
            return
        d = self.domaine
        etendue = max(d["max_x"] - d["min_x"], d["max_y"] - d["min_y"])
        self.vue3d.setCameraPosition(pos=QtGui.QVector3D(0, 0, 0), distance=etendue * 1.8,
                                     elevation=28, azimuth=-55)

    def vue_dessus(self):
        if gl is None:
            return
        d = self.domaine
        etendue = max(d["max_x"] - d["min_x"], d["max_y"] - d["min_y"])
        self.vue3d.setCameraPosition(pos=QtGui.QVector3D(0, 0, 0), distance=etendue * 1.8,
                                     elevation=90, azimuth=-90)

    def exporter(self):
        if gl is None:
            return
        defaut = os.path.join(nc.DOSSIER, time.strftime("surface_%Y%m%d_%H%M%S.png"))
        chemin, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Enregistrer l'image", defaut, "Images PNG (*.png)")
        if not chemin:
            return
        if self.vue3d.grabFramebuffer().save(chemin):
            self.statut(f"Image enregistrée : {os.path.basename(chemin)}", SUCCES)
        else:
            self.statut(f"Enregistrement impossible : {chemin}", ERREUR)

    def statut(self, texte, couleur=TEXTE_DOUX):
        self.label_statut.setText(texte)
        self.label_statut.setStyleSheet(f"color: {couleur};")

    def sauvegarder(self):
        sauver_etat(FICHIER_ETAT, dict(self.domaine, fonctions=self.liste.etat(), parametres=self.curseurs.valeurs,
                                       couleur_hauteur=self.case_hauteur.isChecked(),
                                       fil_de_fer=self.case_fil.isChecked(), axes=self.case_axes.isChecked()))
