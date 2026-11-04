"""Éléments d'interface communs à toutes les visualisations : thème, axes, et la classe
de base VueFractale (image zoomable, panneau de paramètres, calcul C++ en arrière-plan,
recalcul automatique après un zoom, survol, export PNG)."""
import os
import time

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

import newton_calcul as nc

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

STYLE = f"""
QMainWindow, QWidget {{ background: {FOND}; color: {TEXTE}; font-family: "Segoe UI", sans-serif; font-size: 10pt; }}
QFrame#panneau {{ background: {PANNEAU}; border: 1px solid #232838; border-radius: 10px; }}
QFrame#panneau QLabel, QFrame#panneau QCheckBox, QFrame#panneau QScrollArea,
QFrame#panneau QWidget#contenu {{ background: transparent; }}
QScrollArea {{ border: none; }}
QLabel#titre {{ font-size: 20pt; font-weight: bold; }}
QLabel#ligne1 {{ font-size: 12pt; }}
QLabel#infos, QLabel#libelle, QLabel#aide {{ color: {TEXTE_DOUX}; font-size: 9pt; }}
QLabel#entete {{ font-size: 14pt; font-weight: bold; }}
QLabel#section {{ color: {ACCENT}; font-size: 8.5pt; font-weight: bold; }}
QLineEdit, QComboBox {{ background: {CHAMP}; border: 1px solid {BORDURE}; border-radius: 4px; padding: 5px 7px;
             color: {TEXTE}; selection-background-color: {ACCENT}; selection-color: {FOND}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {CHAMP}; color: {TEXTE}; selection-background-color: {CHAMP_SURVOL};
             border: 1px solid {BORDURE}; }}
QPushButton {{ background: {CHAMP}; border: 1px solid {BORDURE}; border-radius: 4px; padding: 7px 10px; color: {TEXTE}; }}
QPushButton:hover {{ background: {CHAMP_SURVOL}; }}
QPushButton#principal {{ background: {ACCENT}; color: {FOND}; font-size: 12pt; font-weight: bold;
                         border: none; padding: 11px; }}
QPushButton#principal:hover {{ background: {ACCENT_SURVOL}; }}
QPushButton#segment {{ padding: 3px 12px; }}
QPushButton#segment:checked {{ background: {ACCENT}; color: {FOND}; font-weight: bold; border-color: {ACCENT}; }}
QPushButton#retour {{ background: transparent; border: 1px solid {BORDURE}; border-radius: 16px; padding: 5px 14px;
                      color: {TEXTE_DOUX}; }}
QPushButton#retour:hover {{ color: {TEXTE}; border-color: {ACCENT}; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDURE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TEXTE}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QMenuBar {{ background: {FOND}; color: {TEXTE_DOUX}; }}
QMenuBar::item:selected {{ background: {CHAMP}; color: {TEXTE}; }}
QMenu {{ background: {PANNEAU}; color: {TEXTE}; border: 1px solid {BORDURE}; }}
QMenu::item {{ padding: 6px 24px 6px 18px; }}
QMenu::item:selected {{ background: {CHAMP_SURVOL}; }}
QMenu::separator {{ height: 1px; background: {BORDURE}; margin: 4px 8px; }}
QStatusBar {{ background: {PANNEAU}; color: {TEXTE_DOUX}; }}
QStatusBar QLabel {{ color: {TEXTE_DOUX}; }}
QFrame#carte {{ background: {PANNEAU}; border: 1px solid #232838; border-radius: 14px; }}
QFrame#carte:hover {{ border: 1px solid {ACCENT}; }}
QFrame#carte QLabel {{ background: transparent; }}
QLabel#grand_titre {{ font-size: 28pt; font-weight: bold; }}
QLabel#accroche {{ color: {TEXTE_DOUX}; font-size: 12pt; }}
QLabel#carte_titre {{ font-size: 16pt; font-weight: bold; }}
QLabel#carte_texte {{ color: {TEXTE}; font-size: 10pt; }}
QLabel#carte_points {{ color: {TEXTE_DOUX}; font-size: 9.5pt; }}
QLabel#raccourci {{ color: {TEXTE_DOUX}; font-size: 9pt; }}
"""

# Images stockées ligne par ligne (une ligne par valeur de y), la ligne 0 en bas
pg.setConfigOptions(imageAxisOrder="row-major", antialias=False)


