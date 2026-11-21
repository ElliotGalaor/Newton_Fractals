"""Génère l'icône du logiciel : une fractale de Newton de z³ - 1, ronde, sur fond transparent.

Sorties :
  packaging/icone.ico            icône Windows (16 à 256 px, images PNG dans le .ico)
  ConsoleApplication2/icone.png  icône de la fenêtre Qt (256 px)

Usage : python packaging/generer_icone.py   (nécessite numpy et PySide6)
"""
import io
import os
import struct

import numpy as np
from PySide6 import QtCore, QtGui

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAILLES = (16, 24, 32, 48, 64, 128, 256)
COULEURS = np.array([(76, 201, 240), (157, 125, 255), (247, 37, 133)], dtype=float)   # couleurs de l'interface


def fractale(n, sur_echantillonnage=4):
    """Image RGBA n×n de la fractale de Newton de z³ - 1, disque anticrénelé."""
    m = n * sur_echantillonnage
    t = (np.arange(m) + 0.5) / m * 2 - 1
    z = (t[None, :] - 1j * t[:, None]) * 1.6
    rayon = np.abs(z) / 1.6
    racines = np.exp(2j * np.pi * np.arange(3) / 3)
    iterations = np.zeros(z.shape)
    with np.errstate(all="ignore"):
        for _ in range(40):
            z = z - (z ** 3 - 1) / (3 * z ** 2)
            iterations += np.min(np.abs(z[..., None] - racines), axis=-1) > 1e-3
    proche = np.argmin(np.abs(np.nan_to_num(z)[..., None] - racines), axis=-1)
    lumiere = np.clip(1.15 - iterations / 22, 0.25, 1)[..., None]
    rgb = COULEURS[proche] * lumiere
    alpha = (rayon <= 1).astype(float)
    # moyenne des sous-pixels (anticrénelage)
    rgb = (rgb * alpha[..., None]).reshape(n, sur_echantillonnage, n, sur_echantillonnage, 3).mean(axis=(1, 3))
    alpha = alpha.reshape(n, sur_echantillonnage, n, sur_echantillonnage).mean(axis=(1, 3))
    rgb = np.where(alpha[..., None] > 0, rgb / np.maximum(alpha[..., None], 1e-9), 0)
    return np.dstack([rgb, alpha * 255]).round().clip(0, 255).astype(np.uint8)


def png(rgba):
    h, w, _ = rgba.shape
    image = QtGui.QImage(np.ascontiguousarray(rgba).data, w, h, 4 * w, QtGui.QImage.Format_RGBA8888)
    tampon = QtCore.QBuffer()
    tampon.open(QtCore.QIODevice.WriteOnly)
    image.save(tampon, "PNG")
    return bytes(tampon.data())


def ico(images_png):
    """Fichier .ico contenant des images PNG (format accepté depuis Windows Vista)."""
    entete = struct.pack("<HHH", 0, 1, len(images_png))
    repertoire, donnees = io.BytesIO(), io.BytesIO()
    decalage = 6 + 16 * len(images_png)
    for taille, contenu in images_png:
        cote = 0 if taille >= 256 else taille            # 0 signifie 256
        repertoire.write(struct.pack("<BBBBHHII", cote, cote, 0, 0, 1, 32, len(contenu), decalage))
        donnees.write(contenu)
        decalage += len(contenu)
    return entete + repertoire.getvalue() + donnees.getvalue()


def main():
    images = [(taille, png(fractale(taille))) for taille in TAILLES]
    with open(os.path.join(RACINE, "packaging", "icone.ico"), "wb") as f:
        f.write(ico(images))
    with open(os.path.join(RACINE, "ConsoleApplication2", "icone.png"), "wb") as f:
        f.write(images[-1][1])
    print("icone.ico et icone.png générés")


if __name__ == "__main__":
    main()
