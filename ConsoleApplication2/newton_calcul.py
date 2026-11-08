"""Logique de la fractale de Newton, sans interface graphique.

Lecture des polynômes et des racines, formatage des nombres, paramètres mémorisés,
recherche et options du programme C++, lecture de ses résultats (texte ou binaire).
Utilisé par l'interface Qt (NewtonFractalsDrawing.py).
"""
import ast
import json
import os
import re
import shutil

import numpy as np

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_RESULTATS = os.path.join(DOSSIER, "results.txt")      # produit par main.exe lancé seul
FICHIER_BINAIRE = os.path.join(DOSSIER, "results.bin")        # produit pour l'interface (rapide)
FICHIER_PARAMETRES = os.path.join(DOSSIER, "parametres.json")   # mémorise le dernier calcul

# mode : "polynome" (on saisit p(z)) ou "racines" (on saisit les racines, p(z) = ∏(z - r))
DEFAUTS = {"mode": "polynome", "polynome": "z^3 - 2z + 2", "racines_texte": "",
           "largeur": 1000, "hauteur": 1000, "min_x": -2.0, "max_x": 2.0,
           "min_y": -2.0, "max_y": 2.0, "eps": 1e-6, "iterations": 50}
EXEMPLES = {"polynome": ["z^3 - 2z + 2", "z^3 - 1", "z^4 - 1", "z^5 - 1", "z^6 + z^3 - 1",
                         "z^8 + 15z^4 - 16", "(z^2 + 1)(z^2 - 4)", "z^3 - (1 + 2i)z + 1"],
            "racines": ["1 ; -1 ; i ; -i", "0 ; 1 ; 2", "1 ; -0.5+0.866i ; -0.5-0.866i",
                        "1+i ; 1-i ; -2 ; 0.5i", "-1 ; 1 ; 1.5i ; -1.5i ; 0", "1 ; 1 ; -1",
                        "2 ; 2i ; -2 ; -2i ; 0.3+0.3i"]}
LIBELLES_MODE = {"polynome": "p(z) =   (ex. z^3 - 2z + 2,  (z-1)(z+i),  z^5 - 1)",
                 "racines": "Racines, séparées par « ; »   (ex. 1 ; -1 ; 0.5+2i)"}
DEGRE_MAX = 20


# --- Couleurs -------------------------------------------------------------
COULEURS_RACINES = ["#4cc9f0", "#f72585", "#ffd166", "#06d6a0", "#9d7dff", "#ff8c42",
                    "#ef476f", "#118ab2", "#caffbf", "#ffadad", "#a0c4ff", "#fdffb6"]
COULEUR_NON_CONVERGENCE = "#262a36"


# --- Données ----------------------------------------------------------------
def lire_resultats(chemin):
    """Renvoie le tableau des indices de racine, une ligne par valeur de y."""
    with open(chemin) as f:
        lignes = [ligne for ligne in f.read().splitlines() if ligne.strip()]
    tableau = np.array(" ".join(lignes).split(), dtype=np.int16).reshape(len(lignes), -1)
    return tableau.T  # results.txt contient une ligne par valeur de x


def lire_binaire(chemin):
    """Lit results.bin (écrit par main.exe --binaire) ; même convention que lire_resultats.
    Format : dim_x et dim_y en int32 little-endian, puis un int8 par pixel, ligne par ligne selon x."""
    with open(chemin, "rb") as f:
        dim_x, dim_y = np.frombuffer(f.read(8), dtype="<i4")
        tableau = np.frombuffer(f.read(), dtype=np.int8)
    if tableau.size != dim_x * dim_y:
        raise ValueError(f"fichier incomplet ({tableau.size} pixels au lieu de {dim_x * dim_y})")
    return tableau.reshape(dim_x, dim_y).T


def lire_fichier_resultat(chemin):
    return lire_binaire(chemin) if chemin.endswith(".bin") else lire_resultats(chemin)


# --- Polynôme ---------------------------------------------------------------
_JETON = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)"   # nombre
                    r"|([zZxX])"                                                      # variable
                    r"|([iIjJ])"                                                      # unité imaginaire
                    r"|(\*\*|[-+*/^()]))")                                            # opérateur


