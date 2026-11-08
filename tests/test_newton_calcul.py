"""Logique de la fractale de Newton : polynômes, racines, nombres, fichiers."""
import numpy as np
import pytest

import newton_calcul as nc


def test_racines_du_polynome_par_defaut():
    coefs, racines = nc.lire_polynome("z^3 - 2z + 2")
    np.testing.assert_allclose(coefs, [1, 0, -2, 2])
    assert len(racines) == 3
    np.testing.assert_allclose(np.polyval(coefs, np.array(racines)), 0, atol=1e-9)
    assert racines[0].real < 0 and abs(racines[0].imag) < 1e-12   # triées : la racine réelle d'abord


@pytest.mark.parametrize("texte, degre", [("(z-1)(z+2i)", 2), ("z^3 - (1 + 2i)z + 1", 3), ("2z**2 + .5", 2),
                                          ("x^2+1", 2), ("z(z+1)", 2), ("1e-3z^2 - 1", 2)])
def test_syntaxe_des_polynomes(texte, degre):
    coefs, _ = nc.lire_polynome(texte)
    assert len(coefs) == degre + 1


def test_racines_multiples_regroupees():
    """np.roots éparpille une racine triple d'environ 1e-5 : elle doit rester une seule racine."""
    _, racines = nc.lire_polynome("(z-1)^3(z+1)")
    np.testing.assert_allclose(sorted(r.real for r in racines), [-1, 1], atol=1e-4)


@pytest.mark.parametrize("texte, message", [("3", "degré 1"), ("z^-1", "exposant"), ("z^30", "exposant"),
                                            ("z/0", "diviser"), ("sin(z)", "caractère inattendu"),
                                            ("__import__('os')", "caractère inattendu")])
def test_polynomes_refuses(texte, message):
    with pytest.raises(ValueError, match=message):
        nc.lire_polynome(texte)


def test_lecture_des_racines():
    assert nc.lire_racines("1 ; -1 ; i") == [1, -1, 1j]
    assert nc.lire_racines("1, -1, 2i") == [1, -1, 2j]
    assert nc.lire_racines("0,5 ; 1+i") == [0.5, 1 + 1j]           # virgule décimale avec « ; »
    np.testing.assert_allclose(nc.lire_racines("(1+i)/2 ; 1/3"), [0.5 + 0.5j, 1 / 3])
    with pytest.raises(ValueError, match="vide"):
        nc.lire_racines("1 ; ; 2")
    with pytest.raises(ValueError, match="20 au maximum"):
        nc.lire_racines(";".join(["1"] * 21))


@pytest.mark.parametrize("texte", ["z^3 - 2z + 2", "(z-1)^3(z+1)", "z^3 - (1 + 2i)z + 1", "z^4 - 1"])
def test_aller_retour_polynome_racines(texte):
    """Polynôme → racines (texte) → polynôme : on retrouve le polynôme unitaire de départ."""
    coefs, _ = nc.lire_polynome(texte)
    texte_racines = nc.texte_racines(coefs)
    coefs2, _ = nc.depuis_racines(nc.lire_racines(texte_racines))
    coefs3, _ = nc.lire_polynome(nc.texte_polynome(coefs2))
    np.testing.assert_allclose(coefs3, coefs / coefs[0], atol=1e-8)


def test_texte_polynome_sans_bruit_d_arrondi():
    coefs, _ = nc.depuis_racines(nc.lire_racines(nc.texte_racines(nc.lire_polynome("z^3 - 2z + 2")[0])))
    assert nc.texte_polynome(coefs) == "z^3 - 2z + 2"


@pytest.mark.parametrize("a, b", [(-2, 2), (-0.743794786, -0.743494786), (0.1161199999, 0.1161200001),
                                  (0.30000000000000004, 0.30000000000000016)])
def test_bornes_en_ecriture_scientifique(a, b):
    """Les bornes restent distinctes, l'écart est juste et elles ne glissent pas (vue stable au recalcul)."""
    ta, tb = nc.intervalle_sci(a, b)
    ra, rb = float(ta), float(tb)
    assert rb > ra
    assert abs((rb - ra) - (b - a)) <= 1e-6 * (b - a)
    assert abs(ra - a) <= 1e-6 * (b - a) and abs(rb - b) <= 1e-6 * (b - a)


def test_limite_de_zoom():
    assert nc.ecart_trop_petit(0.5, 0.5 + 1e-14)
    assert not nc.ecart_trop_petit(0.5, 0.5 + 1e-9)


@pytest.mark.parametrize("v, ecart, attendu", [(0.5, 0.5, "0.5"), (-1.25, 0.25, "-1.25"), (2, 1, "2"),
                                               (0, 0.5, "0"), (0.11612, 1e-5, "1.1612e-1")])
def test_graduations(v, ecart, attendu):
    assert nc.etiquette_axe(v, ecart) == attendu


def test_format_binaire(tmp_path):
    """results.bin : dim_x, dim_y (int32) puis un int8 par pixel, ligne par ligne selon x."""
    indices_x_y = np.array([[1, 2, -1], [3, 1, 2]], dtype=np.int8)          # dim_x = 2, dim_y = 3
    chemin = tmp_path / "r.bin"
    chemin.write_bytes(np.array([2, 3], dtype="<i4").tobytes() + indices_x_y.tobytes())
    np.testing.assert_array_equal(nc.lire_binaire(str(chemin)), indices_x_y.T)   # une ligne par y
    chemin.write_bytes(np.array([2, 3], dtype="<i4").tobytes() + b"\x01")
    with pytest.raises(ValueError, match="incomplet"):
        nc.lire_binaire(str(chemin))


def test_arguments_du_moteur():
    p = dict(nc.DEFAUTS, **nc.lire_saisie_polynome("z^2 - 1", "polynome"))
    args = nc.arguments_calcul(p, "sortie.bin")
    assert args[args.index("--coefs") + 1] == "3" and args[args.index("--racines") + 1] == "2"
    assert args[args.index("--binaire") + 1] == "sortie.bin"


def test_verification_des_parametres():
    p = dict(nc.DEFAUTS)
    nc.verifier_parametres(p)
    for cle, valeur, message in (("largeur", 0, "taille"), ("max_x", -3, "min < max"), ("eps", 0, "précision"),
                                 ("iterations", 0, "Itérations")):
        with pytest.raises(ValueError, match=message):
            nc.verifier_parametres(dict(p, **{cle: valeur}))
