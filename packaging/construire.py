"""Construit le logiciel Windows : dist/NewtonFractals/ puis l'installateur NewtonFractals-Setup-X.Y.Z.exe.

Étapes :
  1. moteur C++ : compilé avec g++ (MinGW, OpenMP) ou fourni par --moteur, avec les DLL dont il dépend ;
  2. interface : NewtonFractals.exe et Python embarqué, avec PyInstaller (packaging/NewtonFractals.spec) ;
  3. manuel utilisateur (docs/manuel) copié à côté du logiciel ;
  4. installateur compilé avec Inno Setup (ISCC.exe), s'il est installé.

Usage (depuis la racine du dépôt, avec les dépendances de requirements.txt et pyinstaller) :
  python packaging/construire.py [--moteur CHEMIN\\main.exe] [--sans-installateur]
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, "ConsoleApplication2")
CONSTRUCTION = os.path.join(RACINE, "build")
DIST = os.path.join(RACINE, "dist")
APPLICATION = os.path.join(DIST, "NewtonFractals")


def version():
    with open(os.path.join(SOURCES, "NewtonFractalsDrawing.py"), encoding="utf-8") as f:
        return re.search(r'^VERSION = "(\d+\.\d+\.\d+)"', f.read(), re.M).group(1)


def etape(texte):
    print(f"\n== {texte}", flush=True)


# ---------- 1. Moteur C++ et ses DLL ----------

def dll_importees(chemin):
    """Noms des DLL importées par un exécutable PE (table d'imports)."""
    with open(chemin, "rb") as f:
        donnees = f.read()
    pe = struct.unpack_from("<I", donnees, 0x3C)[0]
    nb_sections, taille_optionnel = struct.unpack_from("<H", donnees, pe + 6)[0], struct.unpack_from("<H", donnees, pe + 20)[0]
    optionnel = pe + 24
    pe32_plus = struct.unpack_from("<H", donnees, optionnel)[0] == 0x20B
    rva_imports = struct.unpack_from("<I", donnees, optionnel + (120 if pe32_plus else 104))[0]
    sections = []
    for k in range(nb_sections):
        s = optionnel + taille_optionnel + 40 * k
        taille_virtuelle, adresse, _taille_brute, position = struct.unpack_from("<IIII", donnees, s + 8)
        sections.append((adresse, max(taille_virtuelle, _taille_brute), position))

    def position(rva):
        for adresse, taille, debut in sections:
            if adresse <= rva < adresse + taille:
                return rva - adresse + debut
        raise ValueError(f"adresse {rva:#x} hors des sections")

    noms, p = [], position(rva_imports) if rva_imports else None
    while p is not None:
        rva_nom = struct.unpack_from("<I", donnees, p + 12)[0]
        if rva_nom == 0:
            break
        debut = position(rva_nom)
        noms.append(donnees[debut:donnees.index(b"\0", debut)].decode("ascii"))
        p += 20
    return noms


def dependances(exe, dossiers):
    """DLL non fournies par Windows dont dépend exe (récursivement), cherchées dans dossiers."""
    systeme = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    trouvees, a_voir = {}, [exe]
    while a_voir:
        for nom in dll_importees(a_voir.pop()):
            cle = nom.lower()
            if cle in trouvees or cle.startswith(("api-ms-", "ext-ms-")) or os.path.isfile(os.path.join(systeme, nom)):
                continue
            chemin = next((os.path.join(d, nom) for d in dossiers if os.path.isfile(os.path.join(d, nom))), None)
            if chemin is None:
                sys.exit(f"DLL introuvable : {nom} (dépendance de {os.path.basename(exe)})")
            trouvees[cle] = chemin
            a_voir.append(chemin)
    return sorted(trouvees.values())


def preparer_moteur(moteur):
    dossier = os.path.join(CONSTRUCTION, "moteur")
    os.makedirs(dossier, exist_ok=True)
    gpp = shutil.which("g++")
    if moteur is None:
        if gpp is None:
            sys.exit("g++ introuvable : installez MinGW (MSYS2 UCRT64) ou indiquez --moteur main.exe")
        moteur = os.path.join(dossier, "moteur.exe")
        etape(f"Compilation du moteur avec {gpp}")
        subprocess.run([gpp, "-std=c++14", "-O2", "-fopenmp", "-o", moteur,
                        *(os.path.join(SOURCES, f) for f in ("main.cpp", "Tableau.cpp", "CNum.cpp"))], check=True)
    dossiers = [os.path.dirname(os.path.abspath(moteur))] + ([os.path.dirname(gpp)] if gpp else [])
    dossiers += os.environ.get("PATH", "").split(os.pathsep)
    return moteur, dependances(moteur, [d for d in dossiers if d])


# ---------- 2. PyInstaller ----------

def ecrire_infos_version(v):
    """Ressource « Détails » de l'exe (clic droit > Propriétés dans l'explorateur)."""
    nombres = ", ".join(v.split(".") + ["0"])
    texte = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nombres}), prodvers=({nombres})),
  kids=[StringFileInfo([StringTable('040C04B0', [
      StringStruct('CompanyName', 'Elliot Galaor'),
      StringStruct('FileDescription', 'Newton Fractals - visualisations mathématiques'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'NewtonFractals'),
      StringStruct('OriginalFilename', 'NewtonFractals.exe'),
      StringStruct('ProductName', 'Newton Fractals'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [0x040C, 1200])])])
"""
    os.makedirs(CONSTRUCTION, exist_ok=True)
    with open(os.path.join(CONSTRUCTION, "version_info.txt"), "w", encoding="utf-8") as f:
        f.write(texte)


def pyinstaller():
    etape("Empaquetage de l'interface (PyInstaller)")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", DIST, "--workpath", os.path.join(CONSTRUCTION, "pyinstaller"),
                    os.path.join(RACINE, "packaging", "NewtonFractals.spec")], check=True)


# ---------- 3 et 4. Assemblage et installateur ----------

def assembler(moteur, dlls):
    etape("Assemblage de dist/NewtonFractals")
    dossier_moteur = os.path.join(APPLICATION, "moteur")
    os.makedirs(dossier_moteur, exist_ok=True)
    shutil.copy2(moteur, os.path.join(dossier_moteur, "moteur.exe"))
    for dll in dlls:
        shutil.copy2(dll, dossier_moteur)
        print("  DLL du moteur :", os.path.basename(dll))
    # le manuel (docs/manuel) utilise les captures de docs/images : même disposition une fois installé
    shutil.copytree(os.path.join(RACINE, "docs", "manuel"), os.path.join(APPLICATION, "manuel"), dirs_exist_ok=True)
    shutil.copytree(os.path.join(RACINE, "docs", "images"), os.path.join(APPLICATION, "images"), dirs_exist_ok=True)


def trouver_iscc():
    candidats = [shutil.which("iscc")] + [os.path.join(os.environ.get(v, ""), "Inno Setup 6", "ISCC.exe")
                                         for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    candidats += glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup*", "ISCC.exe"))
    return next((c for c in candidats if c and os.path.isfile(c)), None)


def installateur(v):
    iscc = trouver_iscc()
    if iscc is None:
        print("\nInno Setup introuvable : installateur non construit (https://jrsoftware.org/isinfo.php).")
        return None
    etape(f"Compilation de l'installateur ({iscc})")
    subprocess.run([iscc, f"/DVersion={v}", os.path.join(RACINE, "packaging", "installateur.iss")], check=True)
    return os.path.join(DIST, f"NewtonFractals-Setup-{v}.exe")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--moteur", help="moteur déjà compilé (main.exe) au lieu de le compiler avec g++")
    parser.add_argument("--sans-installateur", action="store_true", help="s'arrêter à dist/NewtonFractals")
    args = parser.parse_args()

    v = version()
    print(f"Newton Fractals {v}")
    moteur, dlls = preparer_moteur(args.moteur)
    ecrire_infos_version(v)
    pyinstaller()
    assembler(moteur, dlls)
    setup = None if args.sans_installateur else installateur(v)
    print(f"\nLogiciel : {APPLICATION}\\NewtonFractals.exe")
    if setup:
        print(f"Installateur : {setup}")


if __name__ == "__main__":
    main()
