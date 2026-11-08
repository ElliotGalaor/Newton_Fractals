"""Configuration commune des tests : accès aux modules de ConsoleApplication2 et au moteur C++."""
import os
import shutil
import subprocess
import sys

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_SOURCES = os.path.join(RACINE, "ConsoleApplication2")
sys.path.insert(0, DOSSIER_SOURCES)

# L'interface Qt est testée hors écran (aucun affichage nécessaire, y compris en CI)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def chemin_moteur():
    """Exécutable du moteur : variable MAIN_EXE, sinon main(.exe) compilé dans ConsoleApplication2."""
    candidats = [os.environ.get("MAIN_EXE", "")]
    candidats += [os.path.join(DOSSIER_SOURCES, nom) for nom in ("main.exe", "main")]
    candidats += [os.path.join(RACINE, "x64", "Release", "ConsoleApplication2.exe")]
    return next((c for c in candidats if c and os.path.isfile(c)), None)


@pytest.fixture(scope="session")
def moteur():
    """Lance le moteur C++ : moteur(*options, cwd=...) → subprocess.CompletedProcess."""
    exe = chemin_moteur()
    if exe is None:
        pytest.skip("moteur C++ non compilé (définir MAIN_EXE ou compiler ConsoleApplication2/main)")
    env = dict(os.environ)
    # DLL OpenMP de MinGW pour un exécutable compilé sans -static
    for dossier in (os.path.dirname(shutil.which("g++") or ""), r"C:\msys64\ucrt64\bin"):
        if dossier and os.path.isdir(dossier):
            env["PATH"] = dossier + os.pathsep + env.get("PATH", "")

    def lancer(*options, cwd=None):
        return subprocess.run([exe, *map(str, options)], capture_output=True, text=True,
                              env=env, cwd=cwd, timeout=120)

    return lancer
