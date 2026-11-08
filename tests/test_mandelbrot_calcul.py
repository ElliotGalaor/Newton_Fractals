"""Logique de l'ensemble de Mandelbrot : couleurs, itérations, fichiers."""
import numpy as np
import pytest

import mandelbrot_calcul as mc


def test_coloration():
    mu = np.array([[-1.0, 0.0], [10.0, 300.0]])
    rgb = mc.colorer(mu, "Océan")
    assert rgb.shape == (2, 2, 3) and rgb.dtype == np.uint8
    assert tuple(rgb[0, 0]) == mc.COULEUR_INTERIEUR                        # point de l'ensemble
    # Le décalage d'une période complète ne change rien (palettes cycliques)
    np.testing.assert_array_equal(mc.colorer(mu, "Feu", 1.0, 0.0), mc.colorer(mu, "Feu", 1.0, 1.0))


@pytest.mark.parametrize("nom", mc.NOMS_PALETTES)
def test_palettes(nom):
    table = mc.TABLES[nom]
    assert table.shape == (1024, 3)
    assert np.abs(table[0].astype(int) - table[-1].astype(int)).max() < 40   # boucle sans saut visible


def test_iterations_croissantes_avec_le_zoom():
    valeurs = [mc.iterations_pour_zoom(w) for w in (3.5, 1e-2, 1e-4, 1e-8, 1e-12)]
    assert valeurs == sorted(valeurs) and valeurs[0] >= 200 and valeurs[-1] <= 100_000


def test_format_binaire(tmp_path):
    mu_x_y = np.array([[-1.0, 2.5], [3.25, 0.0], [1.0, -1.0]], dtype="<f4")   # dim_x = 3, dim_y = 2
    chemin = tmp_path / "m.bin"
    chemin.write_bytes(np.array([3, 2], dtype="<i4").tobytes() + mu_x_y.tobytes())
    np.testing.assert_array_equal(mc.lire_binaire(str(chemin)), mu_x_y.T)


def test_apercu_numpy():
    mu = mc.calcul_apercu(80, 50, 100)
    assert mu.shape == (50, 80)
    assert 0.05 < (mu < 0).mean() < 0.4          # l'ensemble occupe une partie de l'image
    assert (mu[mu >= 0] >= 0).all()


def test_lieux_celebres_valides():
    for nom, cx, cy, largeur in mc.LIEUX:
        assert -2.5 < cx < 1 and -1.5 < cy < 1.5 and largeur > 0, nom


def test_arguments_du_moteur():
    args = mc.arguments_calcul(dict(mc.DEFAUTS), "m.bin")
    assert args[0] == "--mandelbrot" and args[-2:] == ["--binaire", "m.bin"]