def _evaluer(noeud):
    """Évalue l'expression en polynôme, sans eval : seuls nombres, z, + - * / et puissances entières."""
    P = np.polynomial.Polynomial
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body)
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float, complex)) \
            and not isinstance(noeud.value, bool):
        return P([noeud.value])
    if isinstance(noeud, ast.Name) and noeud.id == "z":
        return P([0, 1])
    if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
        v = _evaluer(noeud.operand)
        return -v if isinstance(noeud.op, ast.USub) else v
    if isinstance(noeud, ast.BinOp):
        g, d = _evaluer(noeud.left), _evaluer(noeud.right)
        if isinstance(noeud.op, ast.Add):
            return g + d
        if isinstance(noeud.op, ast.Sub):
            return g - d
        if isinstance(noeud.op, ast.Mult):
            return g * d
        constante = d.trim().degree() == 0
        if isinstance(noeud.op, ast.Div):
            if not constante or d.coef[0] == 0:
                raise ValueError("Polynôme : on ne peut diviser que par un nombre non nul")
            return g / d.coef[0]
        if isinstance(noeud.op, ast.Pow):
            e = d.coef[0]
            if not constante or np.imag(e) != 0 or np.real(e) != int(np.real(e)) or not 0 <= np.real(e) <= DEGRE_MAX:
                raise ValueError(f"Polynôme : exposant entier entre 0 et {DEGRE_MAX} attendu")
            return g ** int(np.real(e))
    raise ValueError("Polynôme : expression non reconnue")


def _vers_polynome(texte, contexte="Polynôme"):
    """Expression → objet Polynomial de numpy (lève ValueError avec un message clair)."""
    s = texte.strip()
    if not s:
        raise ValueError(f"{contexte} : rien n'est écrit")
    jetons, pos = [], 0
    while pos < len(s):
        m = _JETON.match(s, pos)
        if not m:
            reste = s[pos:].strip()
            if not reste:
                break
            raise ValueError(f"{contexte} : caractère inattendu « {reste[0]} »")
        pos = m.end()
        nombre, variable, imaginaire, operateur = m.groups()
        if nombre:
            jetons.append(("valeur", nombre))
        elif variable:
            jetons.append(("valeur", "z"))
        elif imaginaire:
            jetons.append(("valeur", "1j"))
        else:
            jetons.append(("op", "**" if operateur == "^" else operateur))
    # Multiplication implicite : entre une valeur ou « ) » et une valeur ou « ( »
    morceaux = []
    for k, (genre, v) in enumerate(jetons):
        if k and (genre == "valeur" or v == "(") and (jetons[k - 1][0] == "valeur" or jetons[k - 1][1] == ")"):
            morceaux.append("*")
        morceaux.append(v)
    try:
        arbre = ast.parse(" ".join(morceaux), mode="eval")
    except SyntaxError:
        raise ValueError(f"{contexte} : expression mal écrite") from None
    try:
        return _evaluer(arbre).trim()
    except ValueError as e:
        raise ValueError(str(e).replace("Polynôme", contexte, 1)) from None


def grouper_racines(valeurs):
    """Regroupe les valeurs presque égales (racine multiple) → [(valeur, multiplicité)], triées.
    np.roots éparpille une racine multiple (≈1e-5 pour une racine triple), d'où la tolérance."""
    groupes = []
    for r in valeurs:
        r = complex(r)
        for g in groupes:
            if abs(g[0] - r) <= 2e-4 * max(1, abs(r)):
                g.append(r)
                break
        else:
            groupes.append([r])
    resultat = []
    for g in groupes:
        v = complex(np.mean(g))
        if abs(v.imag) <= 1e-12 * max(1, abs(v)):
            v = complex(v.real, 0)
        if abs(v.real) <= 1e-12 * max(1, abs(v)):
            v = complex(0, v.imag)
        resultat.append((v, len(g)))
    resultat.sort(key=lambda vm: (round(vm[0].real, 9), round(vm[0].imag, 9)))
    return resultat


