"""Tests de fumée de l'interface Qt, hors écran (QT_QPA_PLATFORM=offscreen)."""
import os

import numpy as np
import pytest

pytestmark = pytest.mark.interface

QtWidgets = pytest.importorskip("PySide6.QtWidgets", reason="PySide6 absent", exc_type=ImportError)
pg = pytest.importorskip("pyqtgraph", reason="pyqtgraph absent", exc_type=ImportError)


class Arguments:
    vue = None
    fichier = "absent.txt"
    bornes = None
    eps = None
    iterations = None
    polynome = None


@pytest.fixture(scope="module")
def application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def fenetre(application, tmp_path, monkeypatch):
    import newton_calcul as nc
    import vue_graphe2d
    import vue_surfaces3d

    # Aucun fichier d'état ni de résultat écrit dans le projet
    monkeypatch.setattr(nc, "DOSSIER", str(tmp_path))
    monkeypatch.setattr(nc, "DOSSIER_DONNEES", str(tmp_path))
    monkeypatch.setattr(nc, "FICHIER_PARAMETRES", str(tmp_path / "parametres.json"))
    monkeypatch.setattr(vue_graphe2d, "FICHIER_ETAT", str(tmp_path / "graphes2d.json"))
    monkeypatch.setattr(vue_surfaces3d, "FICHIER_ETAT", str(tmp_path / "surfaces3d.json"))
    import NewtonFractalsDrawing as entree

    application.setStyleSheet(entree.STYLE)
    f = entree.FenetrePrincipale(Arguments(), None)
    yield f
    f.close()


def test_accueil(fenetre):
    assert fenetre.pile.currentWidget() is fenetre.accueil
    assert set(fenetre.accueil.cartes) == {"newton", "mandelbrot", "graphe2d", "surfaces3d"}


def test_navigation(fenetre):
    fenetre.ouvrir("newton")
    assert fenetre.windowTitle().startswith("Fractales de Newton")
    assert "introuvable" in fenetre.vues["newton"].label_statut.text()   # pas de moteur dans ce test
    fenetre.aller_accueil()
    assert fenetre.pile.currentWidget() is fenetre.accueil


def test_menu_aide_et_manuel(fenetre):
    import NewtonFractalsDrawing as entree

    menus = [action.text() for action in fenetre.menuBar().actions()]
    assert "&Aide" in menus
    assert entree.chemin_manuel().endswith(os.path.join("docs", "manuel", "index.html"))
    assert os.path.isfile(entree.chemin_icone())


def test_auto_test_sans_moteur(fenetre, tmp_path):
    """Le rapport est écrit même quand une page échoue ; sans moteur, les fractales échouent."""
    import json

    import NewtonFractalsDrawing as entree

    rapport = tmp_path / "rapport.json"
    assert entree.auto_test(fenetre, str(rapport)) == 1
    pages = json.loads(rapport.read_text(encoding="utf-8"))["pages"]
    assert pages["graphe2d"]["ok"] and pages["graphe2d"]["courbes"] > 0
    assert not pages["newton"]["ok"] and "introuvable" in pages["newton"]["erreur"]
    assert fenetre.pile.currentWidget() is fenetre.accueil


def test_graphes_2d(fenetre, application):
    fenetre.ouvrir("graphe2d")
    vue = fenetre.vues["graphe2d"]
    vue.liste.vider()
    vue.liste.ajouter("x^2 + y^2 = r^2")          # équation avec un paramètre
    vue.liste.ajouter("f(x) = sin(x)")
    ligne_fausse = vue.liste.ajouter("sin x")
    application.processEvents()
    assert len(vue.courbes) == 2
    assert all(not courbe.path().isEmpty() for courbe, *_ in vue.courbes)
    assert list(vue.curseurs.valeurs_actuelles()) == ["r"]
    assert "parenthèses" in ligne_fausse.erreur.text()


def test_marching_cubes_sphere():
    """Extraction de surface utilisée par la page 3D (sans créer de vue OpenGL)."""
    t = np.linspace(-5, 5, 60)
    x, y, z = np.meshgrid(t, t, t, indexing="ij")
    sommets, faces = pg.isosurface(x ** 2 + y ** 2 + z ** 2 - 9, 0.0)
    rayons = np.linalg.norm(-5 + np.asarray(sommets) * (10 / 59), axis=1)
    assert len(faces) > 1000
    np.testing.assert_allclose(rayons, 3.0, atol=0.02)


