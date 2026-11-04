#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <chrono>
#include <cstdlib>
#include <algorithm>
#include <cstdint>
#include <math.h>
#include "CNum.h"
#include "Tableau.h"

using namespace std;

CNum j = CNum(-0.5, sqrt(3) / 2);

// Polynome par défaut (quand le programme est lancé sans option)
static const char* POLYNOME_DEFAUT = "z^3 - 2z + 2";
static const vector<CNum> COEFS_DEFAUT = { CNum(1), CNum(0), CNum(-2), CNum(2) };
static const vector<CNum> RACINES_DEFAUT = { CNum(-1.76929,0), CNum(0.884646,-0.589743), CNum(0.884646,0.589743) };

// Polynome utilisé pour le calcul : coefficients du plus haut degré au terme constant,
// et ses racines (dans l'ordre où elles sont numérotées dans results.txt : 1, 2, ...)
static vector<CNum> coefs = COEFS_DEFAUT;
static vector<CNum> zero_list = RACINES_DEFAUT;
static double seuil2 = 0.1 * 0.1;   // distance (au carré) sous laquelle un point est attribué à une racine

// Calcule p(z) et p'(z) en une seule passe (schéma de Horner)
static inline void evaluer(const CNum& z, CNum& p, CNum& dp) {
    p = coefs[0];
    dp = CNum(0, 0);
    for (size_t k = 1; k < coefs.size(); k++) {
        dp = dp * z + p;
        p = p * z + coefs[k];
    }
}


double dist(const CNum& a, const CNum& b) {
    return (a - b).norme();
}

// Cherche en une seule passe la racine la plus proche de z.
// Renvoie son indice (1..nombre de racines) et met la distance AU CARRÉ dans d2min
// (on évite ainsi sqrt et pow dans la boucle de Newton).
static inline int nearestZero(const CNum& z, double& d2min) {
    d2min = (z - zero_list[0]).norme2();
    int idx = 1;
    const int nb_zero = (int)zero_list.size();
    for (int r = 1; r < nb_zero; r++) {
        double d2 = (z - zero_list[r]).norme2();
        if (d2 <= d2min) { d2min = d2; idx = r + 1; }
    }
    return idx;
}

double distZero(const CNum& test) {
    double d2;
    nearestZero(test, d2);
    return sqrt(d2);
}

int index_distZero(const CNum& test) {
    double d2;
    return nearestZero(test, d2);
}


// Remplit tab en place (plus de copie du tableau).
// Les lignes sont réparties sur tous les coeurs du processeur avec OpenMP.
static void map_fractale(Tableau& tab, double eps = 1e-6, int step = 50) {
    const int dim_x = tab.getDimX();
    const int dim_y = tab.getDimY();
    const double eps2 = eps * eps;

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < dim_x; i++) {
        for (int jj = 0; jj < dim_y; jj++) {
            CNum iter = tab.getCell(i, jj);
            CNum p, dp;
            double d2;
            int idx = nearestZero(iter, d2);
            for (int k = 0; k < step && d2 > eps2; k++) {
                evaluer(iter, p, dp);
                if (dp == 0) break;
                iter = iter - p / dp;
                idx = nearestZero(iter, d2);
            }
            if (d2 < seuil2) tab.setIndice(idx, i, jj);
        }
    }
}



void write_file(const Tableau& tab) {
    // On construit tout le texte en mémoire puis on l'écrit d'un coup
    // (endl vidait le buffer à chaque ligne).
    string buffer;
    buffer.reserve((size_t)tab.getDimX() * (tab.getDimY() * 3 + 2));
    for (int i = 0; i < tab.getDimX(); i++) {
        for (int k = 0; k < tab.getDimY(); k++) {
            buffer += to_string(tab.getIndice(i, k));
            buffer += ' ';
        }
        buffer += '\n';
    }
    ofstream MyFile("results.txt");
    MyFile << buffer;
    MyFile.close();
}

