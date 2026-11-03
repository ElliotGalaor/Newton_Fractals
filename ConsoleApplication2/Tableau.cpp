#include "Tableau.h"

Tableau::Tableau(int dim_x, int dim_y, double max_x, double min_x, double max_y, double min_y)
    : dim_x(dim_x), dim_y(dim_y), max_x(max_x), min_x(min_x), max_y(max_y), min_y(min_y) {
    reInit();
}

void Tableau::reInit() {
    incr_x = (max_x - min_x) / dim_x;
    incr_y = (max_y - min_y) / dim_y;
    res.assign((size_t)dim_x * dim_y, -1);
}
