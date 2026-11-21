"""Lecture et évaluation de fonctions mathématiques réelles, à la façon de GeoGebra.

    f(x) = sin(x) / x        y = x^2 - 3        2x sin(x)        exp(-x²)
    z = sin(x) cos(y)        f(x, y) = a (x² - y²)

Les variables sont x (et y pour une surface). Toute autre lettre (a, b, k…) est un
paramètre, réglable dans l'interface par un curseur. L'expression est analysée puis
évaluée avec numpy, sans jamais être exécutée comme du code Python.
"""
import ast
import re

import numpy as np

FONCTIONS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "arcsin": np.arcsin, "arccos": np.arccos, "arctan": np.arctan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "asinh": np.arcsinh, "acosh": np.arccosh, "atanh": np.arctanh,
    "exp": np.exp, "ln": np.log, "log": np.log10, "log10": np.log10, "log2": np.log2,
    "sqrt": np.sqrt, "racine": np.sqrt, "cbrt": np.cbrt,
    "abs": np.abs, "floor": np.floor, "ceil": np.ceil, "round": np.round,
    "sign": np.sign, "sgn": np.sign,
}
CONSTANTES = {"pi": np.pi, "e": np.e}
# Noms reconnus dans une suite de lettres, du plus long au plus court (« xsin » → x · sin)
_NOMS = sorted(list(FONCTIONS) + list(CONSTANTES), key=len, reverse=True)

_JETON = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)"   # nombre
                    r"|([A-Za-z][A-Za-z0-9]*)"                                        # lettres
                    r"|(\*\*|[-+*/^(),]))")                                           # opérateur
_REMPLACEMENTS = {"π": "pi", "²": "^2", "³": "^3", "×": "*", "·": "*", "−": "-", "÷": "/"}
# « f(x) = » ou « y = » (plan), « f(x, y) = » ou « z = » (espace) : définition d'une fonction
_PREFIXES = {lettre: re.compile(r"^\s*(?:([A-Za-z]\w*)\s*\(([A-Za-z\s,]*)\)|(" + lettre + r"))\s*=\s*")
             for lettre in "yz"}

EXEMPLES_2D = ["sin(x)", "x^2 + y^2 = 4", "x^2 - 3", "x^2/9 + y^2/4 = 1", "exp(-x^2)", "y^2 = x^3 - x",
               "a sin(b x)", "(x^2 + y^2)^2 = 8 x y", "1/x", "sin(x) = cos(y)", "sqrt(4 - x^2)",
               "x^2 - y^2 = 1", "ln(x)", "x = 2", "tan(x)", "sin(x)/x"]
EXEMPLES_3D = ["sin(x) cos(y)", "x^2 + y^2 + z^2 = 9", "x^2 - y^2", "(sqrt(x^2 + y^2) - 3)^2 + z^2 = 1",
               "exp(-(x^2 + y^2))", "x^2 + y^2 - z^2 = 1", "a sin(sqrt(x^2 + y^2))", "x^2/16 + y^2/4 + z^2 = 1",
               "cos(x y)", "x^2 + y^2 = 4", "cos(x) + cos(y) + cos(z) = 0", "x y / (1 + x^2 + y^2)",
               "x^2 + y^2 = z^2", "abs(x) + abs(y)"]


