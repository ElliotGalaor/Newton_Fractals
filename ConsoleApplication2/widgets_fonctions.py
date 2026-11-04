"""Composants partagés par les graphes 2D et les surfaces 3D : liste de fonctions
modifiable (à la façon de la fenêtre Algèbre de GeoGebra) et curseurs de paramètres."""
import json
import string

from PySide6 import QtCore, QtWidgets

import expressions as ex
from interface_commune import BORDURE, ERREUR, etiquette

COULEURS_COURBES = ["#4cc9f0", "#f72585", "#ffd166", "#06d6a0", "#9d7dff", "#ff8c42",
                    "#ef476f", "#118ab2", "#caffbf", "#ffadad"]
NOMS_AUTO = [c for c in "fghpqrsuvw"]


def charger_etat(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sauver_etat(chemin, etat):
    try:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(etat, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


class LigneFonction(QtWidgets.QWidget):
    """Une fonction de la liste : couleur, visibilité, expression, suppression."""
    modifiee = QtCore.Signal()
    supprimee = QtCore.Signal(object)

    def __init__(self, texte, couleur, visible, variables):
        super().__init__()
        self.variables = variables
        self.couleur = couleur
        self.expression = None
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        ligne = QtWidgets.QHBoxLayout()
        ligne.setSpacing(6)
        self.bouton_couleur = QtWidgets.QPushButton()
        self.bouton_couleur.setFixedSize(22, 22)
        self.bouton_couleur.setToolTip("Changer de couleur")
        self.bouton_couleur.clicked.connect(self.couleur_suivante)
        self.case = QtWidgets.QCheckBox()
        self.case.setChecked(visible)
        self.case.setToolTip("Afficher / masquer")
        self.case.toggled.connect(lambda _: self.modifiee.emit())
        self.champ = QtWidgets.QLineEdit(texte)
        self.champ.setCursorPosition(0)
        self.champ.textChanged.connect(self.texte_change)
        supprimer = QtWidgets.QPushButton("×")
        supprimer.setFixedSize(26, 26)
        supprimer.setToolTip("Supprimer")
        supprimer.clicked.connect(lambda: self.supprimee.emit(self))
        for w in (self.bouton_couleur, self.case):
            ligne.addWidget(w)
        ligne.addWidget(self.champ, 1)
        ligne.addWidget(supprimer)
        v.addLayout(ligne)
        self.erreur = QtWidgets.QLabel("")
        self.erreur.setWordWrap(True)
        self.erreur.setStyleSheet(f"color: {ERREUR}; font-size: 8.5pt; margin-left: 56px;")
        self.erreur.hide()
        v.addWidget(self.erreur)
        self.appliquer_couleur()
        self.lire()

    def appliquer_couleur(self):
        self.bouton_couleur.setStyleSheet(f"background: {self.couleur}; border: 2px solid {BORDURE}; "
                                          f"border-radius: 11px; padding: 0;")

    def couleur_suivante(self):
        i = COULEURS_COURBES.index(self.couleur) if self.couleur in COULEURS_COURBES else -1
        self.couleur = COULEURS_COURBES[(i + 1) % len(COULEURS_COURBES)]
        self.appliquer_couleur()
        self.modifiee.emit()

    def lire(self):
        try:
            self.expression = ex.lire(self.champ.text(), self.variables)
            self.erreur.hide()
            self.champ.setStyleSheet("")
        except ValueError as e:
            self.expression = None
            vide = not self.champ.text().strip()
            self.erreur.setText("" if vide else str(e))
            self.erreur.setVisible(not vide)
            self.champ.setStyleSheet("" if vide else f"border: 1px solid {ERREUR};")

    def texte_change(self, _):
        self.lire()
        self.modifiee.emit()

    def etat(self):
        return {"texte": self.champ.text(), "couleur": self.couleur, "visible": self.case.isChecked()}


class ListeFonctions(QtWidgets.QWidget):
    """Liste de fonctions ; émet « changee » à chaque modification (frappe, couleur, ajout…)."""
    changee = QtCore.Signal()

    def __init__(self, variables, exemples, etats):
        super().__init__()
        self.variables = variables
        self.exemples = exemples
        self.num_exemple = -1
        self.lignes = []
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.zone_lignes = QtWidgets.QVBoxLayout()
        self.zone_lignes.setSpacing(6)
        v.addLayout(self.zone_lignes)
        ajout = QtWidgets.QHBoxLayout()
        self.champ_nouveau = QtWidgets.QLineEdit()
        self.champ_nouveau.setPlaceholderText("Nouvelle fonction…  (Entrée pour ajouter)")
        self.champ_nouveau.returnPressed.connect(self.ajouter_saisie)
        exemple = QtWidgets.QPushButton("Exemple ▸")
        exemple.clicked.connect(self.ajouter_exemple)
        ajout.addWidget(self.champ_nouveau, 1)
        ajout.addWidget(exemple)
        v.addLayout(ajout)
        for e in etats:
            self.ajouter(e.get("texte", ""), e.get("couleur"), e.get("visible", True), signaler=False)

    def ajouter(self, texte, couleur=None, visible=True, signaler=True):
        if couleur is None:
            utilisees = {l.couleur for l in self.lignes}
            couleur = next((c for c in COULEURS_COURBES if c not in utilisees),
                           COULEURS_COURBES[len(self.lignes) % len(COULEURS_COURBES)])
        ligne = LigneFonction(texte, couleur, visible, self.variables)
        ligne.modifiee.connect(self.changee.emit)
        ligne.supprimee.connect(self.supprimer)
        self.lignes.append(ligne)
        self.zone_lignes.addWidget(ligne)
        if signaler:
            self.changee.emit()
        return ligne

    def ajouter_saisie(self):
        texte = self.champ_nouveau.text().strip()
        if texte:
            self.ajouter(texte)
            self.champ_nouveau.clear()

    def ajouter_exemple(self):
        self.num_exemple = (self.num_exemple + 1) % len(self.exemples)
        self.ajouter(self.exemples[self.num_exemple])

    def supprimer(self, ligne):
        self.lignes.remove(ligne)
        ligne.setParent(None)
        ligne.deleteLater()
        self.changee.emit()

    def vider(self):
        for ligne in list(self.lignes):
            self.lignes.remove(ligne)
            ligne.setParent(None)
            ligne.deleteLater()

    def fonctions(self):
        """[(expression, couleur, visible, nom affiché)] des fonctions lisibles, noms automatiques f, g, h…"""
        pris = {l.expression.nom for l in self.lignes if l.expression and l.expression.nom}
        libres = [n for n in NOMS_AUTO if n not in pris] + list(string.ascii_uppercase)
        resultat = []
        for l in self.lignes:
            if l.expression is None:
                continue
            nom = l.expression.nom or libres.pop(0)
            resultat.append((l.expression, l.couleur, l.case.isChecked(), nom))
        return resultat

    def parametres(self):
        noms = set()
        for l in self.lignes:
            if l.expression is not None:
                noms.update(l.expression.parametres)
        return sorted(noms)

    def etat(self):
        return [l.etat() for l in self.lignes]


class Curseurs(QtWidgets.QWidget):
    """Un curseur par paramètre (a, b, k…), créé ou retiré au fil des fonctions saisies.
    Le bouton ▶ anime le paramètre en le faisant aller et venir entre ses bornes."""
    changes = QtCore.Signal()
    PAS = 100    # le curseur travaille en centièmes

    def __init__(self, valeurs_initiales=None):
        super().__init__()
        self.valeurs = dict(valeurs_initiales or {})
        self.lignes = {}
        self.sens = {}
        self.v = QtWidgets.QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(4)
        self.minuteur = QtCore.QTimer(self)
        self.minuteur.setInterval(40)
        self.minuteur.timeout.connect(self.animer)
        self.animes = set()

    def mettre_a_jour(self, noms):
        for nom in list(self.lignes):
            if nom not in noms:
                widget = self.lignes.pop(nom)[0]
                widget.setParent(None)
                widget.deleteLater()
                self.animes.discard(nom)
        for nom in noms:
            if nom not in self.lignes:
                self.creer(nom)
        self.setVisible(bool(self.lignes))

    def creer(self, nom):
        valeur = float(self.valeurs.get(nom, 1.0))
        conteneur = QtWidgets.QWidget()
        ligne = QtWidgets.QHBoxLayout(conteneur)
        ligne.setContentsMargins(0, 0, 0, 0)
        texte = QtWidgets.QLabel()
        texte.setMinimumWidth(78)
        curseur = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        curseur.setRange(-10 * self.PAS, 10 * self.PAS)
        curseur.setValue(int(round(valeur * self.PAS)))
        lecture = QtWidgets.QPushButton("▶")
        lecture.setFixedSize(30, 26)
        lecture.setCheckable(True)
        lecture.setToolTip(f"Animer {nom}")
        ligne.addWidget(texte)
        ligne.addWidget(curseur, 1)
        ligne.addWidget(lecture)
        self.v.addWidget(conteneur)
        self.lignes[nom] = (conteneur, curseur, texte, lecture)
        self.sens[nom] = 1

        def change(v, nom=nom, texte=texte):
            self.valeurs[nom] = v / self.PAS
            texte.setText(f"<b>{nom}</b> = {v / self.PAS:.2f}")
            self.changes.emit()

        curseur.valueChanged.connect(change)
        lecture.toggled.connect(lambda actif, nom=nom: self.basculer_animation(nom, actif))
        self.valeurs[nom] = valeur
        texte.setText(f"<b>{nom}</b> = {valeur:.2f}")

    def basculer_animation(self, nom, actif):
        (self.animes.add if actif else self.animes.discard)(nom)
        self.lignes[nom][3].setText("❚❚" if actif else "▶")
        if self.animes and not self.minuteur.isActive():
            self.minuteur.start()
        elif not self.animes:
            self.minuteur.stop()

    def animer(self):
        for nom in list(self.animes):
            curseur = self.lignes[nom][1]
            v = curseur.value() + self.sens[nom] * 8
            if v >= curseur.maximum() or v <= curseur.minimum():
                self.sens[nom] *= -1
            curseur.setValue(max(curseur.minimum(), min(curseur.maximum(), v)))

    def valeurs_actuelles(self):
        return {nom: self.valeurs[nom] for nom in self.lignes}


def zone_defilante(largeur=410):
    """Panneau de droite avec défilement : renvoie (cadre, disposition verticale du contenu)."""
    panneau = QtWidgets.QFrame()
    panneau.setObjectName("panneau")
    panneau.setFixedWidth(largeur)
    externe = QtWidgets.QVBoxLayout(panneau)
    externe.setContentsMargins(2, 2, 2, 2)
    defilement = QtWidgets.QScrollArea()
    defilement.setWidgetResizable(True)
    defilement.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    contenu = QtWidgets.QWidget()
    contenu.setObjectName("contenu")
    v = QtWidgets.QVBoxLayout(contenu)
    v.setContentsMargins(18, 14, 18, 12)
    v.setSpacing(6)
    defilement.setWidget(contenu)
    externe.addWidget(defilement)
    return panneau, v


def barre_titre(nom, principale):
    """Bouton « ← Accueil » suivi du titre de la page."""
    barre = QtWidgets.QHBoxLayout()
    retour = QtWidgets.QPushButton("←  Accueil")
    retour.setObjectName("retour")
    retour.setToolTip("Revenir à la page d'accueil (Ctrl+0)")
    retour.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    retour.clicked.connect(principale.aller_accueil)
    barre.addWidget(retour)
    barre.addSpacing(10)
    barre.addWidget(etiquette(nom, "titre"))
    barre.addStretch(1)
    return barre

