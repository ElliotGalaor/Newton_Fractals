#include <iostream>
#include "CNum.h"
using namespace std;

CNum::CNum() {
	re = 0;
	im = 0;
}

CNum::CNum(double a, double b) {
	re = a;
	im = b;
}

CNum CNum::pui(int p) {
	CNum res = 1;
	for (int i = 0;i < p;i++) {
		res = res * CNum(re, im);
	}
	return res;
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
	return CNum(a * c - b * d, b * c + a * d);
}

CNum CNum::operator*(const double& a) const {
	return CNum(this->getRe() * a, this->getIm() * a);
}

CNum CNum::operator/(const CNum& other) const {
	double a = this->getRe();
	double b = this->getIm();
	double c = other.getRe();
	double d = other.getIm();
	double K = 1/(pow(c, 2) + pow(d, 2));
	return CNum(K * (a * c + b * d), K * (b * c - a * d));
}

CNum CNum::operator/(const double& a) const {
	return CNum(this->getRe() / a, this->getIm() / a);
}

CNum CNum::operator=(const double& a) const {
	return CNum(a, 0);
}

bool CNum::operator==(const CNum& a) const {
	return (this->getRe() == a.getRe()) && (this->getIm() == a.getIm());
}

ostream& operator<<(ostream& os, const CNum& n)
{
	if (n.getIm() == 0) {
		if (n.getRe() == 0) {
			os << 0;
			return os;
		}
		os << n.getRe();
		return os;
	}
	else if (n.getRe() == 0) {
		os << n.getIm() << "i";
		return os;
	}
	if (n.getIm() < 0) {
		os << n.getRe() << " - " << -1*n.getIm() << "i";
		return os;
	}
	os << n.getRe() << " + " << n.getIm() << "i";
	return os;
}
