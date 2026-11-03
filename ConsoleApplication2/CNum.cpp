#include <iostream>
#include "CNum.h"
using namespace std;

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
