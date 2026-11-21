# Spécification PyInstaller : NewtonFractals.exe (dossier dist/NewtonFractals, sans console)
#
# Usage (depuis la racine du dépôt) :
#   python -m PyInstaller --noconfirm packaging/NewtonFractals.spec
# Le moteur C++ (moteur/moteur.exe et ses DLL) est copié ensuite dans dist/NewtonFractals/moteur
# par packaging/construire.ps1.
import os

RACINE = os.path.dirname(os.path.abspath(SPECPATH))
SOURCES = os.path.join(RACINE, "ConsoleApplication2")

# Modules importés dynamiquement par les vues (pyqtgraph.opengl dans la page 3D)
CACHES = ["vue_newton", "vue_mandelbrot", "vue_graphe2d", "vue_surfaces3d",
          "pyqtgraph.opengl", "OpenGL.platform.win32", "OpenGL.arrays.numpymodule"]

# Gros modules inutiles que PyInstaller embarquerait sinon
EXCLUS = ["tkinter", "matplotlib", "scipy", "pandas", "IPython", "pytest", "PyQt5", "PyQt6", "PySide2",
          "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick", "PySide6.QtQml",
          "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization",
          "PySide6.QtPdf", "PySide6.QtBluetooth", "PySide6.QtNetworkAuth", "PySide6.QtSql"]

a = Analysis(
    [os.path.join(SOURCES, "NewtonFractalsDrawing.py")],
    pathex=[SOURCES],
    datas=[(os.path.join(SOURCES, "icone.png"), ".")],
    hiddenimports=CACHES,
    excludes=EXCLUS,
    noarchive=False,
)

# Bibliothèques entraînées par des greffons Qt inutilisés (QML, PDF, réseau sécurisé)
# et traductions de Qt autres que le français et l'anglais
def inutile(chemin):
    nom = os.path.basename(chemin).lower()
    if nom.startswith(("qt6quick", "qt6qml", "qt6pdf", "qt6virtualkeyboard", "libcrypto", "libssl")):
        return True
    dossiers = chemin.replace("\\", "/").lower()
    return "/translations/" in dossiers and not nom.endswith(("_fr.qm", "_en.qm"))


a.binaries = [b for b in a.binaries if not inutile(b[0])]
a.datas = [d for d in a.datas if not inutile(d[0])]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NewtonFractals",
    console=False,
    icon=os.path.join(RACINE, "packaging", "icone.ico"),
    version=os.path.join(RACINE, "build", "version_info.txt"),   # écrit par construire.py
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="NewtonFractals", upx=False)
