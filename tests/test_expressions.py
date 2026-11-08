"""Lecteur de fonctions réelles (graphes 2D et surfaces 3D)."""
import numpy as np
import pytest

import expressions as ex

X = np.array([-1.0, 0.0, 0.5, 2.0])


def valeurs(texte, **parametres):
    return ex.lire(texte, ("x",)).evaluer(dict(parametres, x=X))


@pytest.mark.parametrize("texte, attendu", [
    ("sin(x)", np.sin(X)),
    ("x^2 - 3", X ** 2 - 3),
    ("x**2", X ** 2),
    ("x²", X ** 2),                       # notation unicode
    ("2x", 2 * X),                        # multiplication implicite
    ("xsin(x)", X * np.sin(X)),           # « xsin » = x · sin
    ("(x-1)(x+1)", (X - 1) * (X + 1)),
    ("2pi x", 2 * np.pi * X),
    ("π", np.full_like(X, np.pi)),
    ("e^x", np.exp(X)),
    ("3", np.full_like(X, 3.0)),          # constante : même forme que x
    ("abs(x) - 2", np.abs(X) - 2),
])
def test_evaluation(texte, attendu):
    np.testing.assert_allclose(valeurs(texte), attendu)


def test_valeurs_hors_domaine_donnent_nan():
    assert np.isnan(valeurs("1/x")[1])          # division par zéro
    assert np.isnan(valeurs("ln(x)")[0])        # logarithme d'un négatif
    assert np.isnan(valeurs("sqrt(x)")[0])


def test_parametres_detectes_et_utilises():
    e = ex.lire("a sin(b x)", ("x",))
    assert e.parametres == ["a", "b"]
    np.testing.assert_allclose(e.evaluer({"x": X, "a": 2.0, "b": 3.0}), 2 * np.sin(3 * X))


@pytest.mark.parametrize("texte, nom", [("f(x) = x^2", "f"), ("y = x^2", None), ("x^2", None)])
def test_prefixe_de_definition(texte, nom):
    e = ex.lire(texte, ("x",))
    assert e.nom == nom and not e.implicite
    np.testing.assert_allclose(e.evaluer({"x": X}), X ** 2)


@pytest.mark.parametrize("texte, message", [
    ("sin x", "parenthèses"),
    ("sen(x)", "nom inconnu"),            # faute de frappe : pas de découpage en paramètres s·e·n
    ("x ** ", "mal écrite"),
    ("y + 1", "y n'est pas une variable"),
    ("", "rien n'est écrit"),
])
def test_erreurs_explicites(texte, message):
    with pytest.raises(ValueError, match=message):
        ex.lire(texte, ("x",))


@pytest.mark.parametrize("texte", ["__import__('os')", "x; 1", "x.real", "[x]", "lambda: 1", "open(x)"])
def test_aucun_code_python_execute(texte):
    """Le lecteur n'accepte que des expressions mathématiques : jamais d'appel arbitraire."""
    with pytest.raises(ValueError):
        ex.lire(texte, ("x",))


# --- Équations (courbes et surfaces implicites) ----------------------------------
@pytest.mark.parametrize("texte", ["x^2 + y^2 = 4", "sin(x) = cos(y)", "x = 2", "2y = x", "y^2 = x^3 - x"])
def test_equations_dans_le_plan(texte):
    e = ex.lire(texte, ("x",), equations=True)
    assert e.implicite and e.variables == ("x", "y") and e.nom is None


def test_y_egal_reste_une_fonction_dans_le_plan():
    assert not ex.lire("y = x^2", ("x",), equations=True).implicite


def test_dimension_du_prefixe():
    """« y = » définit une fonction dans le plan, mais c'est une surface dans l'espace (et inversement pour z)."""
    assert ex.lire("y = x^2", ("x", "y"), equations=True).implicite
    surface = ex.lire("z = x y", ("x", "y"), equations=True)
    assert not surface.implicite and surface.variables == ("x", "y")


def test_equation_dans_l_espace():
    e = ex.lire("x^2 + y^2 + z^2 = r^2", ("x", "y"), equations=True)
    assert e.implicite and e.variables == ("x", "y", "z") and e.parametres == ["r"]


def test_equations_refusees_sans_l_option():
    with pytest.raises(ValueError):
        ex.lire("x^2 + y^2 = 4", ("x", "y"))


@pytest.mark.parametrize("texte, message", [
    ("x = = 2", "un seul signe"),
    ("x^2 + y^2 =", "il manque un membre"),
    ("x + y", "écris-la avec ="),
])
def test_erreurs_d_equations(texte, message):
    with pytest.raises(ValueError, match=message):
        ex.lire(texte, ("x",), equations=True)


def test_exemples_proposes_sont_valides():
    for texte in ex.EXEMPLES_2D:
        ex.lire(texte, ("x",), equations=True)
    for texte in ex.EXEMPLES_3D:
        ex.lire(texte, ("x", "y"), equations=True)


# --- Tracés -------------------------------------------------------------------------
def test_cercle_par_carres_marchants():
    e = ex.lire("x^2 + y^2 = 4", ("x",), equations=True)
    segments = ex.segments_implicites(e, -5, 5, -3, 3, 450, 270, {})
    assert len(segments) > 100
    rayons = np.hypot(segments[..., 0], segments[..., 1])
    np.testing.assert_allclose(rayons, 2.0, atol=1e-3)


def test_pas_de_faux_trait_sur_un_pole():
    """y = 1/x change de signe en x = 0 sans que la courbe y passe."""
    e = ex.lire("y - 1/x = 0", ("x",), equations=True)
    s = ex.segments_implicites(e, -5, 5, -3, 3, 450, 270, {})
    verticaux_sur_le_pole = (np.abs(s[..., 0]) < 0.03).all(axis=1) & (np.abs(s[:, 0, 1] - s[:, 1, 1]) > 0.01)
    assert not verticaux_sur_le_pole.any()


def test_cas_selle_et_equation_sans_solution():
    croix = ex.segments_implicites(ex.lire("x^2 - y^2 = 0", ("x",), equations=True), -2, 2, -2, 2, 101, 101, {})
    assert len(croix) > 0
    vide = ex.segments_implicites(ex.lire("x^2 + y^2 = -1", ("x",), equations=True), -2, 2, -2, 2, 50, 50, {})
    assert vide.shape == (0, 2, 2)


def test_asymptotes_coupees():
    x, y = ex.echantillonner_courbe(ex.lire("tan(x)", ("x",)), -5, 5, 10, {}, 1000)
    assert np.isnan(y).sum() >= 3      # une coupure par asymptote (x = ±π/2, ±3π/2)
