#pragma once
#include <vector>
#include "CNum.h"

class Tableau
{
private:
    vector<vector<CNum>> tab;   // tableau des valeurs complexes utilisées pour l'attracteur de Newton
    vector<vector<int>> res;    // tableau d'indice de la plus proche racine (-1 quand il n'y en a pas)
    int dim_x = 10;
    int dim_y = 10; 
    double max_x = 2;
    double min_x = -2;
    double max_y = 2;
    double min_y = -2;
public:
	Tableau();
    Tableau(int dim_x = 10, int dim_y = 10, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2);
    CNum getCell(int x, int y) { return tab[x][y]; }
    int getIndice(int x, int y) { return res[x][y]; }
    int getDimX() { return dim_x; }
    int getDimY() { return dim_y; }
    double getMaxX() { return max_x; }
    double getMinX() { return min_x; }
    double getMaxY() { return max_y; }
    double getMinY() { return min_y; }
    void setCell(CNum c, int x, int y) { tab[x][y] = c; }
    void setIndice(int ind, int x, int y) { res[x][y] = ind; }
    void setDimX(int dim_x) { this->dim_x = dim_x; }
    void setDimY(int dim_y) { this->dim_y = dim_y; }
    void setMaxX(double max_x) { this->max_x = max_x; }
    void setMinX(double min_x) { this->min_x = min_x; }
    void setMaxY(double max_y) { this->max_y = max_y; }
    void setMinY(double min_y) { this->min_y = min_y; }
    void reInit();
};

