import re 
import matplotlib.pyplot as plt
import numpy as np

tableau = []
with open(r'results.txt') as f:
  for x in f:
      test = list(map(int, re.split(" ",x)[:-1]))
      tableau.append(test)

def reverse_table(tab):
    return [[tab[j][i] for j in range(len(tab))] for i in range(len(tab[0]))]

tab = reverse_table(tableau)
plt.figure(figsize=(10,10))
plt.imshow(tab,extent=[-2,2,-2,2])
plt.show()