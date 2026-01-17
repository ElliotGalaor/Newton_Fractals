// ConsoleApplication2.cpp : Ce fichier contient la fonction 'main'. L'exécution du programme commence et se termine à cet endroit.
//

#include <iostream>
#include <vector>
#include <complex>
using namespace std;

int factoriel(int a) {
    if (((a % 1) != 0) || (a < 0)) {
        cout << "Error : Undefined value";
    }
    else if (a != 1) {
        return factoriel(a - 1) * a;
    }
    else {
        return 1;
    }
}

int average(vector<int> n) {
    int res = 0;
    for(int i = 0; i < n.size();i++) {
        res += n[i];
    }
    return res/n.size();
}

int lowest(vector<int> n) {
    int res = n[0];
    for (int i : n) {
        if (i < res) res = i;
    }
    return res;
}

void affiche_liste_cube(int N) {
    if (N >= 5) {
        for (int i = 5;i <= N;i++) {
            cout << pow(i, 3) << "  ";
        }
    }
}

int u_n(int n) {
    if (n == 0) return 3;
    else return 3 * u_n(n - 1) + 4;
}

int premier(int n) {
    for (int i = 2; i < n;i++) {
        if (n % i == 0) {
            cout << n << " n'est pas premier\n\n";
            return 0;
        }
    }
    cout << n << " est premier\n\n";
    return 1;
}

double f(double x) {
    return pow(x, 3) - 2 * x + 2;
}

static vector<vector<complex<double>>> map_fractale_simple(int dim_x, int dim_y, double eps, int) {
    vector<vector<complex<double>>> res;
    for (int i = 0;i < dim_x;i++) {
        for (int j = 0;j < dim_y;j++) {

        }
    }
    return res;
}

int main()
{
    double a = -1.7692921;
    cout << f(a);

    //return 0;
}