@pytest.mark.parametrize("etat", ['{"fonctions": "abc"}', '{"fonctions": [{"texte": "x", "couleur": "pas une couleur"}]}',
                                  '{"min_x": "a"}', '{"fonctions": 5, "parametres": {"a": "x"}}', "[1, 2]",
                                  '{"resolution": 100000}', '{"min_x": -Infinity}', '{"vue": [1, 0, "a"]}', "{"])
def test_etat_sauvegarde_invalide_ignore(fenetre, etat):
    """Un fichier d'état modifié ou abîmé ne doit jamais empêcher une page de s'ouvrir."""
    import vue_graphe2d
    import vue_surfaces3d

    for module in (vue_graphe2d, vue_surfaces3d):
        with open(module.FICHIER_ETAT, "w", encoding="utf-8") as f:
            f.write(etat)
    fenetre.ouvrir("graphe2d")
    assert fenetre.pile.currentWidget() is fenetre.vues["graphe2d"]
    if vue_surfaces3d.ERREUR_OPENGL is None:
        vue = vue_surfaces3d.VueSurfaces3D(fenetre)
        vue_surfaces3d.verifier_domaine(vue.domaine)


def test_domaine_3d_verifie():
    import vue_surfaces3d as v3

    textes = {cle: str(v) for cle, v in v3.DOMAINE.items()}
    assert v3.lire_domaine(textes) == v3.DOMAINE
    for cle, texte, message in (("max_x", "nan", "fini"), ("min_x", "-1e308", "trop grande"),
                                ("max_x", "abc", "nombre attendu"), ("resolution", "12.9", "entier"),
                                ("limite_z", "inf", "fini")):
        with pytest.raises(ValueError, match=message):
            v3.lire_domaine(dict(textes, **{cle: texte}))


def test_trous_sans_rideaux():
    """z = f(x, y) avec des trous : aucun triangle ne touche un point non défini."""
    import vue_surfaces3d as v3

    xs = np.linspace(-3, 3, 31)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    Z = np.sqrt(4 - X ** 2 - Y ** 2)
    trous = ~np.isfinite(Z)
    sommets, faces = v3.maillage_grille(xs, xs, np.where(trous, 0, Z), trous)
    assert len(faces) > 0 and not trous.ravel()[faces].any()


def test_pas_de_surface_sur_un_pole():
    import expressions as ex
    import vue_surfaces3d as v3

    n, bornes = 60, [(-5, 5)] * 3
    X, Y, Z = np.meshgrid(*[np.linspace(a, b, n) for a, b in bornes], indexing="ij")
    for texte, plans in (("tan(x) = 0", [-np.pi, 0, np.pi]), ("1/x = 0", [])):
        e = ex.lire(texte, ("x", "y"), equations=True)
        F = e.evaluer({"x": X, "y": Y, "z": Z})
        grille, faces = pg.isosurface(F, 0.0)
        grille = np.asarray(grille, dtype=float)
        sommets = -5 + grille * (10 / (n - 1))
        faux = v3.sommets_sur_un_pole(e, {}, sommets, grille, F, bornes)
        gardes = faces[~faux[faces].any(axis=1)]
        np.testing.assert_allclose(np.unique(np.round(sommets[np.unique(gardes), 0], 1)), np.round(plans, 1))


def test_enregistrer_utilise_le_fichier_demande(tmp_path):
    """--enregistrer exporte le fichier --fichier, pas le dernier calcul mémorisé."""
    import subprocess
    import sys

    grille = tmp_path / "mini.txt"
    grille.write_text("1 2 3\n3 2 1\n1 1 1\n2 2 2\n", encoding="utf-8")   # 4 valeurs de x, 3 de y
    image = tmp_path / "mini.png"
    script = os.path.join(os.path.dirname(__file__), "..", "ConsoleApplication2", "NewtonFractalsDrawing.py")
    r = subprocess.run([sys.executable, script, "--enregistrer", str(image), "--fichier", str(grille)],
                       capture_output=True, text=True, env=dict(os.environ, NEWTON_FRACTALS_RELANCE="1"), timeout=120)
    assert r.returncode == 0, r.stderr
    from PySide6 import QtGui
    lue = QtGui.QImage(str(image))
    assert (lue.width(), lue.height()) == (4, 3)
    r = subprocess.run([sys.executable, script, "--enregistrer", str(image), "--fichier", str(tmp_path / "absent.txt")],
                       capture_output=True, text=True, env=dict(os.environ, NEWTON_FRACTALS_RELANCE="1"), timeout=120)
    assert r.returncode != 0 and "introuvable" in r.stderr
