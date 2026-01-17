#include <iostream>
#include <vector>
#include <math.h>
#include "CNum.h"

using namespace std;

CNum j = CNum(-0.5, sqrt(3) / 2);

CNum f(CNum x) {
    return x * x * x - 1;
}

CNum f_derivee(CNum x) {
    return 3 * x * x;
}

double dist(CNum a, CNum b) {
    return sqrt(pow(a.getRe() - b.getRe(), 2) + pow(a.getIm() - b.getIm(), 2));
}

double distZero(CNum test) {
    CNum a = 1;
    CNum b = j;
    CNum c = j*j;
    return min({ dist(test,a),dist(test,b),dist(test,c) });
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
    

static vector<vector<CNum>> map_fractale_simple(vector<vector<CNum>> tab,int dim_x=10, int dim_y=10, double eps=1e-6, int step=50 ) {
    int k = 0;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            CNum iter = tab[i][j];
            while ((k < step) && (distZero(iter) > eps)) {
                iter = iter * iter * iter - 1;
                k++;
            }
            tab[i][j] = iter;
        }
    }
    return tab;
}

int main()
{
    vector<vector<CNum>> test = init_map_simple();
    //test = map_fractale_simple(test);
    //for (vector<CNum> i : test) {
    //    for (CNum j : i) {
    //        cout << j << " ; ";
    //    }
    //    cout << endl;
    //}
    cout << j << "   " << j * j *j*j*j<< "   " << j.pui(5);
    

    //return 0;
}