class Expression:
    """Fonction réelle lue depuis un texte. evaluer() prend un dictionnaire de valeurs
    (variables et paramètres, tableaux numpy ou nombres) et renvoie un tableau.

    Avec equations=True, un texte de la forme « gauche = droite » qui ne définit pas
    simplement la fonction (y = …, f(x) = … dans le plan ; z = …, f(x, y) = … dans l'espace)
    est une équation : en x et y dans le plan (courbe implicite, ex. le cercle x² + y² = 4),
    en x, y et z dans l'espace (surface implicite, ex. la sphère x² + y² + z² = 9).
    implicite vaut alors True et evaluer() renvoie gauche - droite : la courbe ou la surface
    est l'ensemble des points où cette valeur s'annule."""

    def __init__(self, texte, variables, equations=False):
        self.texte = texte
        dans_le_plan = len(variables) == 1
        lettre = "y" if dans_le_plan else "z"
        self.nom, corps, declarees = _separer_prefixe(texte, lettre)
        self.corps = " ".join(corps.split())
        self.implicite = "=" in corps
        if equations and not self.implicite and declarees == [lettre] and _contient_nom(corps, lettre):
            # « y = sin(x y) » : y figure des deux côtés, c'est une équation (comme dans GeoGebra)
            self.implicite, corps = True, f"{lettre} = {corps}"
        if self.implicite:
            if not equations:
                raise ValueError("un seul signe = est permis, au début (ex. z = …)")
            if corps.count("=") > 1:
                raise ValueError("une équation ne contient qu'un seul signe =")
            gauche, droite = corps.split("=")
            if not gauche.strip() or not droite.strip():
                raise ValueError("il manque un membre de l'équation (ex. "
                                 + ("x² + y² = 4)" if dans_le_plan else "x² + y² + z² = 9)"))
            self.nom = None
            self.variables = ("x", "y") if dans_le_plan else ("x", "y", "z")
            self.arbre, self.parametres = _analyser(f"({gauche}) - ({droite})", self.variables)
        else:
            self.variables = tuple(variables)
            if declarees in (None, [lettre]) or declarees == list(self.variables):
                self.arbre, self.parametres = _analyser(self.corps, self.variables, equations)
            else:
                self.arbre, self.parametres = _renommer_variables(self.corps, declarees, self.variables, self.nom)

    def evaluer(self, valeurs):
        with np.errstate(all="ignore"):
            resultat = _evaluer(self.arbre, valeurs)
            forme = np.broadcast(*[np.asarray(valeurs[v]) for v in self.variables]).shape
            resultat = np.broadcast_to(np.asarray(resultat, dtype=float), forme).astype(float)
        resultat[~np.isfinite(resultat)] = np.nan   # (division par zéro, racine d'un négatif…)
        return resultat


def _separer_prefixe(texte, lettre="y"):
    """« f(x) = … » ou « y = … » (lettre « z » dans l'espace) → (nom ou None, reste, variables déclarées).
    Les variables déclarées sont [lettre] pour « y = … », la liste entre parenthèses pour « f(t) = … »,
    None s'il n'y a pas de préfixe."""
    t = texte
    for a, b in _REMPLACEMENTS.items():
        t = t.replace(a, b)
    m = _PREFIXES[lettre].match(t)
    if not m or m.group(1) in FONCTIONS:   # « sin(x) = cos(y) » est une équation, pas une définition
        return None, t, None
    if m.group(3):
        return None, t[m.end():], [lettre]
    return m.group(1), t[m.end():], [v.strip() for v in m.group(2).split(",") if v.strip()]


def _contient_nom(texte, nom):
    try:
        return ("nom", nom) in _jetons(texte)
    except ValueError:
        return False


def _renommer_variables(corps, declarees, variables, nom):
    """« f(t) = t² » : la variable déclarée t est renommée x (x et y dans l'espace)."""
    attendu = ", ".join(variables)
    if len(declarees) != len(variables) or len(set(declarees)) != len(declarees)             or any(len(v) != 1 or v in CONSTANTES for v in declarees):
        raise ValueError(f"la fonction doit dépendre de {attendu} : {nom}({attendu}) = …")
    arbre, parametres = _analyser(corps, tuple(declarees))
    for v in variables:
        if v in parametres and v not in declarees:
            raise ValueError(f"{v} ne peut pas être un paramètre ici : écris {nom}({attendu}) = …")
    correspondance = dict(zip(declarees, variables, strict=True))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Name) and noeud.id in correspondance:
            noeud.id = correspondance[noeud.id]
    return arbre, parametres


def _jetons(texte):
    jetons, pos = [], 0
    while pos < len(texte):
        m = _JETON.match(texte, pos)
        if not m:
            reste = texte[pos:].strip()
            if not reste:
                break
            raise ValueError(f"caractère inattendu « {reste[0]} »")
        pos = m.end()
        nombre, lettres, operateur = m.groups()
        if nombre:
            jetons.append(("nombre", nombre))
        elif operateur:
            jetons.append(("op", "**" if operateur == "^" else operateur))
        else:
            # Découpe une suite de lettres en noms connus (sin, pi…) et en lettres seules (x, a…)
            seulement_lettres = re.sub(r"\d", "", lettres)
            if len(seulement_lettres) >= 3 and not any(n in lettres for n in _NOMS if len(n) >= 2):
                raise ValueError(f"nom inconnu : {lettres} (fonctions : sin, cos, tan, exp, ln, "
                                 f"log, sqrt, abs… ; pour un produit, sépare les lettres : a b c)")
            i = 0
            lettres_minuscules = lettres
            while i < len(lettres):
                nom = next((n for n in _NOMS if lettres_minuscules.startswith(n, i)), None)
                if nom is None:
                    if lettres[i].isdigit():
                        jetons.append(("nombre", lettres[i]))
                    else:
                        jetons.append(("nom", lettres[i]))
                    i += 1
                else:
                    jetons.append(("fonction" if nom in FONCTIONS else "nom", nom))
                    i += len(nom)
    return jetons


