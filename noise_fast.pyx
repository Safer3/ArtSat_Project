# noise_fast.pyx
# cython: boundscheck=False, wraparound=False, cdivision=True, nonecheck=False

import numpy as np
cimport numpy as np
from libc.math cimport floor, fabs
from cython.parallel cimport prange
from openmp cimport omp_set_num_threads, omp_get_max_threads

# ─────────────────────────────────────────
# Встроенная реализация Simplex Noise 3D
# (не требует внешней библиотеки noise)
# ─────────────────────────────────────────

cdef int PERM[512]
cdef int GRAD3[12][3]

def _init_tables():

    # Ограничить число потоков OpenMP (например, 4)
    cdef int cpu_count = omp_get_max_threads()  # максимальное доступное
    omp_set_num_threads(2) #(max(1, cpu_count - 3))

    """Инициализация таблиц перестановок (вызвать один раз при импорте)"""
    cdef int p[256]
    p_list = [
        151,160,137,91,90,15,131,13,201,95,96,53,194,233,7,225,
        140,36,103,30,69,142,8,99,37,240,21,10,23,190,6,148,
        247,120,234,75,0,26,197,62,94,252,219,203,117,35,11,32,
        57,177,33,88,237,149,56,87,174,20,125,136,171,168,68,175,
        74,165,71,134,139,48,27,166,77,146,158,231,83,111,229,122,
        60,211,133,230,220,105,92,41,55,46,245,40,244,102,143,54,
        65,25,63,161,1,216,80,73,209,76,132,187,208,89,18,169,
        200,196,135,130,116,188,159,86,164,100,109,198,173,186,3,64,
        52,217,226,250,124,123,5,202,38,147,118,126,255,82,85,212,
        207,206,59,227,47,16,58,17,182,189,28,42,223,183,170,213,
        119,248,152,2,44,154,163,70,221,153,101,155,167,43,172,9,
        129,22,39,253,19,98,108,110,79,113,224,232,178,185,112,104,
        218,246,97,228,251,34,242,193,238,210,144,12,191,179,162,241,
        81,51,145,235,249,14,239,107,49,192,214,31,181,199,106,157,
        184,84,204,176,115,121,50,45,127,4,150,254,138,236,205,93,
        222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180
    ]
    grad3_list = [
        [1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
        [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
        [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]
    ]
    for i in range(256):
        PERM[i] = p_list[i]
        PERM[i + 256] = p_list[i]
    for i in range(12):
        for j in range(3):
            GRAD3[i][j] = grad3_list[i][j]

_init_tables()


cdef inline double _dot3(int g[3], double x, double y, double z) nogil:
    return g[0]*x + g[1]*y + g[2]*z

cdef inline double _fade(double t) nogil:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

cdef inline double _lerp(double t, double a, double b) nogil:
    return a + t * (b - a)


cdef double _simplex3(double xin, double yin, double zin) nogil:
    """Быстрый Simplex Noise 3D без GIL"""
    cdef double F3 = 1.0 / 3.0
    cdef double G3 = 1.0 / 6.0
    cdef double s, t, x0, y0, z0
    cdef int i, j, k, i1, j1, k1, i2, j2, k2
    cdef double x1, y1, z1, x2, y2, z2, x3, y3, z3
    cdef double t0, t1, t2, t3, n0, n1, n2, n3
    cdef int ii, jj, kk, gi0, gi1, gi2, gi3

    s = (xin + yin + zin) * F3
    i = <int>floor(xin + s)
    j = <int>floor(yin + s)
    k = <int>floor(zin + s)

    t = (i + j + k) * G3
    x0 = xin - (i - t)
    y0 = yin - (j - t)
    z0 = zin - (k - t)

    if x0 >= y0:
        if y0 >= z0:   i1,j1,k1, i2,j2,k2 = 1,0,0, 1,1,0
        elif x0 >= z0: i1,j1,k1, i2,j2,k2 = 1,0,0, 1,0,1
        else:          i1,j1,k1, i2,j2,k2 = 0,0,1, 1,0,1
    else:
        if y0 < z0:    i1,j1,k1, i2,j2,k2 = 0,0,1, 0,1,1
        elif x0 < z0:  i1,j1,k1, i2,j2,k2 = 0,1,0, 0,1,1
        else:          i1,j1,k1, i2,j2,k2 = 0,1,0, 1,1,0

    x1 = x0 - i1 + G3
    y1 = y0 - j1 + G3
    z1 = z0 - k1 + G3
    x2 = x0 - i2 + 2.0*G3
    y2 = y0 - j2 + 2.0*G3
    z2 = z0 - k2 + 2.0*G3
    x3 = x0 - 1.0 + 3.0*G3
    y3 = y0 - 1.0 + 3.0*G3
    z3 = z0 - 1.0 + 3.0*G3

    ii = i & 255
    jj = j & 255
    kk = k & 255
    gi0 = PERM[ii + PERM[jj + PERM[kk]]] % 12
    gi1 = PERM[ii+i1 + PERM[jj+j1 + PERM[kk+k1]]] % 12
    gi2 = PERM[ii+i2 + PERM[jj+j2 + PERM[kk+k2]]] % 12
    gi3 = PERM[ii+1  + PERM[jj+1  + PERM[kk+1 ]]] % 12

    t0 = 0.6 - x0*x0 - y0*y0 - z0*z0
    n0 = 0.0 if t0 < 0 else (t0*t0)*(t0*t0) * _dot3(GRAD3[gi0], x0, y0, z0)

    t1 = 0.6 - x1*x1 - y1*y1 - z1*z1
    n1 = 0.0 if t1 < 0 else (t1*t1)*(t1*t1) * _dot3(GRAD3[gi1], x1, y1, z1)

    t2 = 0.6 - x2*x2 - y2*y2 - z2*z2
    n2 = 0.0 if t2 < 0 else (t2*t2)*(t2*t2) * _dot3(GRAD3[gi2], x2, y2, z2)

    t3 = 0.6 - x3*x3 - y3*y3 - z3*z3
    n3 = 0.0 if t3 < 0 else (t3*t3)*(t3*t3) * _dot3(GRAD3[gi3], x3, y3, z3)

    return 32.0 * (n0 + n1 + n2 + n3)


# ─────────────────────────────────────────
# Хелперы для одного пикселя (nogil)
# Cython требует, чтобы все локальные переменные
# внутри prange жили в отдельной cdef-функции
# ─────────────────────────────────────────

cdef double _fbm_pixel(double xi, double yi, double t, int octaves) nogil:
    cdef double val = 0.0
    cdef double amp = 1.0
    cdef double freq = 1.0
    cdef int o
    for o in range(octaves):
        val += amp * _simplex3(xi * freq, yi * freq, t)
        freq *= 2.0
        amp  *= 0.5
    return val


cdef double _warp_fbm_pixel(double xi, double yi, double t,
                             double warp_strength, int octaves) nogil:
    cdef double wx = xi + _simplex3(xi + 100.0, yi,         t) * warp_strength
    cdef double wy = yi + _simplex3(xi,          yi + 100.0, t) * warp_strength
    cdef double val = 0.0
    cdef double amp = 1.0
    cdef double freq = 1.0
    cdef int o
    for o in range(octaves):
        val += amp * _simplex3(wx * freq, wy * freq, t)
        freq *= 2.0
        amp  *= 0.5
    return val


# ─────────────────────────────────────────
# FBM — обход всего массива без GIL
# ─────────────────────────────────────────

def fbm_array(
    np.ndarray[np.float64_t, ndim=2] x not None,
    np.ndarray[np.float64_t, ndim=2] y not None,
    double t,
    int octaves
):
    """
    Vectorised fBm по двумерным массивам x, y.
    Возвращает np.ndarray[float64, 2D] того же размера.
    """
    cdef int rows = x.shape[0]
    cdef int cols = x.shape[1]
    cdef np.ndarray[np.float64_t, ndim=2] out = np.empty((rows, cols), dtype=np.float64)

    cdef int r, c

    for r in prange(rows, nogil=True, schedule='static'):
        for c in range(cols):
            out[r, c] = _fbm_pixel(x[r, c], y[r, c], t, octaves)

    return out


def warp_and_fbm(
    np.ndarray[np.float64_t, ndim=2] x not None,
    np.ndarray[np.float64_t, ndim=2] y not None,
    double t,
    double warp_strength,
    int octaves
):
    """
    Объединяет warp + fbm в один проход — меньше выделений памяти.
    """
    cdef int rows = x.shape[0]
    cdef int cols = x.shape[1]
    cdef np.ndarray[np.float64_t, ndim=2] out = np.empty((rows, cols), dtype=np.float64)

    cdef int r, c

    for r in prange(rows, nogil=True, schedule='static'):
        for c in range(cols):
            out[r, c] = _warp_fbm_pixel(x[r, c], y[r, c], t, warp_strength, octaves)

    return out