// Version binaire, bien plus rapide à écrire et à relire (utilisée par l'interface) :
// en-tête de 8 octets (dim_x puis dim_y, entiers 32 bits little-endian), puis un octet
// signé par pixel, dans le même ordre que results.txt (ligne par ligne selon x).
static bool write_binary(const Tableau& tab, const string& chemin) {
    const int32_t dims[2] = { tab.getDimX(), tab.getDimY() };
    vector<int8_t> octets((size_t)dims[0] * dims[1]);
    for (int i = 0; i < dims[0]; i++)
        for (int k = 0; k < dims[1]; k++)
            octets[(size_t)i * dims[1] + k] = (int8_t)tab.getIndice(i, k);
    ofstream f(chemin, ios::binary);
    if (!f) return false;
    f.write(reinterpret_cast<const char*>(dims), sizeof(dims));
    f.write(reinterpret_cast<const char*>(octets.data()), (streamsize)octets.size());
    return (bool)f;
}

// Paramètres d'un calcul
struct Parametres {
    int dim_x = 1000;
    int dim_y = 1000;
    double min_x = -2, max_x = 2;
    double min_y = -2, max_y = 2;
    double eps = 1e-6;
    int iterations = 50;
    string fichier_binaire;                  // si non vide : sortie binaire dans ce fichier au lieu de results.txt
    vector<CNum> coefs = COEFS_DEFAUT;       // du plus haut degré au terme constant
    vector<CNum> racines = RACINES_DEFAUT;
    bool mandelbrot = false;                 // ensemble de Mandelbrot au lieu de la fractale de Newton
};

// Ensemble de Mandelbrot : pour chaque point c, on itère z <- z² + c depuis z = 0.
// Résultat par pixel : nombre d'itérations « lissé » avant que |z| dépasse le rayon
// d'échappement (valeur réelle, pour des dégradés sans bandes), ou -1 si le point
// n'a pas divergé après p.iterations itérations (il est alors considéré dans l'ensemble).
static vector<float> calculer_mandelbrot(const Parametres& p) {
    const int dim_x = p.dim_x, dim_y = p.dim_y;
    const double incr_x = (p.max_x - p.min_x) / dim_x;
    const double incr_y = (p.max_y - p.min_y) / dim_y;
    const double rayon2 = 256.0 * 256.0;     // grand rayon d'échappement : lissage plus précis
    const double log2 = log(2.0);
    vector<float> res((size_t)dim_x * dim_y);

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < dim_x; i++) {
        const double cx = p.min_x + i * incr_x;
        for (int k = 0; k < dim_y; k++) {
            const double cy = p.min_y + k * incr_y;
            float& sortie = res[(size_t)i * dim_y + k];
            // Points de la cardioïde principale et du disque de période 2 : dans l'ensemble, sans calcul
            const double q = (cx - 0.25) * (cx - 0.25) + cy * cy;
            if (q * (q + (cx - 0.25)) <= 0.25 * cy * cy || (cx + 1) * (cx + 1) + cy * cy <= 0.0625) {
                sortie = -1.0f;
                continue;
            }
            double x = 0, y = 0, x2 = 0, y2 = 0;
            int n = 0;
            while (n < p.iterations && x2 + y2 <= rayon2) {
                y = 2 * x * y + cy;
                x = x2 - y2 + cx;
                x2 = x * x;
                y2 = y * y;
                n++;
            }
            if (n >= p.iterations && x2 + y2 <= rayon2) {
                sortie = -1.0f;
            }
            else {
                const double log_module = 0.5 * log(x2 + y2);
                const double lisse = n + 1 - log(log_module / log2) / log2;
                sortie = (float)(lisse > 0 ? lisse : 0);
            }
        }
    }
    return res;
}

