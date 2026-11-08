# User guide

Detailed documentation of Newton Fractals: features, installation, controls, formula
syntax, command-line engine and output formats. For an overview, see the
[README](../README.md).

## Contents

- [Features](#features)
- [Requirements and build](#requirements)
- [Usage](#usage)
- [Command-line engine](#command-line-engine)
- [Output formats](#output-formats)
- [Limits](#limits)

## Features

**Navigation**

- Home page with a preview of each visualization; switch between them from the
  *Visualisations* menu, the *← Accueil* button or with `Ctrl+0` … `Ctrl+4`.
  Each page keeps its state when you switch to another one.

**Common to both fractals**

- Mouse-wheel zoom and drag to pan, with automatic full-resolution recomputation of the
  visible area once you stop moving; the computation runs in the background.
- **Deep zoom** down to about 10⁻¹³ of the coordinate magnitude (the limit of `double`
  precision), with bounds shown in scientific notation.
- Value under the mouse in the status bar, PNG export at the computed resolution,
  last parameters and result remembered between sessions.

**Newton fractals**

- **Any polynomial**, real or complex coefficients, degree 1 to 20: type an expression
  such as `z^3 - 2z + 2`, `(z-1)(z+2i)` or `z^3 - (1 + 2i)z + 1`…
- …**or give the roots directly** (`1 ; -1 ; 0.5+2i`): the polynomial is then the product
  of (z − root). Repeating a root makes it a multiple root.
- Legend with the value of each root and the share of the image it covers.
- Horner evaluation of p and p′ in a single pass, OpenMP multithreading — about
  20–30 ms for a 1000 × 1000 image on a recent CPU.

**Mandelbrot set**

- Smooth (continuous) iteration count for colour gradients without banding; points of
  the main cardioid and period-2 bulb are detected without iterating.
- Famous places to visit in one click (Seahorse Valley, Elephant Valley, a
  mini-Mandelbrot, a 10⁻¹⁰ deep zoom…).
- Maximum number of iterations adapted automatically to the zoom depth.
- Six colour palettes, colour density and offset: changes are applied instantly,
  without recomputing.
- About 10–15 ms for the full view at 1000 × 1000 with 500 iterations.

**2D graphs**

- **Equations in x and y** (implicit curves) such as `x² + y² = 4`, `x²/9 + y²/4 = 1`,
  `y² = x³ - x` or `x = 2`, traced with the marching squares algorithm on the visible
  area (sharp at any zoom level, a few milliseconds per curve).
- Several functions at once, each with its colour, visibility toggle and legend entry;
  syntax errors are shown under the formula as you type.
- Curves resampled on every zoom or pan, so they stay sharp; vertical asymptotes
  (`tan(x)`, `1/x`) are cut cleanly.
- Any letter other than `x` (`a`, `b`, `k`…) becomes a **parameter** with its own slider,
  which can be **animated** (▶).
- Axes through the origin, grid, orthonormal frame, "fit to curves", coordinates and
  function values under the mouse, with a dot following the nearest curve.

**3D surfaces**

- Several surfaces z = f(x, y), lit (shaded), coloured per surface or by height,
  optional wireframe, axes and grid; drag to rotate, wheel to zoom.
- **Equations in x, y and z** (implicit surfaces) such as `x² + y² + z² = 9` (sphere),
  `(sqrt(x² + y²) - 3)² + z² = 1` (torus), `x² + y² - z² = 1` (hyperboloid) or
  `x² + y² = 4` (cylinder), extracted with the marching cubes algorithm on a 120³ grid
  (about 0.15 s per surface).
- Parameters with animated sliders, as in 2D; while a slider moves, equations are drawn
  as a fast preview (56³ grid, ~10 frames per second) and recomputed at full resolution
  when it stops.
- Adjustable domain, resolution (points per side) and z clipping; holes in the domain of
  definition (e.g. `sqrt(4 - x² - y²)`) are left transparent.

Functions, parameters and display settings of the 2D and 3D pages are remembered
between sessions.

## Requirements

- **C++ compiler** with OpenMP: Visual Studio 2022 (MSVC v143) or g++ (e.g. MSYS2 UCRT64).
- **Python 3.11+** with `numpy`, `PySide6`, `pyqtgraph` and `PyOpenGL` (PyOpenGL is only
  needed for the 3D surfaces page, which explains how to install it if it is missing):

```bash
python -m pip install numpy pyside6 pyqtgraph PyOpenGL
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

The window opens maximized on the home page; click a card (or press `Ctrl+1` …
`Ctrl+4`) to open a visualization. It finds the compiled engine automatically
(`main.exe` built with g++, or the Visual Studio `Release`/`Debug` executable, whichever
is newest); use `--exe path\to\program.exe` to choose another one.

```bash
python NewtonFractalsDrawing.py --vue graphe2d     # open a page directly: accueil, newton, mandelbrot, graphe2d, surfaces3d
python NewtonFractalsDrawing.py --help
```

| Control | Action |
|---|---|
| `Ctrl+0` | Home page |
| `Ctrl+1` / `Ctrl+2` / `Ctrl+3` / `Ctrl+4` | Newton fractals / Mandelbrot set / 2D graphs / 3D surfaces |
| Mouse wheel | Zoom (around the cursor in 2D) |
| Click and drag | Pan (2D), rotate (3D) |
| Middle-click drag or `Ctrl` + drag | Pan (3D) |
| `H` | Fractals: back to the view of the computed image |
| `Enter` (in a field) | Fractals: compute · 2D/3D: add the typed function |
| `Ctrl+Q` | Quit |

With *Recalcul automatique* checked (default), the fractal pages recompute the visible
area 0.35 s after you stop zooming or panning, so details appear instead of enlarged pixels.

The right-hand panel of each fractal page (labels are in French):

| Section | Newton fractals | Mandelbrot set |
|---|---|---|
| Top | *Polynôme*: `p(z)` / *Racines* switch, the polynomial or its roots, *Exemple ▸* | *Lieux célèbres*: famous places |
| *Image* | width and height in pixels | width and height in pixels |
| *Fenêtre du plan complexe* | Re min / max, Im min / max | Re min / max, Im min / max |
| Bottom | *Convergence*: precision `eps`, maximum iterations | *Itérations* (with *Adapter au zoom*), *Couleurs*: palette, density, offset |

Buttons: *Recalculer la vue affichée* (recompute the visible area), *Pixels carrés*
(adjust the height so pixels are square), *Par défaut* (reset), *Export PNG*, *Calculer*.

### Polynomial syntax (Newton fractals)

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

### Function syntax (2D graphs and 3D surfaces)

Type one function per line in the *Fonctions* / *Surfaces* panel; it is drawn as you type.

| Input | Meaning |
|---|---|
| `sin(x)`, `y = x^2 - 3`, `f(x) = 2x exp(-x)` | 2D: a function of `x` (a name like `f(x) =` is optional) |
| `x^2 + y^2 = 4`, `y^2 = x^3 - x`, `sin(x) = cos(y)`, `x = 2` | 2D: an equation in `x` and `y` — any `=` that does not simply define `y` or `f(x)` |
| `sin(x) cos(y)`, `z = x^2 - y^2`, `g(x, y) = …` | 3D: a function of `x` and `y` |
| `x^2 + y^2 + z^2 = 9`, `x^2 + y^2 = 4`, `y = x^2` | 3D: an equation in `x`, `y` and `z` — any `=` that does not simply define `z` or `f(x, y)` |
| `x^2`, `x**2`, `x²` | powers |
| `2x`, `x sin(x)`, `(x-1)(x+1)`, `2pi x` | implicit multiplication |
| `a sin(b x)` | any other single letter is a parameter with a slider (default 1, range −10…10) |
| `pi` or `π`, `e` | constants |

Functions: `sin cos tan asin acos atan sinh cosh tanh exp ln log` (base 10) `log2 sqrt
cbrt abs floor ceil round sign`. Values outside the domain of definition (`ln(-1)`,
`1/0`…) are simply not drawn.

### Command-line engine

`main.exe` can also be used on its own. Without options it computes the default Newton
fractal (z³ − 2z + 2 on [−0.3, 0.3]²), writes `results.txt` and opens the interface; the
Newton page shows that result when you open it.
Options (names are in French):

| Option | Description |
|---|---|
| `--taille W H` | image size in pixels (default 1000 1000) |
| `--bornes MIN_X MAX_X MIN_Y MAX_Y` | area of the complex plane (default −2 2 −2 2) |
| `--iterations N` | maximum number of iterations (default 50) |
| `--eps EPS` | Newton: convergence precision (default 1e-6) |
| `--coefs N re1 im1 … reN imN` | Newton: polynomial coefficients, from highest degree to constant term |
| `--racines N re1 im1 … reN imN` | Newton: roots of the polynomial (required with `--coefs`); their order gives the indices 1…N in the output |
| `--mandelbrot` | compute the Mandelbrot set instead (requires `--binaire`) |
| `--binaire FILE` | write a binary file instead of `results.txt` |
| `--aide` | show help |

Examples:

```bash
# Newton fractal of z^3 - 1 on [-2, 2]^2
main.exe --taille 800 800 --bornes -2 2 -2 2 --coefs 4 1 0 0 0 0 0 -1 0 --racines 3 1 0 -0.5 0.8660254037844386 -0.5 -0.8660254037844386

# Mandelbrot set, full view
main.exe --mandelbrot --taille 1000 800 --bornes -2.5 1 -1.4 1.4 --iterations 500 --binaire mandelbrot.bin
```

### Output formats

All binary files start with an 8-byte header — `dim_x` and `dim_y` as little-endian
`int32` — followed by one value per pixel, x-major (all y values for the first x, then
the next x…).

- **Newton**, `results.txt`: one line per x value, `dim_y` space-separated integers per
  line. Each value is the index (1…N) of the root reached, or `-1` if Newton's method did
  not converge to a root within the iteration limit.
- **Newton**, `--binaire`: the same values as signed bytes (`int8`).
- **Mandelbrot**, `--binaire`: one `float32` per pixel — the smooth iteration count
  before |z| exceeds the escape radius, or `-1` for points that did not escape (inside
  the set).

## Limits

- Zooming stops when the visible width falls below about 10⁻¹² of the coordinate
  magnitude: beyond that, `double` precision can no longer tell neighbouring pixels apart.
- Newton: polynomial degree is limited to 20; root colours repeat after 12 roots. Points
  closer than a small threshold to a root are assigned to it (0.1, reduced automatically
  when roots are close to each other).
- Mandelbrot: very deep zooms need many iterations; the automatic setting goes up to
  about 5 500 iterations at 10⁻¹².
- 2D: explicit functions y = f(x) and equations in x and y (no parametric curves or
  points yet). An equation is drawn where its two sides are equal on a grid of about one
  point every 2.5 pixels: details smaller than that, or curves where the two sides touch
  without crossing (e.g. `(x² + y² - 4)² = 0`), may be missed.
- 3D: explicit surfaces z = f(x, y) and equations in x, y and z (no parametric surfaces
  yet). Surfaces are limited to z between ± the "z entre ±" setting, which is also the
  z extent of the grid used for equations; as in 2D, details smaller than a grid cell
  (1/120 of the domain) or surfaces that touch zero without crossing may be missed.
- Inside the plotting area, only plain Qt graphics items are used (curves, axes, fractal
  images): pyqtgraph's own plot items do not render with the PySide6 6.9 build of MSYS2.
