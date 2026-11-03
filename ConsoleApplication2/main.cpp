#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <chrono>
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

void Newton_Fractals(int dim_x, int dim_y, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2, double eps = 1e-6) {
    auto t0 = chrono::steady_clock::now();
    Tableau res(dim_x, dim_y, max_x, min_x, max_y, min_y);
    map_fractale(res, eps);
    auto t1 = chrono::steady_clock::now();
    write_file(res);
    auto t2 = chrono::steady_clock::now();
    cout << "Calcul : " << chrono::duration<double>(t1 - t0).count() << " s, "
         << "ecriture : " << chrono::duration<double>(t2 - t1).count() << " s" << endl;

    string filename = "NewtonFractalsDrawing.py";
    string command = "python ";
    command += filename;
    cout << "Show graph ? (Y/N)" << endl;
    char test_affichage;
    cin >> test_affichage;
    if (test_affichage == 'Y' || test_affichage == 'y') {
        system(command.c_str());
    }
}

int main()
{
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