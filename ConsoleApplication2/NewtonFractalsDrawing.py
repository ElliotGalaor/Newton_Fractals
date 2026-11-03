"""Interface Qt de la fractale de Newton.

Un panneau à droite permet de choisir les paramètres (polynôme ou racines, pixels,
zone du plan complexe, précision, itérations). Le calcul C++ tourne en arrière-plan
et l'image se met à jour dans la même fenêtre ; après un zoom ou un déplacement,
la vue est recalculée automatiquement en pleine résolution.

Utilisation :
    python NewtonFractalsDrawing.py
    python NewtonFractalsDrawing.py --bornes -0.3 0.3 -0.3 0.3       (affiche results.txt)
    python NewtonFractalsDrawing.py --enregistrer fractale.png        (image seule, sans fenêtre)
    python NewtonFractalsDrawing.py --exe chemin\\vers\\programme.exe

Dans la fenêtre :
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
import time

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
    import pyqtgraph as pg
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError as erreur_qt:
    _relancer_avec_un_autre_python()
    sys.exit(f"Impossible de charger Qt avec ce Python ({sys.executable}) :\n  {erreur_qt}\n\n"
             "Installe PySide6 et pyqtgraph dans ton Python Windows (leurs DLL sont signées) :\n"
             '  & "$env:LOCALAPPDATA\\Python\\bin\\python.exe" -m pip install pyside6 pyqtgraph\n'
             "puis relance : python NewtonFractalsDrawing.py")

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
QFrame#panneau QLabel, QFrame#panneau QCheckBox {{ background: transparent; }}
QLabel#titre {{ font-size: 20pt; font-weight: bold; }}
QLabel#polynome {{ font-size: 12pt; }}
QLabel#infos, QLabel#libelle, QLabel#aide {{ color: {TEXTE_DOUX}; font-size: 9pt; }}
QLabel#entete {{ font-size: 14pt; font-weight: bold; }}
QLabel#section {{ color: {ACCENT}; font-size: 8.5pt; font-weight: bold; }}
QLineEdit {{ background: {CHAMP}; border: 1px solid {BORDURE}; border-radius: 4px; padding: 5px 7px;
             color: {TEXTE}; selection-background-color: {ACCENT}; selection-color: {FOND}; }}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{ background: {CHAMP}; border: 1px solid {BORDURE}; border-radius: 4px; padding: 7px 10px; color: {TEXTE}; }}
QPushButton:hover {{ background: {CHAMP_SURVOL}; }}
QPushButton#principal {{ background: {ACCENT}; color: {FOND}; font-size: 12pt; font-weight: bold;
                         border: none; padding: 11px; }}
QPushButton#principal:hover {{ background: {ACCENT_SURVOL}; }}
QPushButton#segment {{ padding: 3px 12px; }}
QPushButton#segment:checked {{ background: {ACCENT}; color: {FOND}; font-weight: bold; border-color: {ACCENT}; }}
QStatusBar {{ background: {PANNEAU}; color: {TEXTE_DOUX}; }}
QStatusBar QLabel {{ color: {TEXTE_DOUX}; }}
"""

# Image stockée ligne par ligne (une ligne par valeur de y), la ligne 0 en bas
pg.setConfigOptions(imageAxisOrder="row-major", antialias=False)


def sauver_png(indices, chemin):
    """Enregistre la fractale à sa résolution de calcul (un pixel calculé = un pixel de l'image)."""
    rgb = np.ascontiguousarray(nc.image_rgb(indices))
    h, w = rgb.shape[:2]
    image = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888)
    return image.save(chemin)


class AxeReel(pg.AxisItem):
    """Axe gradué en coordonnées réelles.

    La vue travaille en coordonnées recentrées, (z - origine) / échelle, qui restent
    proches de [-0.5, 0.5] : Qt garde ainsi toute sa précision même en zoom très profond.
    Cet axe convertit les graduations dans un sens puis dans l'autre."""

    def __init__(self, orientation, fenetre, composante):
        super().__init__(orientation)
        self.fenetre = fenetre
        self.composante = composante   # 0 = partie réelle, 1 = partie imaginaire

    def _origine_echelle(self):
        return self.fenetre.origine[self.composante], self.fenetre.echelle

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