LONGUEUR_MAX = 500   # caractères par formule


def _analyser(texte, variables, equations=False):
    try:
        return _analyser_sans_garde(texte, variables, equations)
    except (RecursionError, MemoryError):
        # (une formule très imbriquée dépasse la pile de l'analyseur de Python)
        raise ValueError("formule trop complexe : simplifie-la ou découpe-la en plusieurs lignes") from None


def _analyser_sans_garde(texte, variables, equations):
    if not texte.strip():
        raise ValueError("rien n'est écrit")
    if len(texte) > LONGUEUR_MAX:
        raise ValueError(f"formule trop longue ({LONGUEUR_MAX} caractères au maximum)")
    jetons = _jetons(texte)
    morceaux = []
    for k, (genre, v) in enumerate(jetons):
        precedent = jetons[k - 1] if k else None
        # Multiplication implicite : 2x, x(x+1), (x-1)(x+1), 2sin(x), x y
        if precedent and (precedent[0] in ("nombre", "nom") or precedent[1] == ")") \
                and (genre in ("nombre", "nom", "fonction") or v == "("):
            morceaux.append("*")
        if genre == "fonction" and (k + 1 >= len(jetons) or jetons[k + 1][1] != "("):
            raise ValueError(f"il faut des parenthèses après {v} : {v}(…)")
        morceaux.append(v)
    try:
        arbre = ast.parse(" ".join(morceaux), mode="eval")
    except SyntaxError:
        raise ValueError("expression mal écrite") from None
    parametres = set()
    try:
        _verifier(arbre, variables, parametres)
    except ValueError as e:
        if equations and str(e).startswith("y n'est pas"):
            raise ValueError("y est permis dans une équation : écris-la avec =, ex. x² + y² = 4") from None
        if equations and str(e).startswith("z n'est pas"):
            raise ValueError("z est permis dans une équation : écris-la avec =, ex. x² + y² + z² = 9") from None
        raise
    return arbre, sorted(parametres)


def _verifier(noeud, variables, parametres):
    """Refuse tout ce qui n'est pas une expression mathématique, et note les paramètres."""
    if isinstance(noeud, ast.Expression):
        return _verifier(noeud.body, variables, parametres)
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)) and not isinstance(noeud.value, bool):
        return
    if isinstance(noeud, ast.Name):
        nom = noeud.id
        if nom in variables or nom in CONSTANTES:
            return
        if nom in ("x", "y", "z"):
            permis = " et ".join(variables)
            raise ValueError(f"{nom} n'est pas une variable ici (variables : {permis})")
        if len(nom) == 1:
            parametres.add(nom)
            return
        raise ValueError(f"nom inconnu : {nom}")
    if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
        return _verifier(noeud.operand, variables, parametres)
    if isinstance(noeud, ast.BinOp) and isinstance(noeud.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        _verifier(noeud.left, variables, parametres)
        return _verifier(noeud.right, variables, parametres)
    if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and noeud.func.id in FONCTIONS:
        if len(noeud.args) != 1 or noeud.keywords:
            raise ValueError(f"{noeud.func.id} prend un seul argument")
        return _verifier(noeud.args[0], variables, parametres)
    raise ValueError("expression non reconnue")


def _evaluer(noeud, valeurs):
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body, valeurs)
    if isinstance(noeud, ast.Constant):
        return float(noeud.value)
    if isinstance(noeud, ast.Name):
        if noeud.id in CONSTANTES and noeud.id not in valeurs:
            return CONSTANTES[noeud.id]
        return valeurs[noeud.id]
    if isinstance(noeud, ast.UnaryOp):
        v = _evaluer(noeud.operand, valeurs)
        return -v if isinstance(noeud.op, ast.USub) else v
    if isinstance(noeud, ast.Call):
        return FONCTIONS[noeud.func.id](_evaluer(noeud.args[0], valeurs))
    g, d = _evaluer(noeud.left, valeurs), _evaluer(noeud.right, valeurs)
    if isinstance(noeud.op, ast.Add):
        return g + d
    if isinstance(noeud.op, ast.Sub):
        return g - d
    if isinstance(noeud.op, ast.Mult):
        return g * d
    if isinstance(noeud.op, ast.Div):
        return np.divide(g, d)
    return np.power(np.asarray(g, dtype=float), d)


