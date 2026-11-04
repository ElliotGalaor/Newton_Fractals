"""Page d'accueil : présente les visualisations disponibles et permet d'en ouvrir une."""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

import mandelbrot_calcul as mc
import newton_calcul as nc
from interface_commune import FOND, etiquette, qimage_depuis_rgb

# Groupes de visualisations : (titre du groupe, [(clé, titre, description, points forts, raccourci)])
GROUPES = [
    ("FRACTALES DU PLAN COMPLEXE", [
        ("newton", "Fractales de Newton",
         "Chaque point est coloré selon la racine du polynôme que la méthode de Newton atteint "
         "en partant de lui : les frontières entre ces bassins forment une fractale.",
         ["N'importe quel polynôme, ou ses racines", "Racine atteinte affichée au survol"],
         "Ctrl+1"),
        ("mandelbrot", "Ensemble de Mandelbrot",
         "Les points c pour lesquels z ↦ z² + c, partie de 0, reste bornée. Son bord révèle "
         "spirales, hippocampes et copies miniatures à toutes les échelles.",
         ["Lieux célèbres à visiter en un clic", "Palettes modifiables instantanément"],
         "Ctrl+2"),
    ]),
    ("FONCTIONS RÉELLES", [
        ("graphe2d", "Graphes 2D",
         "Trace des fonctions y = f(x) comme dans GeoGebra : écris une formule, la courbe "
         "s'affiche à la frappe et reste nette quel que soit le zoom.",
         ["Plusieurs fonctions, couleurs, légende", "Paramètres animés par curseurs"],
         "Ctrl+3"),
        ("surfaces3d", "Surfaces 3D",
         "Représente des surfaces z = f(x, y) dans l'espace, éclairées et colorées, à faire "
         "tourner et zoomer à la souris.",
         ["Plusieurs surfaces, fil de fer, hauteur", "Paramètres animés par curseurs"],
         "Ctrl+4"),
    ]),
]
LARGEUR_CARTE, LARGEUR_APERCU, HAUTEUR_APERCU = 330, 294, 170


# --- Aperçus ------------------------------------------------------------------
def _apercu_fractale(cle, largeur, hauteur):
    if cle == "newton":
        indices = nc.calcul_apercu(largeur, hauteur)
        rgb = nc.table_couleurs()[np.clip(indices, 0, 255)]
    else:
        rgb = mc.colorer(mc.calcul_apercu(largeur, hauteur), "Océan", 1.0, 0.0)
    return qimage_depuis_rgb(rgb[::-1])


def _apercu_graphe2d(largeur, hauteur):
    """Quelques courbes dans un repère, dessinées avec QPainter."""
    image = QtGui.QImage(largeur, hauteur, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(FOND))
    p = QtGui.QPainter(image)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    echelle = largeur / 13.0                     # x ∈ [-6.5, 6.5]
    cx, cy = largeur / 2, hauteur / 2

    def ecran(x, y):
        return QtCore.QPointF(cx + x * echelle, cy - y * echelle)

    p.setPen(QtGui.QPen(QtGui.QColor(139, 147, 167, 40), max(1.0, largeur / 600)))
    for k in range(-7, 8):
        p.drawLine(ecran(k, -10), ecran(k, 10))
        p.drawLine(ecran(-10, k), ecran(10, k))
    p.setPen(QtGui.QPen(QtGui.QColor("#8b93a7"), max(1.0, largeur / 300)))
    p.drawLine(ecran(-10, 0), ecran(10, 0))
    p.drawLine(ecran(0, -10), ecran(0, 10))
    x = np.linspace(-6.5, 6.5, 400)
    for y, couleur in ((np.sin(x) * 1.5, "#4cc9f0"), (x ** 2 / 6 - 2.2, "#f72585"),
                       (2.6 * np.exp(-x ** 2 / 2), "#ffd166"), (0.08 * x ** 3 - 0.9 * x, "#06d6a0")):
        chemin = QtGui.QPainterPath(ecran(x[0], y[0]))
        for xi, yi in zip(x[1:], y[1:]):
            chemin.lineTo(ecran(xi, yi))
        p.setPen(QtGui.QPen(QtGui.QColor(couleur), largeur / 140))
        p.drawPath(chemin)
    p.end()
    return image


def _apercu_surface(largeur, hauteur):
    """Surface z = sin(x)·cos(y) en perspective, rendue « à la main » (algorithme du peintre)."""
    image = QtGui.QImage(largeur, hauteur, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(FOND))
    n = 44
    t = np.linspace(-3.2, 3.2, n)
    X, Y = np.meshgrid(t, t, indexing="ij")
    Z = 1.3 * np.sin(X) * np.cos(Y)
    az, el = np.radians(-55), np.radians(30)
    # Rotation autour de z puis inclinaison : coordonnées écran (u, v) et profondeur
    xr = X * np.cos(az) - Y * np.sin(az)
    yr = X * np.sin(az) + Y * np.cos(az)
    u = xr
    v = yr * np.sin(el) + Z * np.cos(el)
    profondeur = yr * np.cos(el) - Z * np.sin(el)
    echelle = min(largeur / (np.ptp(u) * 1.08), hauteur / (np.ptp(v) * 1.15))
    U = largeur / 2 + (u - u.mean()) * echelle
    V = hauteur / 2 - (v - v.mean()) * echelle
    degrade = np.array([[0x2b, 0x1e, 0x6e], [0x11, 0x8a, 0xb2], [0x06, 0xd6, 0xa0],
                        [0xff, 0xd1, 0x66], [0xf7, 0x25, 0x85]], dtype=float)
    lumiere = np.array([-0.4, -0.5, 0.75])
    lumiere /= np.linalg.norm(lumiere)
    faces = []
    for i in range(n - 1):
        for j in range(n - 1):
            coins = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            a = np.array([X[i + 1, j] - X[i, j], Y[i + 1, j] - Y[i, j], Z[i + 1, j] - Z[i, j]])
            b = np.array([X[i, j + 1] - X[i, j], Y[i, j + 1] - Y[i, j], Z[i, j + 1] - Z[i, j]])
            normale = np.cross(a, b)
            normale /= np.linalg.norm(normale) + 1e-12
            eclairage = 0.45 + 0.55 * abs(normale @ lumiere)
            h = (np.mean([Z[c] for c in coins]) + 1.3) / 2.6 * (len(degrade) - 1)
            k = min(int(h), len(degrade) - 2)
            couleur = (degrade[k] * (1 - (h - k)) + degrade[k + 1] * (h - k)) * eclairage
            faces.append((np.mean([profondeur[c] for c in coins]), [(U[c], V[c]) for c in coins], couleur))
    faces.sort(key=lambda f: -f[0])   # du plus loin au plus proche
    p = QtGui.QPainter(image)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    for _, points, couleur in faces:
        c = QtGui.QColor(*[int(min(255, max(0, x))) for x in couleur])
        p.setBrush(c)
        p.setPen(QtGui.QPen(c.darker(115), 0.6))
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in points]))
    p.end()
    return image


