"""Tests d'intégration du moteur C++ (main.exe), sur des cas dont le résultat est connu."""
import numpy as np
import pytest

import mandelbrot_calcul as mc
import newton_calcul as nc

pytestmark = pytest.mark.moteur

RACINES_Z3_MOINS_1 = [1, np.exp(2j * np.pi / 3), np.exp(-2j * np.pi / 3)]


def options_racines(racines):
    options = [len(racines)]
    for r in racines:
        options += [complex(r).real, complex(r).imag]
    return options


def test_aide(moteur):
    r = moteur("--aide")
    assert r.returncode == 0 and "--mandelbrot" in r.stdout


def test_newton_z3_moins_1(moteur, tmp_path):
    """Fractale de z³ - 1 : chaque racine attire les points proches d'elle ; les bassins des deux
    racines conjuguées ont la même taille (symétrie par rapport à l'axe réel), et chacun occupe
    environ un tiers du carré (pas exactement : le carré n'a pas la symétrie d'ordre 3)."""
    sortie = tmp_path / "newton.bin"
    r = moteur("--taille", 200, 200, "--bornes", -2, 2, -2, 2, "--iterations", 50,
               "--coefs", 4, 1, 0, 0, 0, 0, 0, -1, 0, "--racines", *options_racines(RACINES_Z3_MOINS_1),
               "--binaire", sortie)
    assert r.returncode == 0, r.stderr
    indices = nc.lire_binaire(str(sortie))            # une ligne par y
    assert indices.shape == (200, 200)
    for k, racine in enumerate(RACINES_Z3_MOINS_1, start=1):
        i = int((racine.real + 2) / 4 * 200)
        j = int((racine.imag + 2) / 4 * 200)
        assert indices[j, i] == k
    parts = [np.mean(indices == k) for k in (1, 2, 3)]
    assert sum(parts) > 0.99                                  # presque tous les points convergent
    assert abs(parts[1] - parts[2]) < 0.01                    # racines conjuguées
    np.testing.assert_allclose(parts, 1 / 3, atol=0.04)


def test_newton_polynome_par_defaut(moteur, tmp_path):
    sortie = tmp_path / "defaut.bin"
    assert moteur("--taille", 50, 40, "--binaire", sortie).returncode == 0
    indices = nc.lire_binaire(str(sortie))
    assert indices.shape == (40, 50) and set(np.unique(indices)) <= {-1, 1, 2, 3}


def test_mandelbrot(moteur, tmp_path):
    """c = 0 et c = -1 sont dans l'ensemble ; c = 1 diverge en quelques itérations."""
    sortie = tmp_path / "mandelbrot.bin"
    r = moteur("--mandelbrot", "--taille", 100, 100, "--bornes", -2, 2, -2, 2, "--iterations", 300,
               "--binaire", sortie)
    assert r.returncode == 0, r.stderr
    mu = mc.lire_binaire(str(sortie))                 # pixel (i, j) au point -2 + 0.04 i, -2 + 0.04 j
    assert mu[50, 50] < 0                             # c = 0
    assert mu[50, 25] < 0                             # c = -1
    assert 0 < mu[50, 75] < 10                        # c = 1
    assert 0.05 < np.mean(mu < 0) < 0.25


@pytest.mark.parametrize("options, message", [
    (["--option-inconnue"], "Option inconnue"),
    (["--mandelbrot"], "--binaire"),
    (["--taille", 0, 10, "--binaire", "x.bin"], "1 pixel"),
    (["--bornes", 1, 0, -1, 1, "--binaire", "x.bin"], "MIN < MAX"),
    (["--coefs", 2, 1, 0, -1, 0, "--binaire", "x.bin"], "ensemble"),
])
def test_erreurs(moteur, tmp_path, options, message):
    r = moteur(*options, cwd=tmp_path)
    assert r.returncode == 1 and message in r.stderr