class Fenetre(QtWidgets.QMainWindow):
    def __init__(self, parametres, indices, executable):
        super().__init__()
        self.setWindowTitle("Fractale de Newton")
        self.p = dict(parametres)                 # paramètres de l'image affichée
        self.indices = None
        self.racines = nc.racines_de(self.p)
        self.mode = self.p.get("mode", "polynome")   # contenu du champ polynôme : p(z) ou racines
        self.num_exemple = {"polynome": 0, "racines": -1}
        self.table = nc.table_couleurs()
        self.origine, self.echelle = (0.0, 0.0), 1.0
        self.rect_image = None

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
        QtGui.QShortcut(QtGui.QKeySequence("H"), self, self.vue_initiale)

        if indices is not None:
            self.afficher_resultat(indices, self.p)
            self.statut("Résultat précédent chargé.")
        elif self.executable:
            QtCore.QTimer.singleShot(0, self.calculer)
        else:
            self.statut("Programme C++ introuvable : compile-le (make) ou passe --exe au script.", ERREUR)

    # -- Construction --------------------------------------------------------
    def construire_interface(self):
        central = QtWidgets.QWidget()
        disposition = QtWidgets.QHBoxLayout(central)
        disposition.setContentsMargins(20, 14, 14, 10)
        disposition.setSpacing(18)

        # Zone de gauche : titre, image, légende
        gauche = QtWidgets.QVBoxLayout()
        gauche.setSpacing(4)
        titre = QtWidgets.QLabel("Fractale de Newton")
        titre.setObjectName("titre")
        self.label_polynome = QtWidgets.QLabel("")
        self.label_polynome.setObjectName("polynome")
        self.label_infos = QtWidgets.QLabel("")
        self.label_infos.setObjectName("infos")
        for w in (titre, self.label_polynome, self.label_infos):
            w.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            gauche.addWidget(w)

        self.axes = {"bottom": AxeReel("bottom", self, 0), "left": AxeReel("left", self, 1)}
        self.plot = pg.PlotWidget(axisItems=self.axes, background=FOND)
        self.plot.hideButtons()
        self.plot.setMenuEnabled(False)
        police_graduations = QtGui.QFont()
        police_graduations.setPointSize(9)
        for nom, texte in (("bottom", "Re(z)"), ("left", "Im(z)")):
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
        self.texte_vide = pg.TextItem("Choisis les paramètres à droite\npuis clique sur « Calculer »",
                                      color=TEXTE_DOUX, anchor=(0.5, 0.5))
        self.plot.addItem(self.texte_vide)
        self.vb.setRange(QtCore.QRectF(-1, -1, 2, 2), padding=0)
        self.vb.sigRangeChangedManually.connect(self.vue_changee_a_la_main)
        self.plot.scene().sigMouseMoved.connect(self.souris_bougee)
        gauche.addSpacing(6)
        gauche.addWidget(self.plot, 1)

        self.label_legende = QtWidgets.QLabel("")
        self.label_legende.setWordWrap(True)
        self.label_legende.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        gauche.addWidget(self.label_legende)
        disposition.addLayout(gauche, 1)

        disposition.addWidget(self.construire_panneau())
        self.setCentralWidget(central)
        self.statusBar().showMessage("Survole l'image pour voir les coordonnées et la racine atteinte.")

    def construire_panneau(self):
        panneau = QtWidgets.QFrame()
        panneau.setObjectName("panneau")
        panneau.setFixedWidth(400)
        v = QtWidgets.QVBoxLayout(panneau)
        v.setContentsMargins(20, 16, 20, 14)
        v.setSpacing(6)

        def etiquette(texte, nom):
            w = QtWidgets.QLabel(texte)
            w.setObjectName(nom)
            return w

        entete = etiquette("Paramètres", "entete")
        v.addWidget(entete)
        v.addSpacing(6)

        self.champs = {}
        textes = nc.textes_champs(self.p)

        def champ(cle):
            w = QtWidgets.QLineEdit(textes.get(cle, ""))
            w.setCursorPosition(0)
            w.returnPressed.connect(self.calculer)
            self.champs[cle] = w
            return w

        # Polynôme : sélecteur p(z) / racines, champ, exemples
        ligne = QtWidgets.QHBoxLayout()
        ligne.addWidget(etiquette("POLYNÔME", "section"))
        ligne.addStretch(1)
        self.boutons_mode = {}
        groupe = QtWidgets.QButtonGroup(self)
        groupe.setExclusive(True)
        for mode, texte in (("polynome", "p(z)"), ("racines", "Racines")):
            b = QtWidgets.QPushButton(texte)
            b.setObjectName("segment")
            b.setCheckable(True)
            b.setChecked(mode == self.mode)
            b.clicked.connect(lambda _=False, m=mode: self.changer_mode(m))
            groupe.addButton(b)
            ligne.addWidget(b)
            self.boutons_mode[mode] = b
        v.addLayout(ligne)
        self.label_aide_polynome = etiquette(nc.LIBELLES_MODE[self.mode], "libelle")
        v.addWidget(self.label_aide_polynome)
        ligne = QtWidgets.QHBoxLayout()
        ligne.addWidget(champ("polynome"), 1)
        bouton_exemple = QtWidgets.QPushButton("Exemple ▸")
        bouton_exemple.clicked.connect(self.exemple_suivant)
        ligne.addWidget(bouton_exemple)
        v.addLayout(ligne)

        # Champs numériques, deux par ligne
        noms = {cle: nom for cle, nom, _ in nc.CHAMPS}
        for titre, paires in (("IMAGE", [("largeur", "hauteur")]),
                              ("FENÊTRE DU PLAN COMPLEXE", [("min_x", "max_x"), ("min_y", "max_y")]),
                              ("CONVERGENCE", [("eps", "iterations")])):
            v.addSpacing(10)
            v.addWidget(etiquette(titre, "section"))
            grille = QtWidgets.QGridLayout()
            grille.setHorizontalSpacing(12)
            grille.setVerticalSpacing(3)
            for n, (a, b) in enumerate(paires):
                for col, cle in enumerate((a, b)):
                    grille.addWidget(etiquette(noms[cle], "libelle"), 2 * n, col)
                    grille.addWidget(champ(cle), 2 * n + 1, col)
            v.addLayout(grille)

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
                              "H : vue de l'image   ·   Entrée : calculer", "aide"))
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

    def lire_champs(self):
        """Lit et vérifie tous les champs ; lève ValueError avec un message clair."""
        p = nc.lire_saisie_polynome(self.champs["polynome"].text(), self.mode)
        p.update(nc.lire_nombres({cle: self.champs[cle].text() for cle, _, _ in nc.CHAMPS}))
        nc.verifier_parametres(p)
        return p

    def changer_mode(self, mode, texte=None):
        """Passe le champ en saisie de p(z) ou de racines, en convertissant ce qui est écrit."""
        if mode == self.mode and texte is None:
            return
        if texte is None:
            try:
                saisi = nc.lire_saisie_polynome(self.champs["polynome"].text(), self.mode)
                texte = saisi["racines_texte"] if mode == "racines" else saisi["polynome"]
            except ValueError as e:
                if self.champs["polynome"].text().strip():
                    self.boutons_mode[self.mode].setChecked(True)   # on reste dans le mode actuel
                    self.statut(f"{e}\n(corrige le champ avant de changer de mode)", ERREUR)
                    return
                texte = ""
        self.mode = mode
        self.boutons_mode[mode].setChecked(True)
        self.label_aide_polynome.setText(nc.LIBELLES_MODE[mode])
        self.champs["polynome"].setText(texte)
        self.champs["polynome"].setCursorPosition(0)
        self.statut("Saisie des racines : p(z) = produit des (z - racine)." if mode == "racines"
                    else "Saisie du polynôme p(z).")

    def exemple_suivant(self):
        liste = nc.EXEMPLES[self.mode]
        n = (self.num_exemple[self.mode] + 1) % len(liste)
        if liste[n] == self.champs["polynome"].text().strip():
            n = (n + 1) % len(liste)
        self.num_exemple[self.mode] = n
        self.champs["polynome"].setText(liste[n])
        self.statut("Exemple choisi : appuie sur Entrée ou clique sur Calculer.")

    def pixels_carres(self, silencieux=False):
        """Ajuste la hauteur pour que les pixels soient carrés (image non déformée)."""
        try:
            p = nc.lire_nombres({cle: self.champs[cle].text() for cle, _, _ in nc.CHAMPS})
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
        self.remplir({k: v for k, v in nc.DEFAUTS.items() if k not in ("mode", "polynome", "racines_texte")})
        self.changer_mode("polynome", texte=nc.DEFAUTS["polynome"])
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
        self.processus.start(self.executable, self.prefixe_args + nc.arguments_calcul(p, nc.FICHIER_BINAIRE))

    def calcul_termine(self, code, etat):
        p, self.calcul_en_cours = self.calcul_en_cours, None
        if etat != QtCore.QProcess.ExitStatus.NormalExit or code != 0:
            sortie = bytes(self.processus.readAllStandardError()).decode(errors="replace").strip()
            premiere = sortie.splitlines()[0] if sortie else f"code {code}"
            self.statut(f"Erreur du programme C++ :\n{premiere}", ERREUR)
        else:
            try:
                indices = nc.lire_binaire(nc.FICHIER_BINAIRE)
            except (OSError, ValueError) as e:
                self.statut(f"Lecture du résultat impossible :\n{e}", ERREUR)
            else:
                self.afficher_resultat(indices, p)
                nc.sauvegarder_parametres(p, nc.FICHIER_BINAIRE)
                duree = time.perf_counter() - self.debut
                self.statut(f"Terminé en {duree:.2f} s   ·   {len(p['racines'])} racine(s)", SUCCES)
        if self.en_attente is not None:
            suivant, self.en_attente = self.en_attente, None
            self.lancer(suivant)

    def erreur_processus(self, erreur):
        # (si le programme démarre puis échoue, c'est calcul_termine qui s'en occupe)
        if erreur == QtCore.QProcess.ProcessError.FailedToStart:
            self.calcul_en_cours = self.en_attente = None
            self.statut(f"Impossible de lancer le programme C++ :\n{self.processus.errorString()}", ERREUR)

    def vue_changee_a_la_main(self, *_):
        if self.case_auto.isChecked() and self.indices is not None:
            self.minuteur_zoom.start()   # redémarre le délai : on attend la fin du geste

    def bornes_vue(self):
        """Zone actuellement visible, en coordonnées réelles."""
        (u0, u1), (v0, v1) = self.vb.viewRange()
        (cx, cy), s = self.origine, self.echelle
        return cx + u0 * s, cx + u1 * s, cy + v0 * s, cy + v1 * s

    def recalculer_vue(self, auto=False):
        """Recalcule en pleine résolution la zone affichée (après un zoom ou un déplacement)."""
        if self.indices is None:
            self.statut("Lance d'abord un calcul.")
            return
        x0, x1, y0, y1 = self.bornes_vue()
        if nc.ecart_trop_petit(x0, x1) or nc.ecart_trop_petit(y0, y1):
            self.statut("Zoom maximal atteint : au-delà, la précision des nombres (double) "
                        "ne permet plus de distinguer les pixels.", ERREUR)
            return
        self.remplir({"min_x": x0, "max_x": x1, "min_y": y0, "max_y": y1})
        self.pixels_carres(silencieux=True)
        self.calculer()

    # -- Affichage -------------------------------------------------------------
    def afficher_resultat(self, indices, p):
        self.indices = indices
        self.p = {k: v for k, v in p.items() if k not in ("coefs", "racines")}
        self.p["hauteur"], self.p["largeur"] = indices.shape
        self.racines = p["racines"] if "racines" in p else nc.racines_de(self.p)

        # Nouveau repère centré sur l'image calculée
        x0, x1, y0, y1 = p["min_x"], p["max_x"], p["min_y"], p["max_y"]
        self.origine = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.echelle = max(x1 - x0, y1 - y0)
        (cx, cy), s = self.origine, self.echelle
        self.rect_image = QtCore.QRectF((x0 - cx) / s, (y0 - cy) / s, (x1 - x0) / s, (y1 - y0) / s)

        # Ligne 0 de l'image = plus petit y : dans la vue (y vers le haut) elle se retrouve en bas
        rgb = np.ascontiguousarray(self.table[np.clip(indices, 0, 255)])
        h, w = rgb.shape[:2]
        image = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888)
        self.image.setPixmap(QtGui.QPixmap.fromImage(image))   # (copie : rgb peut disparaître)
        self.image.setPos(self.rect_image.x(), self.rect_image.y())
        self.image.setTransform(QtGui.QTransform.fromScale(self.rect_image.width() / w,
                                                           self.rect_image.height() / h))
        self.texte_vide.hide()
        limite = 4 * nc.ECART_RELATIF_MIN * max(abs(cx), abs(cy), 1e-300) / s
        self.vb.setLimits(minXRange=limite, minYRange=limite)
        self.vb.setRange(self.rect_image, padding=0)
        for axe in self.axes.values():
            axe.rafraichir()

        self.label_polynome.setText(nc.titre_polynome(self.p, 110))
        self.label_infos.setText(nc.sous_titre(self.p))
        self.label_legende.setText(self.legende_html())

    def legende_html(self):
        total = self.indices.size
        nb = len(self.racines) if self.racines else max(int(self.indices.max()), 1)
        morceaux = []
        for k in range(1, nb + 1):
            couleur = nc.COULEURS_RACINES[(k - 1) % len(nc.COULEURS_RACINES)]
            nom = nc.texte_complexe(self.racines[k - 1]) if self.racines else f"Racine {k}"
            part = 100 * np.count_nonzero(self.indices == k) / total
            morceaux.append(f'<span style="color:{couleur}; font-size:15pt">■</span>&nbsp;{nom}'
                            f'&nbsp;<span style="color:{TEXTE_DOUX}">({part:.1f}&nbsp;%)</span>')
        non_conv = np.count_nonzero(self.indices < 1)
        if non_conv:
            morceaux.append(f'<span style="color:{nc.COULEUR_NON_CONVERGENCE}; font-size:15pt">■</span>'
                            f'&nbsp;Pas de convergence&nbsp;<span style="color:{TEXTE_DOUX}">'
                            f'({100 * non_conv / total:.1f}&nbsp;%)</span>')
        return "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(morceaux)

    def vue_initiale(self):
        if self.rect_image is not None:
            self.vb.setRange(self.rect_image, padding=0)

    def souris_bougee(self, pos):
        """Barre d'état : point sous la souris et racine vers laquelle il converge."""
        if not self.vb.sceneBoundingRect().contains(pos):
            return
        point = self.vb.mapSceneToView(pos)
        (cx, cy), s = self.origine, self.echelle
        x, y = cx + point.x() * s, cy + point.y() * s
        (u0, u1), (v0, v1) = self.vb.viewRange()
        ex = (u1 - u0) * s / max(self.vb.width(), 1)
        ey = (v1 - v0) * s / max(self.vb.height(), 1)
        texte = f"z = {nc.coordonnee(x, ex)} {'+' if y >= 0 else '-'} {nc.coordonnee(abs(y), ey)}i"
        if self.indices is not None:
            p = self.p
            hauteur, largeur = self.indices.shape
            i = int(np.floor((x - p["min_x"]) / (p["max_x"] - p["min_x"]) * largeur))
            j = int(np.floor((y - p["min_y"]) / (p["max_y"] - p["min_y"]) * hauteur))
            if 0 <= i < largeur and 0 <= j < hauteur:
                k = int(self.indices[j, i])
                if k < 1:
                    texte += "     →  pas de convergence"
                elif self.racines and k <= len(self.racines):
                    texte += f"     →  racine {k} = {nc.texte_complexe(self.racines[k - 1], 6)}"
                else:
                    texte += f"     →  racine {k}"
        self.statusBar().showMessage(texte)

    def exporter(self):
        if self.indices is None:
            self.statut("Rien à enregistrer pour l'instant.")
            return
        defaut = os.path.join(nc.DOSSIER, time.strftime("fractale_%Y%m%d_%H%M%S.png"))
        chemin, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Enregistrer l'image", defaut, "Images PNG (*.png)")
        if not chemin:
            return
        if sauver_png(self.indices, chemin):
            self.statut(f"Image enregistrée : {os.path.basename(chemin)}", SUCCES)
        else:
            self.statut(f"Enregistrement impossible : {chemin}", ERREUR)


