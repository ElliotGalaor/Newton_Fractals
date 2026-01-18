#include <iostream>
#include <vector>
#include <math.h>
#include "CNum.h"

using namespace std;

CNum j = CNum(-0.5, sqrt(3) / 2);

CNum f(CNum x) {
    return x.pui(3) - 1;
}

CNum f_derivee(CNum x) {
    return 3 * x.pui(2);
}

double dist(CNum a, CNum b) {
    return sqrt(pow(a.getRe() - b.getRe(), 2) + pow(a.getIm() - b.getIm(), 2));
}

// A refaire lorsqu'on generalisera pour tout polynome
double distZero(CNum test) {
    CNum a = 1;
    CNum b = j;
    CNum c = j*j;
    return min({ dist(test,a),dist(test,b),dist(test,c) });
}

// A refaire lorsqu'on generalisera pour tout polynome
int index_distZero(CNum test) {
    CNum a = 1;
    CNum b = j;
    CNum c = j * j;
    double d1 = dist(test, a);
    double d2 = dist(test, b);
    double d3 = dist(test, c);
    if (d1 == min({ d1,d2,d3 })) return 0;
    if (d2 == min({ d1,d2,d3 })) return 1;
    return 3;
}


static vector<vector<CNum>> init_map_simple(int dim_x=10, int dim_y=10, double max_x=2, double min_x=-2, double max_y=2, double min_y=-2) {
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
    

static vector<vector<int>> map_fractale_simple(vector<vector<CNum>> tab,int dim_x=10, int dim_y=10, double eps=1e-6, int step=50 ) {
    vector<vector<int>> res;
    res.resize(dim_x);      // initialise le tableau
    for (int i = 0; i < dim_x; ++i) {
        res[i].resize(dim_y);
    }
    int k = 0;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            CNum iter = tab[i][j];
            while ((k < step) && (distZero(iter) > eps) && (f_derivee(iter)!=0)) {
                iter = iter - f(iter)/f_derivee(iter);
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

int main()
{
    affiche_terminal_simple(100, 150);
    

    //return 0;
}