def nettoyer(coefs, tolerance=1e-13):
    """Met à zéro les parties réelles / imaginaires négligeables (bruit de calcul)."""
    c = np.array(coefs, dtype=complex)
    m = max(np.abs(c).max(), 1e-300)
    re_, im_ = c.real.copy(), c.imag.copy()
    re_[np.abs(re_) < tolerance * m] = 0
    im_[np.abs(im_) < tolerance * m] = 0
    return re_ + 1j * im_


def lire_polynome(texte):
    """« z^3 - 2z + 2 » → (coefficients du plus haut degré au terme constant, racines distinctes triées).

    Accepte : nombres (2, 0.5, 1e-3), z (ou x), i (unité imaginaire), + - * / ^ (ou **),
    parenthèses, et la multiplication implicite (2z, 3i, z(z+1), (z-1)(z+1))."""
    poly = _vers_polynome(texte)
    degre = poly.degree()
    if degre < 1:
        raise ValueError("Le polynôme doit être de degré 1 au moins (il faut un z)")
    if degre > DEGRE_MAX:
        raise ValueError(f"Degré {degre} trop grand ({DEGRE_MAX} au maximum)")
    coefs = np.asarray(poly.coef, dtype=complex)[::-1]
    return coefs, [v for v, _ in grouper_racines(np.roots(coefs))]


def lire_racines(texte):
    """« 1 ; -1 ; 0.5+2i » (ou « 1, -1, 2i ») → liste des racines, répétitions comprises.

    Séparateur « ; » (la virgule peut alors servir de virgule décimale) ou « , ».
    Chaque racine peut être une petite expression : 1+i, 1/3, (1+i)/2."""
    s = texte.strip()
    if not s:
        raise ValueError("Racines : rien n'est écrit")
    morceaux = [m.replace(",", ".") for m in s.split(";")] if ";" in s else s.split(",")
    racines = []
    for k, m in enumerate(morceaux, 1):
        if not m.strip():
            raise ValueError(f"Racine {k} : vide (séparateur en trop ?)")
        valeur = _vers_polynome(m, f"Racine {k}")
        if valeur.degree() > 0:
            raise ValueError(f"Racine {k} : z n'a pas sa place ici, il faut un nombre")
        racines.append(complex(valeur.coef[0]))
    if len(racines) > DEGRE_MAX:
        raise ValueError(f"{len(racines)} racines : {DEGRE_MAX} au maximum")
    return racines


def depuis_racines(racines):
    """Racines (répétitions comprises) → (coefficients de ∏(z - r), racines distinctes triées)."""
    return nettoyer(np.poly(racines)), [v for v, _ in grouper_racines(racines)]


def texte_racines(coefs):
    """Racines d'un polynôme, écrites pour le champ « Racines » (multiplicités répétées)."""
    morceaux = []
    for v, m in grouper_racines(np.roots(coefs)):
        morceaux += [texte_complexe(v, 10)] * m
    return " ; ".join(morceaux)


def texte_polynome(coefs, chiffres=9):
    """Coefficients (du plus haut degré au terme constant) → « z^3 - 2z + 2 ».
    Ce qui est négligeable devant le plus grand coefficient (< 1e-9) est mis à zéro et
    l'affichage garde 9 chiffres : on efface ainsi le bruit d'arrondi (ex. 2e-10 z^2,
    0.9999999998 z^3 après un passage par les racines)."""
    coefs = nettoyer(coefs, tolerance=1e-9)
    degre = len(coefs) - 1
    termes = []
    for k, c in enumerate(coefs):
        puissance = degre - k
        if c == 0:
            continue
        monome = "" if puissance == 0 else ("z" if puissance == 1 else f"z^{puissance}")
        if c.imag != 0 and c.real != 0:          # coefficient vraiment complexe : entre parenthèses
            signe, corps = "+", f"({texte_complexe(c, chiffres)})" + monome
        else:
            v = c.real if c.imag == 0 else c.imag
            signe = "-" if v < 0 else "+"
            nombre = f"{abs(v):.{chiffres}g}"
            suffixe_i = "" if c.imag == 0 else "i"
            if nombre == "1" and monome and not suffixe_i:
                nombre = ""
            corps = f"{nombre}{suffixe_i}{monome}"
        termes.append((signe, corps))
    if not termes:
        return "0"
    texte = ("-" if termes[0][0] == "-" else "") + termes[0][1]
    for signe, corps in termes[1:]:
        texte += f" {signe} {corps}"
    return texte