// Format : dim_x et dim_y (int32 little-endian), puis un float32 par pixel, ligne par ligne selon x
static bool write_binary_reels(const vector<float>& valeurs, int dim_x, int dim_y, const string& chemin) {
    const int32_t dims[2] = { dim_x, dim_y };
    ofstream f(chemin, ios::binary);
    if (!f) return false;
    f.write(reinterpret_cast<const char*>(dims), sizeof(dims));
    f.write(reinterpret_cast<const char*>(valeurs.data()), (streamsize)(valeurs.size() * sizeof(float)));
    return (bool)f;
}

static bool calculer_et_ecrire_mandelbrot(const Parametres& p) {
    auto t0 = chrono::steady_clock::now();
    vector<float> res = calculer_mandelbrot(p);
    auto t1 = chrono::steady_clock::now();
    if (!write_binary_reels(res, p.dim_x, p.dim_y, p.fichier_binaire)) {
        cerr << "Ecriture impossible : " << p.fichier_binaire << endl;
        return false;
    }
    auto t2 = chrono::steady_clock::now();
    cout << "Calcul : " << chrono::duration<double>(t1 - t0).count() << " s, "
         << "ecriture : " << chrono::duration<double>(t2 - t1).count() << " s" << endl;
    return true;
}

// Calcule la fractale, écrit results.txt (ou le fichier binaire) et affiche les temps
static bool calculer(const Parametres& p) {
    if (p.mandelbrot) return calculer_et_ecrire_mandelbrot(p);

    coefs = p.coefs;
    zero_list = p.racines;
    // Seuil d'attribution : 0.1, réduit si des racines sont très proches l'une de l'autre
    double seuil = 0.1;
    for (size_t a = 0; a < zero_list.size(); a++)
        for (size_t b = a + 1; b < zero_list.size(); b++)
            seuil = min(seuil, 0.4 * dist(zero_list[a], zero_list[b]));
    seuil2 = seuil * seuil;

    auto t0 = chrono::steady_clock::now();
    Tableau res(p.dim_x, p.dim_y, p.max_x, p.min_x, p.max_y, p.min_y);
    map_fractale(res, p.eps, p.iterations);
    auto t1 = chrono::steady_clock::now();
    if (p.fichier_binaire.empty()) {
        write_file(res);
    }
    else if (!write_binary(res, p.fichier_binaire)) {
        cerr << "Ecriture impossible : " << p.fichier_binaire << endl;
        return false;
    }
    auto t2 = chrono::steady_clock::now();
    cout << "Calcul : " << chrono::duration<double>(t1 - t0).count() << " s, "
         << "ecriture : " << chrono::duration<double>(t2 - t1).count() << " s" << endl;
    return true;
}

void Newton_Fractals(int dim_x, int dim_y, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2, double eps = 1e-6, int iterations = 50) {
    Parametres p;
    p.dim_x = dim_x; p.dim_y = dim_y;
    p.min_x = min_x; p.max_x = max_x;
    p.min_y = min_y; p.max_y = max_y;
    p.eps = eps; p.iterations = iterations;
    calculer(p);

    string filename = "NewtonFractalsDrawing.py";
    // On transmet les paramètres au script : il les affiche et peut relancer un calcul
    ostringstream command;
    command.precision(17);
    command << "python " << filename << " --bornes " << min_x << " " << max_x << " " << min_y << " " << max_y
            << " --eps " << eps << " --iterations " << iterations << " --polynome \"" << POLYNOME_DEFAUT << "\"";
    system(command.str().c_str());
}

static void afficher_aide() {
    cout << "Utilisation : main.exe [options]\n"
            "  --taille LARGEUR HAUTEUR            nombre de pixels (defaut 1000 1000)\n"
            "  --bornes MIN_X MAX_X MIN_Y MAX_Y    zone du plan complexe (defaut -2 2 -2 2)\n"
            "  --eps EPS                           precision de convergence (defaut 1e-6)\n"
            "  --iterations N                      nombre maximal d'iterations (defaut 50)\n"
            "  --coefs N re1 im1 ... reN imN       coefficients du polynome, du plus haut degre\n"
            "                                      au terme constant (defaut z^3 - 2z + 2)\n"
            "  --racines N re1 im1 ... reN imN     racines du polynome (obligatoire avec --coefs) ;\n"
            "                                      leur ordre donne les numeros 1..N de results.txt\n"
            "  --binaire FICHIER                   ecrit le resultat en binaire (en-tete dim_x, dim_y\n"
            "                                      en int32, puis un int8 par pixel) au lieu de results.txt\n"
            "  --mandelbrot                        ensemble de Mandelbrot au lieu de la fractale de Newton\n"
            "                                      (avec --binaire, obligatoire : un float32 par pixel = nombre\n"
            "                                      d'iterations lisse avant divergence, -1 dans l'ensemble)\n"
            "Sans option : calcul par defaut puis ouverture du graphique.\n";
}

