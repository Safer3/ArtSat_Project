import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as mcolors
from noise import snoise3
#import threading
import time


#from multiprocessing.connection import Client

# -----------------------------
# CONNECTION
# -----------------------------
# ADDRESS = ('localhost', 6000)
# AUTHKEY = b'secret'
latest_values = [1.0] * 5
def get_d(values):
    global latest_values
    latest_values = values #[1.0] * 7
    return latest_values
conn = None

# -----------------------------
# IMAGE SETTINGS
# -----------------------------
W, H = 280, 280
BASE_SCALE = 0.015

# Предварительно создаём сетку (ВАЖНО!)
x = np.arange(W) * BASE_SCALE
y = np.arange(H) * BASE_SCALE
xx, yy = np.meshgrid(x, y)

# Векторизованный snoise3
vsnoise3 = np.vectorize(snoise3)

# -----------------------------
# SMOOTH VALUES
# -----------------------------
class SmoothValue:
    def __init__(self, alpha=0.05):
        self.value = 0.0
        self.alpha = alpha

    def update(self, new):
        self.value += self.alpha * (new - self.value)
        return self.value

sensors = [SmoothValue(0.03) for _ in range(7)]

# -----------------------------
# FAST FBM
# -----------------------------
def fbm_fast(x, y, t, octaves):
    value = np.zeros_like(x)
    amp = 1.0
    freq = 1.0

    for _ in range(octaves):
        value += amp * vsnoise3(x * freq, y * freq, t)
        freq *= 2.0
        amp *= 0.5

    return value

# -----------------------------
# FAST WARP
# -----------------------------
def warp_fast(x, y, t, strength):
    dx = vsnoise3(x + 100.0, y, t)
    dy = vsnoise3(x, y + 100.0, t)
    return x + dx * strength, y + dy * strength

# -----------------------------
# GENERATE FRAME (OPTIMIZED)
# -----------------------------
def generate_frame(t, params):
    nx = xx
    ny = yy

    wx, wy = warp_fast(nx, ny, t, params["warp"])
    field = fbm_fast(wx, wy, t * params["speed"], params["octaves"])

    return field

# -----------------------------
# FIELD → RGB
# -----------------------------
def field_to_rgb(field, hue, sat, contrast):
    fmin = field.min()
    fmax = field.max()
    norm = (field - fmin) / (fmax - fmin + 1e-6)

    norm = np.clip((norm - 0.5) * contrast + 0.5, 0, 1)

    hsv = np.empty((H, W, 3), dtype=np.float32)
    hsv[..., 0] = (hue + norm) % 1.0
    hsv[..., 1] = sat
    hsv[..., 2] = norm

    return mcolors.hsv_to_rgb(hsv)



def get_measurements():
    return latest_values


from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.animation as animation





from PySide6.QtCore import QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


def create_animation_widget():
    fig = Figure(figsize=(4, 4))
    ax = fig.add_subplot(111)

    image = ax.imshow(np.zeros((H, W, 3), dtype=np.float32))
    ax.axis("off")

    canvas = FigureCanvas(fig)

    frame = {"value": 0}  # mutable контейнер

    def update_frame():
        frame["value"] += 1

        raw = get_measurements()

        values = [sensors[i].update(raw[i]) for i in range(5)]# ввод полученных данных

        params = {
            "zoom": 1.0,
            "speed": 0.2 + values[0] * 1.0,
            "octaves": int(2),
            "warp": values[1] * 1.5
        }

        hue = values[2]
        saturation = 0.6 + values[3] * 0.4
        contrast = 1.0 + values[4] * 2.0

        field = generate_frame(frame["value"] * 0.03, params)
        rgb = field_to_rgb(field, hue, saturation, contrast)

        image.set_data(rgb)
        canvas.draw_idle()

    # 🔁 Таймер Qt
    timer = QTimer()
    timer.timeout.connect(update_frame)
    timer.start(30)  # ~33 FPS

    # ВАЖНО: сохранить ссылку!
    canvas.timer = timer

    return canvas