def texte_complexe(z, chiffres=3):
    """0.885-0.59i, -1.77, 2i"""
    re_, im_ = z.real, z.imag
    if im_ == 0:
        return f"{re_:.{chiffres}g}"
    im_txt = "" if abs(abs(im_) - 1) < 1e-12 else f"{abs(im_):.{chiffres}g}"
    if abs(re_) < 1e-12 * max(1, abs(z)):
        return f"{'-' if im_ < 0 else ''}{im_txt}i"
    return f"{re_:.{chiffres}g}{'-' if im_ < 0 else '+'}{im_txt}i"


def charger_parametres(fichier=None):
    try:
        with open(fichier or FICHIER_PARAMETRES) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sauvegarder_parametres(p, fichier_resultat, fichier=None):
    """Mémorise les paramètres du dernier calcul, et quel fichier de résultat leur correspond."""
    try:
        memo = {k: v for k, v in p.items() if k not in ("coefs", "racines")}
        memo.update(fichier=os.path.basename(fichier_resultat),
                    fichier_date=os.path.getmtime(fichier_resultat))
        with open(fichier or FICHIER_PARAMETRES, "w") as f:
            json.dump(memo, f, indent=2)
    except OSError:
        pass


def resultat_memorise(memo, lire):
    """Relit le résultat du dernier calcul mémorisé, s'il n'a pas changé depuis ; sinon None."""
    if not memo or not memo.get("fichier"):
        return None
    chemin = os.path.join(DOSSIER, memo["fichier"])
    if not os.path.isfile(chemin) or abs(os.path.getmtime(chemin) - memo.get("fichier_date", -1)) >= 1e-3:
        return None
    try:
        return lire(chemin)
    except (OSError, ValueError):
        return None


def arguments_calcul(p, fichier_binaire):
    """Options de main.exe pour les paramètres p (qui contiennent coefs et racines)."""
    args = ["--taille", str(p["largeur"]), str(p["hauteur"]),
            "--bornes", repr(p["min_x"]), repr(p["max_x"]), repr(p["min_y"]), repr(p["max_y"]),
            "--eps", repr(p["eps"]), "--iterations", str(p["iterations"]),
            "--binaire", fichier_binaire]
    for option, valeurs in (("--coefs", p["coefs"]), ("--racines", p["racines"])):
        args += [option, str(len(valeurs))]
        for v in valeurs:
            args += [repr(float(v.real)), repr(float(v.imag))]
    return args


def verifier_parametres(p):
    """Vérifie les valeurs numériques (fractale de Newton) ; lève ValueError avec un message clair."""
    verifier_fenetre(p)
    if p["eps"] <= 0:
        raise ValueError("La précision doit être positive")
    if not 1 <= p["iterations"] <= 1_000_000:
        raise ValueError("Itérations : entre 1 et 1 000 000")


def verifier_fenetre(p):
    """Vérifie la taille de l'image et la zone du plan complexe (communes à toutes les fractales)."""
    if not (1 <= p["largeur"] <= 20000 and 1 <= p["hauteur"] <= 20000):
        raise ValueError("La taille doit être entre 1 et 20000 pixels")
    if p["largeur"] * p["hauteur"] > 50_000_000:
        raise ValueError("Image trop grande (50 millions de pixels max)")
    if p["min_x"] >= p["max_x"] or p["min_y"] >= p["max_y"]:
        raise ValueError("Il faut min < max pour Re et pour Im")
    if ecart_trop_petit(p["min_x"], p["max_x"]) or ecart_trop_petit(p["min_y"], p["max_y"]):
        raise ValueError("Zoom trop profond : la précision des nombres (double, ~16 chiffres) "
                         "ne permet plus de distinguer les pixels")


