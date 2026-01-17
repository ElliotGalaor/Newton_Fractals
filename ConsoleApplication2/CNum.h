#pragma once
#include <math.h>
class CNum
{
private: 
	double re;
	double im;

public:
	CNum();
	CNum(double a, double b);
	double getRe() const { return re; }
	double getIm() const { return im; }
	void setRe(double re) { this->re = re; }
	void setIm(double im) { this->im = im; }
	double norme() { return sqrt(pow(re, 2) + pow(im, 2)); }
	CNum operator+(const CNum& a) const;
	CNum operator+(const double& a) const;
	CNum operator-(const CNum& a) const;
	CNum operator-(const double& a) const;
	CNum operator*(const CNum& a) const;
	CNum operator*(const double& a) const;
	CNum operator/(const CNum& a) const;
	CNum operator/(const double& a) const;
	bool operator==(const CNum& a) const;


};

CNum::CNum() {
	re = 0;
	im = 0;
}

CNum::CNum(double a, double b) {
	re = a;
	im = b;
}


CNum CNum::operator+(const CNum& a) const {
	return CNum(this->getRe() + a.getRe(), this->getIm() + a.getIm());
}

CNum CNum::operator+(const double& a) const {
	return CNum(this->getRe() + a, this->getIm());
}

CNum CNum::operator-(const CNum& a) const {
	return CNum(this->getRe() - a.getRe(), this->getIm() - a.getIm());
}

CNum CNum::operator-(const double& a) const {
	return CNum(this->getRe() - a, this->getIm());
}

CNum CNum::operator*(const CNum& other) const {
	double a = this->getRe();
	double b = this->getIm();
	double c = other.getRe();
	double d = other.getIm();
	return CNum(a * c - b * d, b * c - a * d);
}

CNum CNum::operator*(const double& a) const {
	return CNum(this->getRe() * a, this->getIm() * a);
}

CNum CNum::operator/(const CNum& other) const {
	double a = this->getRe();
	double b = this->getIm();
	double c = other.getRe();
	double d = other.getIm();
	double K = pow(c, 2) + pow(d, 2);
	return CNum(K * (a * c + b * d), K * (b * c - a * d));
}

CNum CNum::operator/(const double& a) const {
	return CNum(this->getRe() / a, this->getIm() / a);
}

bool CNum::operator==(const CNum& a) const {
	return (this->getRe() == a.getRe()) && (this->getIm() == a.getIm());
}