# --- Lancement ----------------------------------------------------------------
def lire_arguments():
    p = argparse.ArgumentParser(description="Interface de la fractale de Newton")
    p.add_argument("--fichier", default=nc.FICHIER_RESULTATS, help="résultat à afficher (results.txt ou .bin)")
    p.add_argument("--bornes", nargs=4, type=float, metavar=("MIN_X", "MAX_X", "MIN_Y", "MAX_Y"),
                   help="zone du plan complexe de --fichier (sinon : dernier calcul de l'interface)")
    p.add_argument("--eps", type=float, help="précision utilisée pour --fichier")
    p.add_argument("--iterations", type=int, help="nombre d'itérations utilisé pour --fichier")
    p.add_argument("--polynome", help="polynôme utilisé pour --fichier, ex. \"z^3 - 2z + 2\"")
    p.add_argument("--exe", help="chemin du programme C++ compilé (sinon recherche automatique)")
    p.add_argument("--enregistrer", metavar="IMAGE.png",
                   help="enregistre l'image du résultat dans ce fichier, sans ouvrir la fenêtre")
    return p.parse_args()


def main():
    args = lire_arguments()
    app = QtWidgets.QApplication(sys.argv)
    p, indices = nc.preparer(args)

    if args.enregistrer:
        if indices is None:
            indices = nc.lire_fichier_resultat(args.fichier)
        if not sauver_png(indices, args.enregistrer):
            sys.exit(f"Enregistrement impossible : {args.enregistrer}")
        print(f"Image enregistree : {args.enregistrer}")
        return

    app.setStyleSheet(STYLE)
    fenetre = Fenetre(p, indices, nc.trouver_executable(args.exe))
    fenetre.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