// Lit un nombre ; renvoie false si le texte n'en est pas un
static bool lire_nombre(const char* texte, double& valeur) {
    char* fin = nullptr;
    valeur = strtod(texte, &fin);
    return fin != texte && *fin == '\0';
}

// Lit « N re1 im1 ... reN imN » à partir de argv[a + 1] ; avance a jusqu'à la dernière valeur lue
static bool lire_complexes(int argc, char* argv[], int& a, vector<CNum>& sortie, string& erreur) {
    string opt = argv[a];
    double n;
    if (a + 1 >= argc || !lire_nombre(argv[a + 1], n) || n < 1 || n > 100 || n != (int)n) {
        erreur = "Nombre de valeurs invalide apres " + opt; return false;
    }
    int nb = (int)n;
    if (a + 1 + 2 * nb >= argc) { erreur = "Valeurs manquantes apres " + opt; return false; }
    sortie.clear();
    for (int k = 0; k < nb; k++) {
        double re, im;
        const char* t_re = argv[a + 2 + 2 * k];
        const char* t_im = argv[a + 3 + 2 * k];
        if (!lire_nombre(t_re, re) || !lire_nombre(t_im, im)) {
            erreur = string("Nombre invalide apres ") + opt; return false;
        }
        sortie.push_back(CNum(re, im));
    }
    a += 1 + 2 * nb;
    return true;
}

static bool lire_arguments(int argc, char* argv[], Parametres& p, string& erreur) {
    bool coefs_lus = false, racines_lues = false;
    for (int a = 1; a < argc; a++) {
        string opt = argv[a];
        if (opt == "--binaire") {
            if (a + 1 >= argc) { erreur = "Nom de fichier manquant apres --binaire"; return false; }
            p.fichier_binaire = argv[++a];
            continue;
        }
        if (opt == "--mandelbrot") {
            p.mandelbrot = true;
            continue;
        }
        if (opt == "--coefs" || opt == "--racines") {
            vector<CNum>& cible = (opt == "--coefs") ? p.coefs : p.racines;
            if (!lire_complexes(argc, argv, a, cible, erreur)) return false;
            (opt == "--coefs" ? coefs_lus : racines_lues) = true;
            continue;
        }
        int nb = (opt == "--taille") ? 2 : (opt == "--bornes") ? 4 : (opt == "--eps" || opt == "--iterations") ? 1 : -1;
        if (nb < 0) { erreur = "Option inconnue : " + opt; return false; }
        if (a + nb >= argc) { erreur = "Valeurs manquantes apres " + opt; return false; }
        double v[4];
        for (int k = 0; k < nb; k++) {
            if (!lire_nombre(argv[a + 1 + k], v[k])) { erreur = string("Nombre invalide : ") + argv[a + 1 + k]; return false; }
        }
        if (opt == "--taille") { p.dim_x = (int)v[0]; p.dim_y = (int)v[1]; }
        else if (opt == "--bornes") { p.min_x = v[0]; p.max_x = v[1]; p.min_y = v[2]; p.max_y = v[3]; }
        else if (opt == "--eps") p.eps = v[0];
        else p.iterations = (int)v[0];
        a += nb;
    }
    if (p.dim_x < 1 || p.dim_y < 1) { erreur = "La taille doit etre d'au moins 1 pixel"; return false; }
    if (p.min_x >= p.max_x || p.min_y >= p.max_y) { erreur = "Il faut MIN < MAX pour les bornes"; return false; }
    if (p.eps <= 0) { erreur = "EPS doit etre positif"; return false; }
    if (p.iterations < 1) { erreur = "Il faut au moins 1 iteration"; return false; }
    if (p.mandelbrot && p.fichier_binaire.empty()) { erreur = "--mandelbrot demande --binaire FICHIER"; return false; }
    if (coefs_lus != racines_lues) { erreur = "--coefs et --racines doivent etre donnes ensemble"; return false; }
    if (p.coefs.size() < 2 || p.coefs[0] == 0) { erreur = "Le polynome doit etre de degre 1 au moins"; return false; }
    return true;
}