def lire(texte, variables, equations=False):
    """Raccourci : Expression(texte, variables, equations), ValueError avec un message clair si illisible."""
    return Expression(texte, variables, equations)


def vrai_zero(expression, valeurs_parametres, debut, fin, v0, v1, etapes=12):
    """F change de signe entre debut et fin (dictionnaires de coordonnées, tableaux) : vrai si
    c'est un zéro, faux si c'est un pôle (ex. tan(x) en π/2). On resserre l'intervalle par
    dichotomie en gardant le changement de signe : autour d'un zéro |F| devient minuscule,
    autour d'un pôle elle grandit (ou F devient indéfinie)."""
    debut = {v: np.array(c, dtype=float) for v, c in debut.items()}
    fin = {v: np.array(c, dtype=float) for v, c in fin.items()}
    v0, v1 = np.array(v0, dtype=float), np.array(v1, dtype=float)
    depart = np.maximum(np.abs(v0), np.abs(v1))
    for _ in range(etapes):
        milieu = {v: (debut[v] + fin[v]) / 2 for v in debut}
        vm = expression.evaluer(dict(valeurs_parametres, **milieu))
        cote_debut = (vm > 0) == (v0 > 0)                  # le changement de signe est dans [milieu, fin]
        for v in debut:
            debut[v] = np.where(cote_debut, milieu[v], debut[v])
            fin[v] = np.where(cote_debut, fin[v], milieu[v])
        v0, v1 = np.where(cote_debut, vm, v0), np.where(cote_debut, v1, vm)
    return np.maximum(np.abs(v0), np.abs(v1)) <= depart   # (NaN → faux)


def segments_implicites(expression, x0, x1, y0, y1, nx, ny, valeurs_parametres):
    """Courbe F(x, y) = 0 sur le rectangle donné, par la méthode des « carrés marchants » :
    on évalue F sur une grille nx × ny ; dans chaque case où F change de signe entre deux
    coins, la courbe coupe les côtés concernés, au point obtenu par interpolation linéaire.
    Renvoie un tableau (nombre de segments, 2 extrémités, 2 coordonnées)."""
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys)                                  # F[j, i] au point (xs[i], ys[j])
    F = expression.evaluer(dict(valeurs_parametres, x=X, y=Y))
    positif = F > 0
    # Cases où F change de signe entre deux coins (en général environ 1 % des cases) :
    # tout le reste du calcul ne porte que sur elles
    pa, pb, pc, pd = positif[:-1, :-1], positif[:-1, 1:], positif[1:, 1:], positif[1:, :-1]
    j, i = np.nonzero((pa != pb) | (pb != pc) | (pc != pd))
    if not j.size:
        return np.zeros((0, 2, 2))
    a, b, c, d = F[j, i], F[j, i + 1], F[j + 1, i + 1], F[j + 1, i]   # bas-g., bas-d., haut-d., haut-g.
    pa, pb, pc, pd = a > 0, b > 0, c > 0, d > 0
    C = expression.evaluer(dict(valeurs_parametres, x=(xs[i] + xs[i + 1]) / 2, y=(ys[j] + ys[j + 1]) / 2))
    # Une case qui « traverse » un pôle (ex. 1/x) change de signe sans contenir la courbe :
    # la valeur au centre y est alors bien plus grande que celles des coins.
    with np.errstate(all="ignore"):
        grand = np.max(np.abs(np.stack([a, b, c, d])), axis=0)
    valides = np.isfinite(a) & np.isfinite(b) & np.isfinite(c) & np.isfinite(d) & np.isfinite(C)
    valides &= np.abs(np.nan_to_num(C)) <= 2 * np.nan_to_num(grand) + 1e-300
    croise = np.stack([pa != pb, pb != pc, pd != pc, pa != pd]) & valides   # côtés : bas, droit, haut, gauche

    xg, xd, yb, yh = xs[i], xs[i + 1], ys[j], ys[j + 1]

    def interp(v0, v1, p0, p1):
        with np.errstate(all="ignore"):
            t = np.clip(v0 / (v0 - v1), 0, 1)
        return p0 + np.nan_to_num(t) * (p1 - p0)

    points = np.stack([
        np.stack([interp(a, b, xg, xd), yb], axis=-1),   # bas
        np.stack([xd, interp(b, c, yb, yh)], axis=-1),   # droit
        np.stack([interp(d, c, xg, xd), yh], axis=-1),   # haut
        np.stack([xg, interp(a, d, yb, yh)], axis=-1),   # gauche
    ])                                                   # (4, cases, 2)
    # Un côté « coupé » à travers un pôle (ex. tan(x) = 0 en x = π/2) n'est pas la courbe
    k = np.nonzero(croise.any(axis=0))[0]
    if k.size:
        extremites = [((xg, yb), (xd, yb), a, b), ((xd, yb), (xd, yh), b, c),
                      ((xg, yh), (xd, yh), d, c), ((xg, yb), (xg, yh), a, d)]
        for cote, ((x_0, y_0), (x_1, y_1), v0, v1) in enumerate(extremites):
            sur_cote = k[croise[cote, k]]
            if sur_cote.size:
                croise[cote, sur_cote] = vrai_zero(
                    expression, valeurs_parametres, {"x": x_0[sur_cote], "y": y_0[sur_cote]},
                    {"x": x_1[sur_cote], "y": y_1[sur_cote]}, v0[sur_cote], v1[sur_cote])
    nombre = croise.sum(axis=0)
    segments = []

    # Cases traversées une fois : un segment entre les deux côtés coupés
    k = np.nonzero(nombre == 2)[0]
    if k.size:
        cotes = np.argsort(~croise[:, k], axis=0, kind="stable")[:2]       # indices des 2 côtés coupés
        segments.append(np.stack([points[cotes[0], k], points[cotes[1], k]], axis=1))

    # Cases « selle » (coins de signes alternés) : deux segments, choisis selon le signe au centre
    k = np.nonzero(nombre == 4)[0]
    if k.size:
        centre_comme_a = (C[k] > 0) == pa[k]
        # centre du signe de a et c : les coins b et d sont isolés → (bas, droit) et (haut, gauche)
        # sinon a et c sont isolés → (bas, gauche) et (droit, haut)
        premier = np.where(centre_comme_a, 1, 3)
        second = np.where(centre_comme_a, 3, 1)
        segments.append(np.stack([points[0, k], points[premier, k]], axis=1))
        segments.append(np.stack([points[2, k], points[second, k]], axis=1))
    return np.concatenate(segments) if segments else np.zeros((0, 2, 2))


