"""Tests de fumée de l'interface Qt, hors écran (QT_QPA_PLATFORM=offscreen)."""
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
