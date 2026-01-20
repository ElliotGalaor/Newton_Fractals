#include <iostream>
#include <iostream>
#include <fstream>
#include <vector>
#include <math.h>
#include "CNum.h"
#include "Tableau.h"

using namespace std;

CNum j = CNum(-0.5, sqrt(3) / 2);
// Racines du polynome
vector<CNum> zero_list = { CNum(-1.76929,0), CNum(0.884646,-0.589743),CNum(0.884646,0.589743) };

// Polynome à représenter
CNum f(CNum x) {

    return x.pui(3) - 2 * x + 2;
}

// Dérivée du polynome
CNum f_derivee(CNum x) {
    return 3 * x.pui(2) - 2;
}


double dist(CNum a, CNum b) {
    return sqrt(pow(a.getRe() - b.getRe(), 2) + pow(a.getIm() - b.getIm(), 2));
}


double distZero(CNum test) {
    double res = dist(test,zero_list[0]);
    for (CNum i : zero_list) {
        if (dist(test, i) < res) res = dist(test, i);
    }
    return res;
}

int index_distZero(CNum test) {
    int res = 0;
    int ind = 1;
    vector<double> list_index;
    for(CNum i : zero_list) {
        if (distZero(test) == dist(test, i)) res = ind;
        ind++;
    }
    return res;
}
   


static Tableau map_fractale(Tableau tab, int dim_x = 10, int dim_y = 10, double eps = 1e-6, int step = 50) {
    Tableau res = tab;
    int k = 0;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            CNum iter = res.getCell(i, j);
            while ((k < step) && (distZero(iter) > eps) && (f_derivee(iter) != 0)) {
                iter = iter - f(iter) / f_derivee(iter);
                k++;
            }
            if(distZero(iter)<0.1) res.setIndice(index_distZero(iter), i, j);
            k = 0;
        }
    }
    return res;
}



void write_file(Tableau tab) {
    ofstream MyFile("results.txt");
    for (int i = 0 ; i < tab.getDimX() ; i++) {
        for (int j = 0 ; j < tab.getDimY() ; j++) {
            MyFile << tab.getIndice(i,j) << " ";
        }
        MyFile << endl;
    }

    MyFile.close();
}

void Newton_Fractals(int dim_x, int dim_y, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2, double eps = 1e-6) {
    Tableau test(dim_x, dim_y, max_x, min_x, max_y, min_y);
    Tableau res = map_fractale(test, dim_x, dim_y, eps);
    write_file(res);

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