def qimage_depuis_rgb(rgb):
    """Tableau RGB uint8 (hauteur, largeur, 3) → QImage (copie indépendante du tableau)."""
    rgb = np.ascontiguousarray(rgb)
    h, w = rgb.shape[:2]
    return QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888).copy()


def sauver_png_rgb(rgb, chemin):
    """Enregistre une image RGB dont la ligne 0 est le bas (plus petit y)."""
    return qimage_depuis_rgb(rgb[::-1]).save(chemin)


class AxeReel(pg.AxisItem):
    """Axe gradué en coordonnées réelles.

    La vue travaille en coordonnées recentrées, (z - origine) / échelle, qui restent
    proches de [-0.5, 0.5] : Qt garde ainsi toute sa précision même en zoom très profond.
    Cet axe convertit les graduations dans un sens puis dans l'autre."""

    def __init__(self, orientation, vue, composante):
        super().__init__(orientation)
        self.vue = vue
        self.composante = composante   # 0 = partie réelle, 1 = partie imaginaire

    def _origine_echelle(self):
        return self.vue.origine[self.composante], self.vue.echelle

    def tickValues(self, minVal, maxVal, size):
        o, s = self._origine_echelle()
        niveaux = super().tickValues(o + minVal * s, o + maxVal * s, size)
        return [(pas / s, [(v - o) / s for v in valeurs]) for pas, valeurs in niveaux]

    def tickStrings(self, values, scale, spacing):
        o, s = self._origine_echelle()
        return [nc.etiquette_axe(o + v * s, spacing * s) for v in values]

    def rafraichir(self):
        self.picture = None   # force le recalcul des graduations
        self.update()


def etiquette(texte, nom):
    w = QtWidgets.QLabel(texte)
    w.setObjectName(nom)
    return w


