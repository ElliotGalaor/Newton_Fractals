"""Page « Ensemble de Mandelbrot »."""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

import mandelbrot_calcul as mc
import newton_calcul as nc
from interface_commune import TEXTE_DOUX, VueFractale, etiquette, qimage_depuis_rgb


class VueMandelbrot(VueFractale):
    NOM = "Ensemble de Mandelbrot"
    FICHIER_BINAIRE = mc.FICHIER_BINAIRE
    FICHIER_PARAMETRES = mc.FICHIER_PARAMETRES
    CHAMPS = mc.CHAMPS
    DEFAUTS = mc.DEFAUTS
    LIBELLE_POINT = "c"

    # -- Panneau -------------------------------------------------------------
    def construire_debut_panneau(self, v):
        v.addWidget(etiquette("LIEUX CÉLÈBRES", "section"))
        self.choix_lieu = QtWidgets.QComboBox()
        self.choix_lieu.addItem("Choisir un lieu à visiter…")
        for nom, *_ in mc.LIEUX:
            self.choix_lieu.addItem(nom)
        self.choix_lieu.activated.connect(self.visiter_lieu)
        v.addWidget(self.choix_lieu)

    def construire_fin_panneau(self, v):
        textes = nc.textes_champs(self.p)
        grille = self.grille_champs(v, "ITÉRATIONS", [("iterations", None)], textes)
        self.case_iterations = QtWidgets.QCheckBox("Adapter au zoom")
        self.case_iterations.setToolTip("Plus on zoome, plus il faut d'itérations pour voir les détails du bord")
        self.case_iterations.setChecked(bool(self.p.get("iterations_auto", True)))
        grille.addWidget(self.case_iterations, 1, 1)

        v.addSpacing(10)
        v.addWidget(etiquette("COULEURS  (changement immédiat, sans recalcul)", "section"))
        self.choix_palette = QtWidgets.QComboBox()
        self.choix_palette.setIconSize(QtCore.QSize(72, 12))
        for nom in mc.NOMS_PALETTES:
            icone = QtGui.QPixmap.fromImage(qimage_depuis_rgb(mc.apercu_palette(nom, 72, 12)))
            self.choix_palette.addItem(QtGui.QIcon(icone), nom)
        self.choix_palette.setCurrentText(self.p.get("palette", "Océan"))
        self.choix_palette.currentTextChanged.connect(self.couleurs_changees)
        v.addWidget(self.choix_palette)

        self.curseurs = {}
        for cle, libelle, mini, maxi, defaut in (("densite", "Densité des couleurs", 5, 400, 1.0),
                                                 ("decalage", "Décalage des couleurs", 0, 100, 0.0)):
            ligne = QtWidgets.QHBoxLayout()
            ligne.addWidget(etiquette(libelle, "libelle"))
            curseur = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            curseur.setRange(mini, maxi)
            curseur.setValue(int(round(float(self.p.get(cle, defaut)) * 100)))
            curseur.valueChanged.connect(self.couleurs_changees)
            ligne.addWidget(curseur, 1)
            v.addLayout(ligne)
            self.curseurs[cle] = curseur

    def couleurs_actuelles(self):
        return {"palette": self.choix_palette.currentText(),
                "densite": self.curseurs["densite"].value() / 100,
                "decalage": self.curseurs["decalage"].value() / 100}

    def couleurs_changees(self, *_):
        self.p.update(self.couleurs_actuelles())
        self.rafraichir_image()
        if self.donnees is not None:
            self.rafraichir_textes()
            nc.sauvegarder_parametres(self.p, self.FICHIER_BINAIRE, self.FICHIER_PARAMETRES)

    def visiter_lieu(self, index):
        if index <= 0:
            return
        nom, cx, cy, largeur = mc.LIEUX[index - 1]
        self.choix_lieu.setCurrentIndex(0)
        self.statut(f"Direction : {nom}…")
        self.aller_a(cx, cy, largeur)

    def avant_recalcul_vue(self, x0, x1, y0, y1):
        if self.case_iterations.isChecked():
            self.champs["iterations"].setText(str(mc.iterations_pour_zoom(x1 - x0)))

    def valeurs_defaut_specifiques(self):
        self.case_iterations.setChecked(True)
        self.choix_palette.setCurrentText(mc.DEFAUTS["palette"])
        self.curseurs["densite"].setValue(int(mc.DEFAUTS["densite"] * 100))
        self.curseurs["decalage"].setValue(int(mc.DEFAUTS["decalage"] * 100))

    # -- Calcul ------------------------------------------------------------------
    def lire_specifique(self):
        p = self.couleurs_actuelles()
        p["iterations_auto"] = self.case_iterations.isChecked()
        return p

    def verifier(self, p):
        mc.verifier_parametres(p)

    def arguments(self, p):
        return mc.arguments_calcul(p, self.FICHIER_BINAIRE)

    def lire_resultat(self):
        return mc.lire_binaire(self.FICHIER_BINAIRE)

    def message_termine(self, p):
        return f"{p['iterations']} itérations max"

    # -- Affichage -------------------------------------------------------------
    def image_rgb(self, mu):
        c = self.couleurs_actuelles()
        return mc.colorer(mu, c["palette"], c["densite"], c["decalage"])

    def entete(self):
        return ("z ↦ z² + c   depuis z = 0   ·   les points noirs ne divergent pas",
                f"{nc.sous_titre(self.p)}   ·   {self.p.get('iterations', '?')} itérations max")

    def legende_html(self):
        mu = self.donnees
        dedans = 100 * np.count_nonzero(mu < 0) / mu.size
        dehors = mu[mu >= 0]
        r, g, b = mc.COULEUR_INTERIEUR
        morceaux = [f'<span style="color:#{r:02x}{g:02x}{b:02x}; font-size:15pt">■</span>&nbsp;Dans l\'ensemble'
                    f'&nbsp;<span style="color:{TEXTE_DOUX}">({dedans:.1f}&nbsp;%)</span>']
        if dehors.size:
            morceaux.append(f'Divergence entre <b>{dehors.min():.0f}</b> et <b>{dehors.max():.0f}</b> itérations'
                            f'&nbsp;<span style="color:{TEXTE_DOUX}">(médiane {np.median(dehors):.0f})</span>')
        morceaux.append(f'Palette&nbsp;<b>{self.choix_palette.currentText()}</b>')
        return "&nbsp;&nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp;&nbsp;".join(morceaux)

    def texte_survol(self, valeur):
        if valeur < 0:
            return f"dans l'ensemble (pas de divergence en {self.p.get('iterations', '?')} itérations)"
        return f"diverge après {valeur:.1f} itérations"