def apercu(cle, largeur, hauteur):
    if cle in ("newton", "mandelbrot"):
        return _apercu_fractale(cle, largeur, hauteur)
    if cle == "graphe2d":
        return _apercu_graphe2d(largeur, hauteur)
    return _apercu_surface(largeur, hauteur)


# --- Cartes -------------------------------------------------------------------
class Carte(QtWidgets.QFrame):
    """Carte cliquable présentant une visualisation."""
    ouverte = QtCore.Signal(str)

    def __init__(self, cle, titre, description, points, raccourci):
        super().__init__()
        self.cle = cle
        self.setObjectName("carte")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(LARGEUR_CARTE)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(7)

        # Aperçu calculé à la résolution réelle de l'écran (net même à 125 % ou 150 %)
        ecran = QtGui.QGuiApplication.primaryScreen()
        ratio = max(1.0, ecran.devicePixelRatio() if ecran else 1.0)
        pixmap = QtGui.QPixmap.fromImage(apercu(cle, int(LARGEUR_APERCU * ratio), int(HAUTEUR_APERCU * ratio)))
        pixmap.setDevicePixelRatio(ratio)
        image = QtWidgets.QLabel()
        image.setPixmap(pixmap)
        image.setFixedSize(LARGEUR_APERCU, HAUTEUR_APERCU)
        v.addWidget(image)

        v.addSpacing(4)
        v.addWidget(etiquette(titre, "carte_titre"))
        texte = etiquette(description, "carte_texte")
        texte.setWordWrap(True)
        v.addWidget(texte)
        liste = etiquette("\n".join(f"•  {p}" for p in points), "carte_points")
        liste.setWordWrap(True)
        v.addWidget(liste)
        v.addStretch(1)

        ligne = QtWidgets.QHBoxLayout()
        bouton = QtWidgets.QPushButton("Ouvrir  →")
        bouton.setObjectName("principal")
        bouton.clicked.connect(lambda: self.ouverte.emit(self.cle))
        ligne.addWidget(bouton, 1)
        ligne.addSpacing(10)
        ligne.addWidget(etiquette(raccourci, "raccourci"))
        v.addLayout(ligne)

    def mouseReleaseEvent(self, evenement):
        if evenement.button() == QtCore.Qt.MouseButton.LeftButton:
            self.ouverte.emit(self.cle)
        super().mouseReleaseEvent(evenement)


class PageAccueil(QtWidgets.QWidget):
    def __init__(self, ouvrir):
        super().__init__()
        defilement = QtWidgets.QScrollArea(self)
        defilement.setWidgetResizable(True)
        externe = QtWidgets.QVBoxLayout(self)
        externe.setContentsMargins(0, 0, 0, 0)
        externe.addWidget(defilement)

        contenu = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(contenu)
        v.setContentsMargins(30, 24, 30, 20)
        v.addStretch(1)
        titre = etiquette("Visualisations mathématiques", "grand_titre")
        titre.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(titre)
        accroche = etiquette("Fractales à explorer en zoomant sans fin, fonctions à tracer dans le plan "
                             "et dans l'espace. Choisis une visualisation :", "accroche")
        accroche.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        accroche.setWordWrap(True)
        v.addWidget(accroche)
        v.addSpacing(26)

        rangee = QtWidgets.QHBoxLayout()
        rangee.setSpacing(46)
        rangee.addStretch(1)
        self.cartes = {}
        for titre_groupe, visualisations in GROUPES:
            groupe = QtWidgets.QVBoxLayout()
            groupe.setSpacing(10)
            groupe.addWidget(etiquette(titre_groupe, "section"))
            cartes = QtWidgets.QHBoxLayout()
            cartes.setSpacing(20)
            for cle, titre_carte, description, points, raccourci in visualisations:
                carte = Carte(cle, titre_carte, description, points, raccourci)
                carte.ouverte.connect(ouvrir)
                cartes.addWidget(carte)
                self.cartes[cle] = carte
            groupe.addLayout(cartes)
            rangee.addLayout(groupe)
        rangee.addStretch(1)
        v.addLayout(rangee)
        v.addSpacing(22)
        pied = etiquette("Le menu « Visualisations » permet de passer de l'une à l'autre à tout moment   ·   "
                         "Ctrl+0 : revenir ici", "raccourci")
        pied.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(pied)
        v.addStretch(1)
        defilement.setWidget(contenu)