def trouver_executable(chemin=None):
    """Cherche le programme C++ compilé (makefile ou Visual Studio) ; prend le plus récent."""
    if chemin:
        return os.path.abspath(chemin) if os.path.isfile(chemin) else None
    candidats = ["main.exe", "main",
                 os.path.join("..", "x64", "Release", "ConsoleApplication2.exe"),
                 os.path.join("x64", "Release", "ConsoleApplication2.exe"),
                 os.path.join("..", "Release", "ConsoleApplication2.exe"),
                 os.path.join("..", "x64", "Debug", "ConsoleApplication2.exe"),
                 os.path.join("..", "Debug", "ConsoleApplication2.exe")]
    trouves = [os.path.join(DOSSIER, c) for c in candidats if os.path.isfile(os.path.join(DOSSIER, c))]
    return max(trouves, key=os.path.getmtime) if trouves else None


def environnement_calcul():
    """Ajoute au PATH le dossier des DLL de MinGW (OpenMP), si on le trouve."""
    env = dict(os.environ)
    dossiers = [os.path.dirname(shutil.which("g++") or ""), r"C:\msys64\ucrt64\bin"]
    for d in dossiers:
        if d and os.path.isdir(d):
            env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env


def hex_vers_rgb(couleur):
    return [int(couleur[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def table_couleurs():
    """Table de 256 couleurs RGB (uint8) : case 0 = pas de convergence, case k = racine k."""
    table = np.zeros((256, 3), dtype=np.uint8)
    table[0] = np.round(np.array(hex_vers_rgb(COULEUR_NON_CONVERGENCE)) * 255)
    for k in range(1, 256):
        table[k] = np.round(np.array(hex_vers_rgb(COULEURS_RACINES[(k - 1) % len(COULEURS_RACINES)])) * 255)
    return table


def image_rgb(indices):
    """Indices (une ligne par y, y croissant) → image RGB uint8 (une ligne par y, y décroissant)."""
    return table_couleurs()[np.clip(indices, 0, 255)][::-1]


def preparer(args):
    """Paramètres de départ, et résultat déjà calculé à afficher s'il en existe un fiable.
    Renvoie (paramètres, indices ou None)."""
    p = dict(DEFAUTS)
    memo = charger_parametres()
    if memo:
        p.update({k: memo[k] for k in DEFAUTS if k in memo})

    indices = None
    if getattr(args, "bornes", None):
        # Lancé par main.exe : on connaît la zone de results.txt
        p["min_x"], p["max_x"], p["min_y"], p["max_y"] = args.bornes
        if args.eps is not None:
            p["eps"] = args.eps
        if args.iterations is not None:
            p["iterations"] = args.iterations
        if args.polynome:
            p["mode"], p["polynome"] = "polynome", args.polynome
        if os.path.isfile(args.fichier):
            indices = lire_fichier_resultat(args.fichier)
    else:
        # Dernier calcul de l'interface, si son fichier n'a pas changé depuis
        indices = resultat_memorise(memo, lire_fichier_resultat)
    if indices is not None:
        p["hauteur"], p["largeur"] = indices.shape
    return p, indices


# --- Nombres en écriture scientifique -------------------------------------------
# Un double a ~16 chiffres significatifs : en dessous de cet écart relatif entre
# min et max, les pixels ne sont plus distinguables et le calcul n'a plus de sens.
ECART_RELATIF_MIN = 1e-12


def nombre_sci(v, chiffres=17):
    """Écriture scientifique compacte : 1.25e-10, -2e0, 3.0517578125e-5."""
    if v == 0:
        return "0"
    mantisse, exposant = f"{v:.{chiffres - 1}e}".split("e")
    if "." in mantisse:
        mantisse = mantisse.rstrip("0").rstrip(".")
    return f"{mantisse}e{int(exposant)}"


def intervalle_sci(a, b, precision=1e-6):
    """Écrit a et b avec le moins de chiffres possible, mais assez pour que
    a < b reste vrai et que l'écart b - a soit juste (à 1e-6 près en relatif).
    Au pire on utilise 17 chiffres, ce qui conserve le double exactement."""
    for n in range(4, 18):
        ta, tb = nombre_sci(a, n), nombre_sci(b, n)
        ra, rb = float(ta), float(tb)
        ecart = b - a
        # écart juste ET bornes à leur place (sinon la vue glisse à chaque recalcul)
        if rb > ra and abs((rb - ra) - ecart) <= precision * ecart \
                and abs(ra - a) <= precision * ecart and abs(rb - b) <= precision * ecart:
            return ta, tb
    return nombre_sci(a, 17), nombre_sci(b, 17)


def ecart_trop_petit(a, b):
    return (b - a) <= ECART_RELATIF_MIN * max(abs(a), abs(b), 1e-300)


def coordonnee(v, ecart):
    """Valeur avec juste assez de chiffres pour être lisible à l'échelle « ecart »."""
    if v == 0 or ecart <= 0:
        return nombre_sci(v, 6)
    chiffres = int(np.ceil(np.log10(abs(v) / ecart))) + 2 if abs(v) > ecart else 4
    return nombre_sci(v, min(max(chiffres, 4), 17))


def sous_titre(p):
    taille = f"{p['largeur']} × {p['hauteur']} px"
    re_min, re_max = intervalle_sci(p["min_x"], p["max_x"], 1e-3)
    im_min, im_max = intervalle_sci(p["min_y"], p["max_y"], 1e-3)
    texte = f"{taille}   ·   Re ∈ [{re_min}, {re_max}]   ·   Im ∈ [{im_min}, {im_max}]"
    if len(texte) <= 80:
        return texte
    # Zoom profond : centre et largeur de la vue, plus lisibles que deux bornes presque égales
    lx, ly = p["max_x"] - p["min_x"], p["max_y"] - p["min_y"]
    cx, cy = (p["min_x"] + p["max_x"]) / 2, (p["min_y"] + p["max_y"]) / 2
    centre = f"{coordonnee(cx, lx / 1000)} {'+' if cy >= 0 else '-'} {coordonnee(abs(cy), ly / 1000)}i"
    return f"{taille}   ·   centre {centre}   ·   largeur {nombre_sci(lx, 3)} × {nombre_sci(ly, 3)}"


def polynome_de(p):
    """(coefficients, racines distinctes) du polynôme des paramètres, selon le mode de saisie."""
    if p.get("mode") == "racines":
        return depuis_racines(lire_racines(p.get("racines_texte", "")))
    return lire_polynome(p.get("polynome", DEFAUTS["polynome"]))


def racines_de(p):
    """Racines du polynôme des paramètres, ou None s'il est illisible."""
    try:
        return polynome_de(p)[1]
    except ValueError:
        return None


def titre_polynome(p, longueur_max=95):
    """« p(z) = z^3 - 2z + 2 », ou en mode racines la forme factorisée « p(z) = (z - 1)(z + i) »."""
    if p.get("mode") == "racines":
        try:
            facteurs = []
            for v, m in grouper_racines(lire_racines(p.get("racines_texte", ""))):
                if v == 0:
                    f = "z"
                elif v.imag == 0:
                    f = f"(z {'-' if v.real > 0 else '+'} {abs(v.real):.4g})"
                elif v.real == 0:
                    f = f"(z {'-' if v.imag > 0 else '+'} {texte_complexe(complex(0, abs(v.imag)), 4)})"
                else:
                    f = f"(z - ({texte_complexe(v, 4)}))"
                facteurs.append(f + (f"^{m}" if m > 1 else ""))
            texte = "p(z) = " + "".join(facteurs)
        except ValueError:
            texte = "racines : " + p.get("racines_texte", "")
    else:
        texte = "p(z) = " + p.get("polynome", DEFAUTS["polynome"])
    return texte if len(texte) <= longueur_max else texte[:longueur_max - 1] + "…"




# --- Champs du panneau --------------------------------------------------------
CHAMPS_FENETRE = [  # (clé, libellé, type) : champs communs à toutes les fractales
    ("largeur", "Largeur (px)", int), ("hauteur", "Hauteur (px)", int),
    ("min_x", "Re min", float), ("max_x", "Re max", float),
    ("min_y", "Im min", float), ("max_y", "Im max", float),
]
CHAMPS = CHAMPS_FENETRE + [  # champs numériques de la fractale de Newton
    ("eps", "Précision (eps)", float), ("iterations", "Itérations max", int),
]


def textes_champs(valeurs):
    """Texte de chaque champ. Les bornes sont écrites par paires (min, max) en écriture
    scientifique, avec assez de chiffres pour rester distinctes ; le champ « polynome »
    contient p(z) ou la liste des racines, selon le mode."""
    t = {}
    for cle, v in valeurs.items():
        if cle == "polynome":
            t[cle] = str(valeurs.get("racines_texte", "") if valeurs.get("mode") == "racines" else v)
        elif cle in ("largeur", "hauteur", "iterations"):
            t[cle] = str(int(v))
        elif cle == "eps":
            t[cle] = nombre_sci(v, 6)
    for a, b in (("min_x", "max_x"), ("min_y", "max_y")):
        if a in valeurs and b in valeurs:
            t[a], t[b] = intervalle_sci(valeurs[a], valeurs[b])
        else:
            for c in (a, b):
                if c in valeurs:
                    t[c] = nombre_sci(valeurs[c])
    return t


def lire_saisie_polynome(texte, mode):
    """Lit le champ polynôme selon le mode. Renvoie les deux écritures (p(z) et racines),
    les coefficients et les racines distinctes ; lève ValueError si illisible."""
    texte = " ".join(texte.split())
    if mode == "racines":
        coefs, racines = depuis_racines(lire_racines(texte))
        return {"mode": "racines", "racines_texte": texte, "polynome": texte_polynome(coefs),
                "coefs": coefs, "racines": racines}
    coefs, racines = lire_polynome(texte)
    return {"mode": "polynome", "polynome": texte, "racines_texte": texte_racines(coefs),
            "coefs": coefs, "racines": racines}


def lire_nombres(textes, champs=None):
    """{clé: texte} des champs numériques → {clé: valeur} ; lève ValueError si un champ est invalide."""
    p = {}
    for cle, libelle, type_ in champs or CHAMPS:
        texte = textes[cle].strip().replace(",", ".")
        try:
            p[cle] = type_(float(texte)) if type_ is int else float(texte)
        except ValueError:
            raise ValueError(f"« {libelle} » : nombre invalide") from None
    return p


def etiquette_axe(v, ecart):
    """Graduation lisible : 0.25, -1.5 à l'échelle normale, écriture scientifique en zoom profond."""
    if ecart >= 1e-4 and abs(v) < 1e4:
        # Assez de décimales pour écrire le pas exactement (0.25 → 2, 0.5 → 1, 2 → 0)
        decimales = next((d for d in range(0, 8)
                          if abs(ecart * 10 ** d - round(ecart * 10 ** d)) < 1e-6 * max(1, ecart * 10 ** d)), 8)
        texte = f"{v:.{decimales}f}"
        return "0" if float(texte) == 0 else texte
    return coordonnee(v, ecart)


def calcul_apercu(largeur=320, hauteur=200, iterations=40):
    """Petit calcul numpy de la fractale de z^5 - 1, sans le moteur C++ (aperçu de la page d'accueil).
    Renvoie les indices de racine, une ligne par y (même convention que lire_resultats)."""
    x = np.linspace(-1.6, 1.6, largeur)
    y = np.linspace(-1.6 * hauteur / largeur, 1.6 * hauteur / largeur, hauteur)
    z = x[None, :] + 1j * y[:, None]
    racines = np.exp(2j * np.pi * np.arange(5) / 5)
    with np.errstate(all="ignore"):
        for _ in range(iterations):
            z = z - (z ** 5 - 1) / (5 * z ** 4)
    distances = np.abs(z[..., None] - racines)
    indices = distances.argmin(-1) + 1
    indices[~(distances.min(-1) < 0.1)] = -1
    return indices
