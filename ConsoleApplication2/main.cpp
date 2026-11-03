#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <chrono>
#include <cstdlib>
#include <math.h>
#include "CNum.h"
#include "Tableau.h"

using namespace std;

CNum j = CNum(-0.5, sqrt(3) / 2);
// Racines du polynome
static const CNum zero_list[] = { CNum(-1.76929,0), CNum(0.884646,-0.589743), CNum(0.884646,0.589743) };
static const int nb_zero = sizeof(zero_list) / sizeof(zero_list[0]);

// Polynome à représenter
static inline CNum f(const CNum& x) {
    return x.pui(3) - 2 * x + 2;
}

// Dérivée du polynome
static inline CNum f_derivee(const CNum& x) {
    return 3 * x.pui(2) - 2;
}


double dist(const CNum& a, const CNum& b) {
    return (a - b).norme();
}

// Cherche en une seule passe la racine la plus proche de z.
// Renvoie son indice (1..nb_zero) et met la distance AU CARRÉ dans d2min
// (on évite ainsi sqrt et pow dans la boucle de Newton).
static inline int nearestZero(const CNum& z, double& d2min) {
    d2min = (z - zero_list[0]).norme2();
    int idx = 1;
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
            double d2;
            int idx = nearestZero(iter, d2);
            for (int k = 0; k < step && d2 > eps2; k++) {
                CNum fd = f_derivee(iter);      // calculée une seule fois par itération
                if (fd == 0) break;
                iter = iter - f(iter) / fd;
                idx = nearestZero(iter, d2);
            }
            if (d2 < 0.1 * 0.1) tab.setIndice(idx, i, jj);
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

// Paramètres d'un calcul
struct Parametres {
    int dim_x = 1000;
    int dim_y = 1000;
    double min_x = -2, max_x = 2;
    double min_y = -2, max_y = 2;
    double eps = 1e-6;
    int iterations = 50;
};

// Calcule la fractale, écrit results.txt et affiche les temps
static void calculer(const Parametres& p) {
    auto t0 = chrono::steady_clock::now();
    Tableau res(p.dim_x, p.dim_y, p.max_x, p.min_x, p.max_y, p.min_y);
    map_fractale(res, p.eps, p.iterations);
    auto t1 = chrono::steady_clock::now();
    write_file(res);
    auto t2 = chrono::steady_clock::now();
    cout << "Calcul : " << chrono::duration<double>(t1 - t0).count() << " s, "
         << "ecriture : " << chrono::duration<double>(t2 - t1).count() << " s" << endl;
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
            << " --eps " << eps << " --iterations " << iterations;
    system(command.str().c_str());
}

static void afficher_aide() {
    cout << "Utilisation : main.exe [options]\n"
            "  --taille LARGEUR HAUTEUR            nombre de pixels (defaut 1000 1000)\n"
            "  --bornes MIN_X MAX_X MIN_Y MAX_Y    zone du plan complexe (defaut -2 2 -2 2)\n"
            "  --eps EPS                           precision de convergence (defaut 1e-6)\n"
            "  --iterations N                      nombre maximal d'iterations (defaut 50)\n"
            "Sans option : calcul par defaut puis ouverture du graphique.\n";
}

// Lit un nombre ; renvoie false si le texte n'en est pas un
static bool lire_nombre(const char* texte, double& valeur) {
    char* fin = nullptr;
    valeur = strtod(texte, &fin);
    return fin != texte && *fin == '\0';
}

static bool lire_arguments(int argc, char* argv[], Parametres& p, string& erreur) {
    for (int a = 1; a < argc; a++) {
        string opt = argv[a];
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
        calculer(p);
        return 0;
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