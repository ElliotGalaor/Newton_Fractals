#include "Tableau.h"

Tableau::Tableau() {
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
    tab = res;
    vector<vector<int>> res_int;
    res_int.resize(dim_x);  
    for (int i = 0; i < dim_x; ++i) {
        res_int[i].resize(dim_y);
    }
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            res_int[i][j] = -1;
        }
    }
    this->res = res_int;
}

Tableau::Tableau(int dim_x, int dim_y, double max_x, double min_x, double max_y, double min_y) {
    vector<vector<CNum>> res;
    this->dim_x = dim_x;
    this->dim_y = dim_y;
    this->max_x = max_x;
    this->min_x = min_x;
    this->max_y = max_y;
    this->min_y = min_y;
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
    tab = res;
    vector<vector<int>> res_int;
    res_int.resize(dim_x);  
    for (int i = 0; i < dim_x; ++i) {
        res_int[i].resize(dim_y);
    }
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            res_int[i][j] = -1;
        }
    }
    this->res = res_int;
}

void Tableau::reInit() {
    vector<vector<CNum>> res;
    res.resize(dim_x);     
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
    tab = res;
    vector<vector<int>> res_int;
    res_int.resize(dim_x);   
    for (int i = 0; i < dim_x; ++i) {
        res_int[i].resize(dim_y);
    }
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {
            res_int[i][j] = -1;
        }
    }
    this->res = res_int;
}