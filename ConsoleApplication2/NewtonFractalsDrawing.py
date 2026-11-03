import matplotlib.pyplot as plt
import numpy as np

# Lecture rapide : tout le fichier d'un coup, converti directement en tableau numpy
with open(r'results.txt') as f:
    lignes = f.read().splitlines()
tableau = np.array(" ".join(lignes).split(), dtype=np.int8).reshape(len(lignes), -1)

tab = tableau.T  # équivalent de l'ancien reverse_table (transposition)
plt.figure(figsize=(10,10))
plt.imshow(tab,extent=[-2,2,-2,2])
plt.show()
