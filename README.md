# Newton Fractals

Explore Newton fractals for any polynomial: a fast multithreaded C++ engine computes
which root Newton's method converges to from every point of the complex plane, and a
Qt interface lets you pick the polynomial, zoom in and recompute the view on the fly.

For a polynomial p, Newton's method iterates z ← z − p(z) / p′(z). Each pixel is a
starting point z₀ and is coloured by the root it converges to; the boundaries between
these basins of attraction form the fractal.

## Features

- **Any polynomial**, real or complex coefficients, degree 1 to 20: type an expression
  such as `z^3 - 2z + 2`, `(z-1)(z+2i)` or `z^3 - (1 + 2i)z + 1`…
- …**or give the roots directly** (`1 ; -1 ; 0.5+2i`): the polynomial is then the product
  of (z − root). Repeating a root makes it a multiple root.
- **Fast C++ engine**: Horner evaluation of p and p′ in a single pass, OpenMP
  multithreading — about 20–30 ms for a 1000 × 1000 image on a recent CPU.
- **Interactive Qt interface**: mouse-wheel zoom, drag to pan, automatic full-resolution
  recomputation of the visible area after each zoom, computation in the background.
- **Deep zoom** down to about 10⁻¹³ of the coordinate magnitude (the limit of `double`
  precision), with bounds shown in scientific notation.
- Legend with the value of each root and the share of the image it covers; the root
  reached from the point under the mouse is shown in the status bar.
- PNG export at the computed resolution.

## Requirements

- **C++ compiler** with OpenMP: Visual Studio 2022 (MSVC v143) or g++ (e.g. MSYS2 UCRT64).
- **Python 3.10+** with:
  - `numpy`
  - `PySide6` and `pyqtgraph`

```bash
python -m pip install numpy pyside6 pyqtgraph
```

> **Windows note:** the Qt DLLs shipped by MSYS2 are not signed, and Windows
> Smart App Control may block them (`DLL load failed … application control policy`).
> The PyPI build of PySide6 is signed and works. If the interface is started with a
> Python where Qt cannot be loaded, it automatically relaunches itself with another
> Python on the machine where PySide6 works, or prints the command to install it.

## Build

**Visual Studio:** open `NewtonFractals.sln` and build the **Release | x64** configuration
(OpenMP is already enabled in the project).

**g++ (MSYS2, Linux, macOS with GCC):** from the `ConsoleApplication2` folder:

```bash
g++ -O2 -fopenmp -o main main.cpp Tableau.cpp CNum.cpp
```

Compile with `-O2` and `-fopenmp`: without them most of the speed is lost. When running
`main.exe` built with MSYS2 outside the MSYS2 shell, `C:\msys64\ucrt64\bin` must be on
the `PATH` so that the OpenMP DLL (`libgomp`) is found; the interface adds it automatically.

## Usage

### Graphical interface

From the `ConsoleApplication2` folder:

```bash
python NewtonFractalsDrawing.py
```

The window opens maximized. It finds the compiled program automatically (`main.exe`
built with g++, or the Visual Studio `Release`/`Debug` executable, whichever is newest);
use `--exe path\to\program.exe` to choose another one.

Set the parameters in the right-hand panel, then press **Enter** in any field or click
**Calculate** (*Calculer*):

| Panel section | Parameters |
|---|---|
| Polynomial (*Polynôme*) | `p(z)` / *Racines* switch, the polynomial or its roots, *Exemple ▸* cycles through examples |
| Image | width and height in pixels |
| Complex plane window (*Fenêtre du plan complexe*) | Re min / max, Im min / max |
| Convergence | precision `eps` and maximum number of iterations |

Buttons: *Recalculer la vue affichée* (recompute the visible area), *Pixels carrés*
(adjust the height so pixels are square), *Par défaut* (reset), *Export PNG*.

| Control | Action |
|---|---|
| Mouse wheel | Zoom around the cursor |
| Click and drag | Pan |
| `H` | Back to the view of the computed image |
| `Enter` (in a field) | Compute |

With *Recalcul automatique* checked (default), the visible area is recomputed 0.35 s
after you stop zooming or panning, so details appear instead of enlarged pixels.
The last parameters are remembered in `parametres.json` and the last result is shown
again at the next launch.

Other options of the script:

```bash
python NewtonFractalsDrawing.py --enregistrer image.png    # save the last result as PNG, no window
python NewtonFractalsDrawing.py --help
```

### Polynomial syntax

| Input | Meaning |
|---|---|
| `z^3 - 2z + 2` | powers with `^` or `**`, implicit multiplication (`2z`) |
| `(z-1)(z+2i)` | products of brackets, `i` is the imaginary unit |
| `3z^4 + (1-i)z` | complex coefficients |
| `z^2/2 + 1` | division by a number |

In **roots mode**, separate roots with `;` (then a comma may be used as decimal
separator, e.g. `0,5 ; 1+i`) or with `,` (`1, -1, 2i`). Each root may be a small
expression such as `(1+i)/2` or `1/3`. Switching between the two modes converts the
field content, keeping multiplicities.

### Command-line engine

`main.exe` can also be used on its own. Without options it computes the default
fractal (z³ − 2z + 2 on [−0.3, 0.3]²), writes `results.txt` and opens the interface.
Options (names are in French):

| Option | Description |
|---|---|
| `--taille W H` | image size in pixels (default 1000 1000) |
| `--bornes MIN_X MAX_X MIN_Y MAX_Y` | area of the complex plane (default −2 2 −2 2) |
| `--eps EPS` | convergence precision (default 1e-6) |
| `--iterations N` | maximum number of iterations (default 50) |
| `--coefs N re1 im1 … reN imN` | polynomial coefficients, from highest degree to constant term |
| `--racines N re1 im1 … reN imN` | roots of the polynomial (required with `--coefs`); their order gives the indices 1…N in the output |
| `--binaire FILE` | write a binary file instead of `results.txt` |
| `--aide` | show help |

Example — z³ − 1 on [−2, 2]²:

```bash
main.exe --taille 800 800 --bornes -2 2 -2 2 --coefs 4 1 0 0 0 0 0 -1 0 --racines 3 1 0 -0.5 0.8660254037844386 -0.5 -0.8660254037844386
```

### Output formats

Each pixel holds the index (1…N) of the root reached, or `-1` if Newton's method did not
converge to a root within the iteration limit.

- `results.txt`: one line per x value, `dim_y` space-separated integers per line.
- `results.bin` (`--binaire`): an 8-byte header — `dim_x` and `dim_y` as little-endian
  `int32` — followed by `dim_x × dim_y` signed bytes in the same order as the text file.

## Project structure

```
NewtonFractals.sln                Visual Studio solution
ConsoleApplication2/
  main.cpp                        Newton iteration, command-line options, output files
  CNum.h / CNum.cpp               complex number class
  Tableau.h / Tableau.cpp         result grid
  newton_calcul.py                polynomial / roots parsing, formatting, engine options, file reading
  NewtonFractalsDrawing.py        Qt interface (PySide6 + pyqtgraph)
```

## Limits

- Zooming stops when the visible width falls below about 10⁻¹² of the coordinate
  magnitude: beyond that, `double` precision can no longer tell neighbouring pixels apart.
- Polynomial degree is limited to 20; root colours repeat after 12 roots.
- Points closer than a small threshold to a root are assigned to it (0.1, reduced
  automatically when roots are close to each other).
