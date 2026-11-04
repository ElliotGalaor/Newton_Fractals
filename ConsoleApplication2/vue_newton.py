"""Page « Fractales de Newton » : bassins d'attraction de la méthode de Newton."""
import numpy as np
from PySide6 import QtWidgets

import newton_calcul as nc
from interface_commune import ERREUR, TEXTE_DOUX, VueFractale, etiquette


class VueNewton(VueFractale):
    NOM = "Fractales de Newton"
    FICHIER_BINAIRE = nc.FICHIER_BINAIRE
    FICHIER_PARAMETRES = nc.FICHIER_PARAMETRES
    CHAMPS = nc.CHAMPS
    DEFAUTS = nc.DEFAUTS
    LIBELLE_POINT = "z"

    def __init__(self, principale, parametres, donnees, executable):
        self.racines = nc.racines_de(parametres)
        self.mode = parametres.get("mode", "polynome")   # contenu du champ polynôme : p(z) ou racines
        self.num_exemple = {"polynome": 0, "racines": -1}
        self.table = nc.table_couleurs()
        super().__init__(principale, parametres, donnees, executable)

    # -- Panneau -------------------------------------------------------------
    def construire_debut_panneau(self, v):
        """Polynôme : sélecteur p(z) / racines, champ, exemples."""
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
        ligne.addWidget(self.champ("polynome", nc.textes_champs(self.p).get("polynome", "")), 1)
        bouton_exemple = QtWidgets.QPushButton("Exemple ▸")
        bouton_exemple.clicked.connect(self.exemple_suivant)
        ligne.addWidget(bouton_exemple)
        v.addLayout(ligne)

    def construire_fin_panneau(self, v):
        self.grille_champs(v, "CONVERGENCE", [("eps", "iterations")], nc.textes_champs(self.p))

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

    def valeurs_defaut_specifiques(self):
        self.changer_mode("polynome", texte=nc.DEFAUTS["polynome"])

    # -- Calcul ------------------------------------------------------------------
    def lire_specifique(self):
        return nc.lire_saisie_polynome(self.champs["polynome"].text(), self.mode)

    def verifier(self, p):
        nc.verifier_parametres(p)

    def arguments(self, p):
        return nc.arguments_calcul(p, self.FICHIER_BINAIRE)

    def lire_resultat(self):
        return nc.lire_binaire(self.FICHIER_BINAIRE)

    def apres_resultat(self, p):
        self.racines = p["racines"] if "racines" in p else nc.racines_de(self.p)

    def message_termine(self, p):
        return f"{len(p['racines'])} racine(s)"

    # -- Affichage -------------------------------------------------------------
    def image_rgb(self, indices):
        return self.table[np.clip(indices, 0, 255)]

    def entete(self):
        return nc.titre_polynome(self.p, 110), nc.sous_titre(self.p)

    def legende_html(self):
        indices = self.donnees
        total = indices.size
        nb = len(self.racines) if self.racines else max(int(indices.max()), 1)
        morceaux = []
        for k in range(1, nb + 1):
            couleur = nc.COULEURS_RACINES[(k - 1) % len(nc.COULEURS_RACINES)]
            nom = nc.texte_complexe(self.racines[k - 1]) if self.racines else f"Racine {k}"
            part = 100 * np.count_nonzero(indices == k) / total
            morceaux.append(f'<span style="color:{couleur}; font-size:15pt">■</span>&nbsp;{nom}'
                            f'&nbsp;<span style="color:{TEXTE_DOUX}">({part:.1f}&nbsp;%)</span>')
        non_conv = np.count_nonzero(indices < 1)
        if non_conv:
            morceaux.append(f'<span style="color:{nc.COULEUR_NON_CONVERGENCE}; font-size:15pt">■</span>'
                            f'&nbsp;Pas de convergence&nbsp;<span style="color:{TEXTE_DOUX}">'
                            f'({100 * non_conv / total:.1f}&nbsp;%)</span>')
        return "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(morceaux)

    def texte_survol(self, valeur):
        k = int(valeur)
        if k < 1:
            return "pas de convergence"
        if self.racines and k <= len(self.racines):
            return f"racine {k} = {nc.texte_complexe(self.racines[k - 1], 6)}"
        return f"racine {k}"
