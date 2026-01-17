#pragma once
#include <math.h>
#include <iostream>
using namespace std;
class CNum
{
private:
	double re;
	double im;

public:
	CNum();
	CNum(double a) { re = a; im = 0; }
	CNum(double a, double b);
	double getRe() const { return re; }
	double getIm() const { return im; }
	void setRe(double re) { this->re = re; }
	void setIm(double im) { this->im = im; }
	double norme() { return sqrt(pow(re, 2) + pow(im, 2)); }
	CNum pui(int p);
	CNum operator+(const CNum& a) const;
	CNum operator+(const double& a) const;
	CNum operator-(const CNum& a) const;
	CNum operator-(const double& a) const;
	CNum operator*(const CNum& a) const;
	CNum operator*(const double& a) const;
	friend CNum operator*(double scalar, const CNum& v) {
		return v * scalar;
	}
	CNum operator/(const CNum& a) const;
	CNum operator/(const double& a) const;
	CNum operator=(const double& a) const;
	bool operator==(const CNum& a) const;
	friend ostream& operator<<(ostream& os, const CNum& n);

};


