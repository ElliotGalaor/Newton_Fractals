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
_PREFIXE = re.compile(r"^\s*(?:([A-Za-z]\w*)\s*\(\s*[A-Za-z\s,]*\)|([yz]))\s*=\s*")

EXEMPLES_2D = ["sin(x)", "x^2 - 3", "exp(-x^2)", "a sin(b x)", "1/x", "sqrt(4 - x^2)",
               "ln(x)", "abs(x) - 2", "x^3 - 3x", "tan(x)", "sin(x)/x", "floor(x)"]
EXEMPLES_3D = ["sin(x) cos(y)", "x^2 - y^2", "exp(-(x^2 + y^2))", "a sin(sqrt(x^2 + y^2))",
               "cos(x y)", "x y / (1 + x^2 + y^2)", "sin(x) + cos(y)", "abs(x) + abs(y)"]


class Expression:
    """Fonction réelle lue depuis un texte. evaluer() prend un dictionnaire de valeurs
    (variables et paramètres, tableaux numpy ou nombres) et renvoie un tableau."""

    def __init__(self, texte, variables):
        self.texte = texte
        self.variables = tuple(variables)
        self.nom, corps = _separer_prefixe(texte)
        self.corps = corps.strip()
        self.arbre, self.parametres = _analyser(self.corps, self.variables)

    def evaluer(self, valeurs):
        with np.errstate(all="ignore"):
            resultat = _evaluer(self.arbre, valeurs)
            forme = np.broadcast(*[np.asarray(valeurs[v]) for v in self.variables]).shape
            resultat = np.broadcast_to(np.asarray(resultat, dtype=float), forme).astype(float)
        resultat[~np.isfinite(resultat)] = np.nan   # (division par zéro, racine d'un négatif…)
        return resultat


def _separer_prefixe(texte):
    """« f(x) = … » ou « y = … » → (nom ou None, reste)."""
    t = texte
    for a, b in _REMPLACEMENTS.items():
        t = t.replace(a, b)
    m = _PREFIXE.match(t)
    if not m:
        return None, t
    return m.group(1), t[m.end():]


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


def _analyser(texte, variables):
    if not texte.strip():
        raise ValueError("rien n'est écrit")
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
        raise ValueError("expression mal écrite")
    parametres = set()
    _verifier(arbre, variables, parametres)
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


def lire(texte, variables):
    """Raccourci : Expression(texte, variables), ValueError avec un message clair si illisible."""
    return Expression(texte, variables)


def echantillonner_courbe(expression, x0, x1, hauteur_vue, valeurs_parametres, n=2000):
    """Points (x, y) d'une courbe y = f(x) sur [x0, x1]. Les sauts verticaux plus grands que
    la hauteur de la vue (asymptotes, comme pour tan ou 1/x) sont coupés par un NaN."""
    x = np.linspace(x0, x1, n)
    valeurs = dict(valeurs_parametres, x=x)
    y = expression.evaluer(valeurs)
    saut = np.abs(np.diff(y)) > 2 * max(hauteur_vue, 1e-300)
    changement = np.sign(y[:-1]) != np.sign(y[1:])
    coupures = np.where(saut & changement)[0]
    if coupures.size:
        y = y.copy()
        y[coupures] = np.nan   # on coupe la ligne au point avant le saut
    return x, y
