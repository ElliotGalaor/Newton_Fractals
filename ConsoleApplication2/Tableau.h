#pragma once
#include <vector>
#include "CNum.h"

// Grille de l'attracteur de Newton.
// Les points complexes ne sont plus stockés : ils se calculent à partir de (x, y).
// Les indices de racine sont rangés dans un seul tableau contigu (bien plus
// rapide qu'un vector<vector<...>>).
class Tableau
{
private:
    vector<int> res;    // indice de la plus proche racine (-1 quand il n'y en a pas), case (x, y) en res[x * dim_y + y]
    int dim_x = 10;
    int dim_y = 10;
    double max_x = 2;
    double min_x = -2;
    double max_y = 2;
    double min_y = -2;
    double incr_x = 0.4;
    double incr_y = 0.4;
public:
    Tableau(int dim_x = 10, int dim_y = 10, double max_x = 2, double min_x = -2, double max_y = 2, double min_y = -2);
    CNum getCell(int x, int y) const { return CNum(min_x + x * incr_x, min_y + y * incr_y); }
    int getIndice(int x, int y) const { return res[(size_t)x * dim_y + y]; }
    int getDimX() const { return dim_x; }
    int getDimY() const { return dim_y; }
    double getMaxX() const { return max_x; }
    double getMinX() const { return min_x; }
    double getMaxY() const { return max_y; }
    double getMinY() const { return min_y; }
    void setIndice(int ind, int x, int y) { res[(size_t)x * dim_y + y] = ind; }
    void setDimX(int dim_x) { this->dim_x = dim_x; }
    void setDimY(int dim_y) { this->dim_y = dim_y; }
    void setMaxX(double max_x) { this->max_x = max_x; }
    void setMinX(double min_x) { this->min_x = min_x; }
    void setMaxY(double max_y) { this->max_y = max_y; }
    void setMinY(double min_y) { this->min_y = min_y; }
    void reInit();   // à appeler après un changement de dimensions ou de bornes
};