int main(int argc, char* argv[])
{
    if (argc > 1) {
        // Mode utilisé par l'interface Python : calcul seul, sans question
        string a1 = argv[1];
        if (a1 == "--aide" || a1 == "--help" || a1 == "-h") { afficher_aide(); return 0; }
        Parametres p;
        string erreur;
        if (!lire_arguments(argc, argv, p, erreur)) {
            cerr << erreur << endl;
            afficher_aide();
            return 1;
        }
        return calculer(p) ? 0 : 1;
    }

    //affiche_terminal_simple(100, 150);
    Newton_Fractals(1000, 1000, 0.3, -0.3, 0.3, -0.3, 1e-9);

}


// Fonctions basique obsolete

/*
static vector<vector<CNum>> init_map_simple(int dim_x = 10, int dim_y = 10, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2) {
    vector<vector<CNum>> res;
    res.resize(dim_x);      // initialise le tableau
    for (int i = 0; i < dim_x; ++i) {
        res[i].resize(dim_y);
    }
    double incr_x = (max_x - min_x) / dim_x;
    double incr_y = (max_y - min_y) / dim_y;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            res[i][j] = CNum(min_x + i * incr_x, min_y + j * incr_y);
        }
    }
    return res;
}

static vector<vector<int>> map_fractale_simple(vector<vector<CNum>> tab, int dim_x = 10, int dim_y = 10, double eps = 1e-6, int step = 50) {
    vector<vector<int>> res;
    res.resize(dim_x);      // initialise le tableau
    for (int i = 0; i < dim_x; ++i) {
        res[i].resize(dim_y);
    }
    int k = 0;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            CNum iter = tab[i][j];
            while ((k < step) && (distZero(iter) > eps) && (f_derivee(iter) != 0)) {
                iter = iter - f(iter) / f_derivee(iter);
                k++;
            }
            res[i][j] = index_distZero(iter);
            k = 0;
        }
    }
    return res;
}

void affiche_terminal_simple(int dim_x, int dim_y) {
    vector<vector<CNum>> test = init_map_simple(dim_x, dim_y);
    vector<vector<int>> res = map_fractale_simple(test, dim_x, dim_y);
    for (vector<int> i : res) {
        for (int j : i) {
            cout << j;
        }
        cout << endl;
    }
}

void write_file_simple(vector<vector<int>> tab) {
    ofstream MyFile("results.txt");
    for (vector<int> i : tab) {
        for (int j : i) {
            MyFile << j << " ";
        }
        MyFile << endl;
    }

    MyFile.close();
}

void Newton_Fractals_Simple(int dim_x, int dim_y) {
    vector<vector<CNum>> test = init_map_simple(dim_x, dim_y);
    vector<vector<int>> res = map_fractale_simple(test, dim_x, dim_y);
    write_file_simple(res);

    string filename = "NewtonFractalsDrawing.py";
    string command = "python ";
    command += filename;
    cout << "Show graph ? (Y/N)" << endl;
    char test_affichage;
    cin >> test_affichage;
    char x[20];
    x[0] = 'Y';
    x[1] = 'y';
    if (test_affichage == x[0] || test_affichage == x[1]) {
        system(command.c_str());
    }
}
*/