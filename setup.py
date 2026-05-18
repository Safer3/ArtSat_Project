# setup.py
import sys
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

# Флаги OpenMP отличаются на Linux/Mac и Windows
if sys.platform == "win32":
    omp_compile = ["/openmp"]
    omp_link    = []
else:
    omp_compile = ["-fopenmp"]
    omp_link    = ["-fopenmp"]

ext = Extension(
    name="noise_fast",
    sources=["noise_fast.pyx"],
    include_dirs=[np.get_include()],
    extra_compile_args=["-O3", "-march=native", "-ffast-math"] + omp_compile,
    extra_link_args=omp_link,
)

setup(
    name="noise_fast",
    ext_modules=cythonize(
        [ext],
        compiler_directives={
            "language_level": "3",
            "boundscheck":    False,
            "wraparound":     False,
            "cdivision":      True,
        },
        annotate=True,
    ),
)