def echantillonner_courbe(expression, x0, x1, hauteur_vue, valeurs_parametres, n=2000):
    """Points (x, y) d'une courbe y = f(x) sur [x0, x1]. Les discontinuités (asymptotes de tan
    ou de 1/x, sauts de floor…) sont coupées par un NaN au lieu d'être reliées par un trait."""
    x = np.linspace(x0, x1, n)
    y = expression.evaluer(dict(valeurs_parametres, x=x))
    seuil = 0.02 * max(hauteur_vue, 1e-300)
    candidats = np.nonzero(np.abs(np.diff(y)) > seuil)[0]
    if candidats.size:
        coupures = candidats[_discontinu(expression, valeurs_parametres, x[candidats], x[candidats + 1],
                                         y[candidats], y[candidats + 1], seuil)]
        if coupures.size:
            y = y.copy()
            y[coupures] = np.nan   # on coupe la ligne au point avant le saut
    return x, y


def _discontinu(expression, valeurs_parametres, xa, xb, ya, yb, seuil, etapes=24):
    """Pour chaque intervalle [xa, xb] où f varie beaucoup : vrai si f y est discontinue.
    On coupe l'intervalle en deux, encore et encore, en gardant la moitié où f varie le plus :
    pour une fonction continue, la variation devient minuscule ; pour une asymptote ou un saut,
    elle reste grande (ou f devient indéfinie)."""
    xa, xb, ya, yb = (np.array(v, dtype=float) for v in (xa, xb, ya, yb))
    for _ in range(etapes):
        xm = (xa + xb) / 2
        ym = expression.evaluer(dict(valeurs_parametres, x=xm))
        with np.errstate(invalid="ignore"):
            gauche = np.nan_to_num(np.abs(ym - ya), nan=np.inf) >= np.nan_to_num(np.abs(yb - ym), nan=np.inf)
        xb, yb = np.where(gauche, xm, xb), np.where(gauche, ym, yb)
        xa, ya = np.where(gauche, xa, xm), np.where(gauche, ya, ym)
    return ~(np.abs(yb - ya) <= seuil)   # (NaN : indéfinie dans l'intervalle → coupée)