class VueFractale(QtWidgets.QWidget):
    """Page de visualisation d'une fractale. Les sous-classes précisent :
    les champs propres (construire_debut_panneau / construire_fin_panneau, CHAMPS),
    la lecture des paramètres (lire_specifique, verifier), les options du moteur
    (arguments), la lecture du résultat (lire_resultat), les couleurs (image_rgb),
    les textes (entete, legende_html, texte_survol) et les valeurs par défaut."""

    NOM = ""
    FICHIER_BINAIRE = ""
    FICHIER_PARAMETRES = ""
    CHAMPS = nc.CHAMPS_FENETRE
    DEFAUTS = {}
    LIBELLE_POINT = "z"

    def __init__(self, principale, parametres, donnees, executable):
        super().__init__()
        self.principale = principale              # fenêtre principale : barre d'état, retour à l'accueil
        self.p = dict(parametres)                 # paramètres de l'image affichée
        self.donnees = None
        self.origine, self.echelle = (0.0, 0.0), 1.0
        self.rect_image = None
        self.premier_affichage = True

        # Calcul C++ en arrière-plan : une seule exécution à la fois, la dernière demande attend
        self.executable = executable
        self.prefixe_args = []                    # (utilisé par les tests)
        self.calcul_en_cours = None
        self.en_attente = None
        self.debut = 0.0
        self.processus = QtCore.QProcess(self)
        self.processus.setWorkingDirectory(nc.DOSSIER)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("PATH", nc.environnement_calcul()["PATH"])   # DLL OpenMP de MinGW
        self.processus.setProcessEnvironment(env)
        self.processus.finished.connect(self.calcul_termine)
        self.processus.errorOccurred.connect(self.erreur_processus)

        # Recalcul automatique quand on arrête de zoomer / déplacer
        self.minuteur_zoom = QtCore.QTimer(self)
        self.minuteur_zoom.setSingleShot(True)
        self.minuteur_zoom.setInterval(350)
        self.minuteur_zoom.timeout.connect(lambda: self.recalculer_vue(auto=True))

        self.construire_interface()
        # (un raccourci n'est actif que si sa page est visible)
        QtGui.QShortcut(QtGui.QKeySequence("H"), self, self.vue_initiale)

        if donnees is not None:
            self.afficher_resultat(donnees, self.p)
            self.statut("Résultat précédent chargé.")
        elif not self.executable:
            self.statut("Programme C++ introuvable : compile-le (make) ou passe --exe au script.", ERREUR)

    def showEvent(self, evenement):
        super().showEvent(evenement)
        if self.premier_affichage:
            self.premier_affichage = False
            if self.donnees is None and self.executable:
                QtCore.QTimer.singleShot(0, self.calculer)   # premier calcul à l'ouverture de la page

    # -- À préciser dans les sous-classes ------------------------------------------
    def construire_debut_panneau(self, v):
        pass

    def construire_fin_panneau(self, v):
        pass

    def lire_specifique(self):
        return {}

    def verifier(self, p):
        nc.verifier_fenetre(p)

    def arguments(self, p):
        raise NotImplementedError

    def lire_resultat(self):
        raise NotImplementedError

    def image_rgb(self, donnees):
        raise NotImplementedError

    def apres_resultat(self, p):
        pass

    def entete(self):
        return "", nc.sous_titre(self.p)

    def legende_html(self):
        return ""

    def texte_survol(self, valeur):
        return ""

    def avant_recalcul_vue(self, x0, x1, y0, y1):
        pass

    def valeurs_defaut_specifiques(self):
        pass

    def message_termine(self, p):
        return ""

    # -- Construction --------------------------------------------------------
    def construire_interface(self):
        disposition = QtWidgets.QHBoxLayout(self)
        disposition.setContentsMargins(20, 10, 14, 6)
        disposition.setSpacing(18)

        # Zone de gauche : retour à l'accueil, titre, image, légende
        gauche = QtWidgets.QVBoxLayout()
        gauche.setSpacing(4)
        barre = QtWidgets.QHBoxLayout()
        retour = QtWidgets.QPushButton("←  Accueil")
        retour.setObjectName("retour")
        retour.setToolTip("Revenir à la page d'accueil (Ctrl+0)")
        retour.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        retour.clicked.connect(self.principale.aller_accueil)
        barre.addWidget(retour)
        barre.addSpacing(10)
        barre.addWidget(etiquette(self.NOM, "titre"))
        barre.addStretch(1)
        gauche.addLayout(barre)
        self.label_ligne1 = etiquette("", "ligne1")
        self.label_infos = etiquette("", "infos")
        for w in (self.label_ligne1, self.label_infos):
            w.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            gauche.addWidget(w)

        self.axes = {"bottom": AxeReel("bottom", self, 0), "left": AxeReel("left", self, 1)}
        self.plot = pg.PlotWidget(axisItems=self.axes, background=FOND)
        self.plot.hideButtons()
        self.plot.setMenuEnabled(False)
        police_graduations = QtGui.QFont()
        police_graduations.setPointSize(9)
        for nom, texte in (("bottom", "Re"), ("left", "Im")):
            axe = self.plot.getAxis(nom)
            axe.enableAutoSIPrefix(False)   # nos graduations sont déjà converties (pas de « x0.001 »)
            axe.setPen(pg.mkPen(BORDURE))
            axe.setTextPen(pg.mkPen(TEXTE_DOUX))
            axe.setStyle(tickFont=police_graduations)
            self.plot.setLabel(nom, texte, color=TEXTE_DOUX)
        self.vb = self.plot.getViewBox()
        self.vb.setAspectLocked(True)
        # Image dessinée par un composant Qt de base : pg.ImageItem n'affiche rien avec
        # certaines combinaisons de versions (ex. pyqtgraph 0.13.7 + PySide6 6.9 de MSYS2).
        # Le lissage mélange les couleurs quand l'image est réduite (pas de crénelage).
        self.image = QtWidgets.QGraphicsPixmapItem()
        self.image.setTransformationMode(QtCore.Qt.TransformationMode.SmoothTransformation)
        self.vb.addItem(self.image, ignoreBounds=True)
        self.texte_vide = pg.TextItem("Calcul en cours…", color=TEXTE_DOUX, anchor=(0.5, 0.5))
        self.plot.addItem(self.texte_vide)
        self.vb.setRange(QtCore.QRectF(-1, -1, 2, 2), padding=0)
        self.vb.sigRangeChangedManually.connect(self.vue_changee_a_la_main)
        self.plot.scene().sigMouseMoved.connect(self.souris_bougee)
        gauche.addSpacing(4)
        gauche.addWidget(self.plot, 1)

        self.label_legende = QtWidgets.QLabel("")
        self.label_legende.setWordWrap(True)
        self.label_legende.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        gauche.addWidget(self.label_legende)
        disposition.addLayout(gauche, 1)
        disposition.addWidget(self.construire_panneau())

    def champ(self, cle, texte):
        w = QtWidgets.QLineEdit(texte)
        w.setCursorPosition(0)
        w.returnPressed.connect(self.calculer)
        self.champs[cle] = w
        return w

    def grille_champs(self, v, titre, paires, textes):
        """Section de champs, deux par ligne (libellé au-dessus du champ)."""
        noms = {cle: nom for cle, nom, _ in self.CHAMPS}
        v.addSpacing(10)
        if titre:
            v.addWidget(etiquette(titre, "section"))
        grille = QtWidgets.QGridLayout()
        grille.setHorizontalSpacing(12)
        grille.setVerticalSpacing(3)
        for n, paire in enumerate(paires):
            for col, cle in enumerate(paire):
                if cle is None:
                    continue
                grille.addWidget(etiquette(noms[cle], "libelle"), 2 * n, col)
                grille.addWidget(self.champ(cle, textes.get(cle, "")), 2 * n + 1, col)
        grille.setColumnStretch(0, 1)
        grille.setColumnStretch(1, 1)
        v.addLayout(grille)
        return grille

    def construire_panneau(self):
        panneau = QtWidgets.QFrame()
        panneau.setObjectName("panneau")
        panneau.setFixedWidth(410)
        externe = QtWidgets.QVBoxLayout(panneau)
        externe.setContentsMargins(2, 2, 2, 2)
        defilement = QtWidgets.QScrollArea()     # au cas où l'écran serait trop petit
        defilement.setWidgetResizable(True)
        defilement.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenu = QtWidgets.QWidget()
        contenu.setObjectName("contenu")
        v = QtWidgets.QVBoxLayout(contenu)
        v.setContentsMargins(18, 14, 18, 12)
        v.setSpacing(6)
        defilement.setWidget(contenu)
        externe.addWidget(defilement)

        v.addWidget(etiquette("Paramètres", "entete"))
        v.addSpacing(4)
        self.champs = {}
        textes = nc.textes_champs(self.p)
        self.construire_debut_panneau(v)
        self.grille_champs(v, "IMAGE", [("largeur", "hauteur")], textes)
        self.grille_champs(v, "FENÊTRE DU PLAN COMPLEXE", [("min_x", "max_x"), ("min_y", "max_y")], textes)
        self.construire_fin_panneau(v)

        v.addSpacing(12)
        self.case_auto = QtWidgets.QCheckBox("Recalcul automatique après zoom ou déplacement")
        self.case_auto.setChecked(True)
        v.addWidget(self.case_auto)
        bouton_vue = QtWidgets.QPushButton("Recalculer la vue affichée")
        bouton_vue.clicked.connect(lambda: self.recalculer_vue())
        v.addWidget(bouton_vue)
        ligne = QtWidgets.QHBoxLayout()
        for texte, action in (("Pixels carrés", self.pixels_carres), ("Par défaut", self.valeurs_defaut),
                              ("Export PNG", self.exporter)):
            b = QtWidgets.QPushButton(texte)
            b.clicked.connect(lambda _=False, a=action: a())
            ligne.addWidget(b)
        v.addLayout(ligne)
        v.addSpacing(6)
        self.bouton_calcul = QtWidgets.QPushButton("Calculer")
        self.bouton_calcul.setObjectName("principal")
        self.bouton_calcul.clicked.connect(self.calculer)
        v.addWidget(self.bouton_calcul)

        self.label_statut = QtWidgets.QLabel("")
        self.label_statut.setWordWrap(True)
        v.addWidget(self.label_statut)
        v.addStretch(1)
        v.addWidget(etiquette("Molette : zoom   ·   clic-glisser : déplacer\n"
                              "H : vue de l'image   ·   Entrée : calculer   ·   Ctrl+0 : accueil", "aide"))
        return panneau

    # -- Champs ----------------------------------------------------------------
    def statut(self, texte, couleur=TEXTE_DOUX):
        self.label_statut.setText(texte)
        self.label_statut.setStyleSheet(f"color: {couleur};")

    def remplir(self, valeurs):
        for cle, texte in nc.textes_champs(valeurs).items():
            if cle in self.champs:
                self.champs[cle].setText(texte)
                self.champs[cle].setCursorPosition(0)

    def textes_numeriques(self):
        return {cle: self.champs[cle].text() for cle, _, _ in self.CHAMPS}

    def lire_champs(self):
        """Lit et vérifie tous les champs ; lève ValueError avec un message clair."""
        p = nc.lire_nombres(self.textes_numeriques(), self.CHAMPS)
        p.update(self.lire_specifique())
        self.verifier(p)
        return p

    def pixels_carres(self, silencieux=False):
        """Ajuste la hauteur pour que les pixels soient carrés (image non déformée)."""
        try:
            p = nc.lire_nombres(self.textes_numeriques(), self.CHAMPS)
            if p["max_x"] <= p["min_x"]:
                raise ValueError("Il faut Re min < Re max")
        except ValueError as e:
            self.statut(str(e), ERREUR)
            return
        hauteur = max(1, min(20000, round(p["largeur"] * (p["max_y"] - p["min_y"]) / (p["max_x"] - p["min_x"]))))
        self.champs["hauteur"].setText(str(hauteur))
        if not silencieux:
            self.statut(f"Hauteur ajustée à {hauteur} px.")

    def valeurs_defaut(self):
        self.remplir(self.DEFAUTS)
        self.valeurs_defaut_specifiques()
        self.statut("Valeurs par défaut remises : appuie sur Entrée ou clique sur Calculer.")

    # -- Calcul ----------------------------------------------------------------
    def calculer(self):
        if not self.executable:
            self.statut("Programme C++ introuvable : compile-le (make) ou passe --exe au script.", ERREUR)
            return
        try:
            p = self.lire_champs()
        except ValueError as e:
            self.statut(str(e), ERREUR)
            return
        self.lancer(p)

    def lancer(self, p):
        if self.processus.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.en_attente = p   # sera lancé dès la fin du calcul en cours (la dernière demande gagne)
            return
        self.calcul_en_cours = p
        self.debut = time.perf_counter()
        self.statut("Calcul en cours…", ACCENT)
        self.processus.start(self.executable, self.prefixe_args + self.arguments(p))

    def calcul_termine(self, code, etat):
        p, self.calcul_en_cours = self.calcul_en_cours, None
        if etat != QtCore.QProcess.ExitStatus.NormalExit or code != 0:
            sortie = bytes(self.processus.readAllStandardError()).decode(errors="replace").strip()
            premiere = sortie.splitlines()[0] if sortie else f"code {code}"
            self.statut(f"Erreur du programme C++ :\n{premiere}", ERREUR)
        else:
            try:
                donnees = self.lire_resultat()
            except (OSError, ValueError) as e:
                self.statut(f"Lecture du résultat impossible :\n{e}", ERREUR)
            else:
                self.afficher_resultat(donnees, p)
                nc.sauvegarder_parametres(self.p, self.FICHIER_BINAIRE, self.FICHIER_PARAMETRES)
                duree = time.perf_counter() - self.debut
                suite = self.message_termine(p)
                self.statut(f"Terminé en {duree:.2f} s" + (f"   ·   {suite}" if suite else ""), SUCCES)
        if self.en_attente is not None:
            suivant, self.en_attente = self.en_attente, None
            self.lancer(suivant)

    def erreur_processus(self, erreur):
        # (si le programme démarre puis échoue, c'est calcul_termine qui s'en occupe)
        if erreur == QtCore.QProcess.ProcessError.FailedToStart:
            self.calcul_en_cours = self.en_attente = None
            self.statut(f"Impossible de lancer le programme C++ :\n{self.processus.errorString()}", ERREUR)

    def vue_changee_a_la_main(self, *_):
        if self.case_auto.isChecked() and self.donnees is not None:
            self.minuteur_zoom.start()   # redémarre le délai : on attend la fin du geste

    def bornes_vue(self):
        """Zone actuellement visible, en coordonnées réelles."""
        (u0, u1), (v0, v1) = self.vb.viewRange()
        (cx, cy), s = self.origine, self.echelle
        return cx + u0 * s, cx + u1 * s, cy + v0 * s, cy + v1 * s

    def aller_a(self, cx, cy, largeur):
        """Calcule la zone centrée en (cx, cy), de la largeur donnée, aux proportions de la vue."""
        (u0, u1), (v0, v1) = self.vb.viewRange()
        rapport = (v1 - v0) / (u1 - u0) if u1 > u0 else 1.0
        x0, x1 = cx - largeur / 2, cx + largeur / 2
        y0, y1 = cy - largeur * rapport / 2, cy + largeur * rapport / 2
        self.remplir({"min_x": x0, "max_x": x1, "min_y": y0, "max_y": y1})
        self.avant_recalcul_vue(x0, x1, y0, y1)
        self.pixels_carres(silencieux=True)
        self.calculer()

    def recalculer_vue(self, auto=False):
        """Recalcule en pleine résolution la zone affichée (après un zoom ou un déplacement)."""
        if self.donnees is None:
            self.statut("Lance d'abord un calcul.")
            return
        x0, x1, y0, y1 = self.bornes_vue()
        if nc.ecart_trop_petit(x0, x1) or nc.ecart_trop_petit(y0, y1):
            self.statut("Zoom maximal atteint : au-delà, la précision des nombres (double) "
                        "ne permet plus de distinguer les pixels.", ERREUR)
            return
        self.remplir({"min_x": x0, "max_x": x1, "min_y": y0, "max_y": y1})
        self.avant_recalcul_vue(x0, x1, y0, y1)
        self.pixels_carres(silencieux=True)
        self.calculer()

    # -- Affichage -------------------------------------------------------------
    def afficher_resultat(self, donnees, p):
        self.donnees = donnees
        self.p = {k: v for k, v in p.items() if k not in ("coefs", "racines")}
        self.p["hauteur"], self.p["largeur"] = donnees.shape[:2]
        self.apres_resultat(p)

        # Nouveau repère centré sur l'image calculée
        x0, x1, y0, y1 = p["min_x"], p["max_x"], p["min_y"], p["max_y"]
        self.origine = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.echelle = max(x1 - x0, y1 - y0)
        (cx, cy), s = self.origine, self.echelle
        self.rect_image = QtCore.QRectF((x0 - cx) / s, (y0 - cy) / s, (x1 - x0) / s, (y1 - y0) / s)

        self.rafraichir_image()
        self.texte_vide.hide()
        limite = 4 * nc.ECART_RELATIF_MIN * max(abs(cx), abs(cy), 1e-300) / s
        self.vb.setLimits(minXRange=limite, minYRange=limite)
        self.vb.setRange(self.rect_image, padding=0)
        for axe in self.axes.values():
            axe.rafraichir()
        self.rafraichir_textes()

    def rafraichir_image(self):
        """(Re)dessine l'image à partir des données, par exemple après un changement de couleurs."""
        if self.donnees is None:
            return
        rgb = self.image_rgb(self.donnees)   # ligne 0 = plus petit y : en bas dans la vue (y vers le haut)
        h, w = rgb.shape[:2]
        self.image.setPixmap(QtGui.QPixmap.fromImage(qimage_depuis_rgb(rgb)))
        self.image.setPos(self.rect_image.x(), self.rect_image.y())
        self.image.setTransform(QtGui.QTransform.fromScale(self.rect_image.width() / w,
                                                           self.rect_image.height() / h))

    def rafraichir_textes(self):
        ligne1, ligne2 = self.entete()
        self.label_ligne1.setText(ligne1)
        self.label_infos.setText(ligne2)
        self.label_legende.setText(self.legende_html())

    def vue_initiale(self):
        if self.rect_image is not None:
            self.vb.setRange(self.rect_image, padding=0)

    def souris_bougee(self, pos):
        """Barre d'état : point sous la souris et valeur calculée en ce point."""
        if not self.isVisible() or not self.vb.sceneBoundingRect().contains(pos):
            return
        point = self.vb.mapSceneToView(pos)
        (cx, cy), s = self.origine, self.echelle
        x, y = cx + point.x() * s, cy + point.y() * s
        (u0, u1), (v0, v1) = self.vb.viewRange()
        ex = (u1 - u0) * s / max(self.vb.width(), 1)
        ey = (v1 - v0) * s / max(self.vb.height(), 1)
        texte = f"{self.LIBELLE_POINT} = {nc.coordonnee(x, ex)} {'+' if y >= 0 else '-'} {nc.coordonnee(abs(y), ey)}i"
        if self.donnees is not None:
            p = self.p
            hauteur, largeur = self.donnees.shape[:2]
            i = int(np.floor((x - p["min_x"]) / (p["max_x"] - p["min_x"]) * largeur))
            j = int(np.floor((y - p["min_y"]) / (p["max_y"] - p["min_y"]) * hauteur))
            if 0 <= i < largeur and 0 <= j < hauteur:
                texte += "     →  " + self.texte_survol(self.donnees[j, i])
        self.principale.statusBar().showMessage(texte)

    def exporter(self):
        if self.donnees is None:
            self.statut("Rien à enregistrer pour l'instant.")
            return
        defaut = os.path.join(nc.DOSSIER, time.strftime("fractale_%Y%m%d_%H%M%S.png"))
        chemin, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Enregistrer l'image", defaut, "Images PNG (*.png)")
        if not chemin:
            return
        if sauver_png_rgb(self.image_rgb(self.donnees), chemin):
            self.statut(f"Image enregistrée : {os.path.basename(chemin)}", SUCCES)
        else:
            self.statut(f"Enregistrement impossible : {chemin}", ERREUR)
