#pragma once
#include <math.h>
#include <iostream>
using namespace std;

// Nombre complexe. Toutes les opérations sont définies ici (inline) pour que
// le compilateur puisse les intégrer directement dans la boucle de Newton.
class CNum
{
private:
	double re;
	double im;

public:
	CNum() : re(0), im(0) {}
	CNum(double a) : re(a), im(0) {}
	CNum(double a, double b) : re(a), im(b) {}
	double getRe() const { return re; }
	double getIm() const { return im; }
	void setRe(double re) { this->re = re; }
	void setIm(double im) { this->im = im; }
	double norme2() const { return re * re + im * im; }   // module au carré (sans racine)
	double norme() const { return sqrt(norme2()); }

	// Puissance entière (p >= 0)
	CNum pui(int p) const {
		if (p <= 0) return CNum(1, 0);
		CNum res = *this;
		for (int i = 1; i < p; i++) res = res * *this;
		return res;
	}

	CNum operator+(const CNum& a) const { return CNum(re + a.re, im + a.im); }
	CNum operator+(double a) const { return CNum(re + a, im); }
	CNum operator-(const CNum& a) const { return CNum(re - a.re, im - a.im); }
	CNum operator-(double a) const { return CNum(re - a, im); }
	CNum operator*(const CNum& o) const {
		return CNum(re * o.re - im * o.im, im * o.re + re * o.im);
	}
	CNum operator*(double a) const { return CNum(re * a, im * a); }
	friend CNum operator*(double scalar, const CNum& v) { return v * scalar; }
	CNum operator/(const CNum& o) const {
		double K = 1 / (o.re * o.re + o.im * o.im);
		return CNum(K * (re * o.re + im * o.im), K * (im * o.re - re * o.im));
	}
	CNum operator/(double a) const { return CNum(re / a, im / a); }

	bool operator==(const CNum& a) const { return (re == a.re) && (im == a.im); }
	bool operator==(double a) const { return (re == a) && (im == 0); }
	bool operator!=(const CNum& a) const { return (re != a.re) || (im != a.im); }
	bool operator!=(double a) const { return (re != a) || (im != 0); }

	friend ostream& operator<<(ostream& os, const CNum& n);
};
