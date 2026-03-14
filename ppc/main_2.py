import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as mcolors
from noise import snoise3
import threading
import time
from multiprocessing.connection import Client

# -----------------------------
# CONNECTION
# -----------------------------
ADDRESS = ('localhost', 6000)
AUTHKEY = b'secret'

latest_values = [0.0] * 7
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

# -----------------------------
# CONNECTION LOOP
# -----------------------------
def connection_loop():
    global latest_values, conn

    while True:
        try:
            print("Подключение к GUI...")
            conn = Client(ADDRESS, authkey=AUTHKEY)
            print("Подключено!")

            while True:
                latest_values = conn.recv()

        except Exception:
            print("Переподключение...")
            time.sleep(1)

def get_measurements():
    return latest_values

# -----------------------------
# MATPLOTLIB SETUP
# -----------------------------
fig, ax = plt.subplots(figsize=(6, 6))
image = ax.imshow(np.zeros((H, W, 3), dtype=np.float32), animated=True)
ax.axis("off")

# -----------------------------
# UPDATE LOOP
# -----------------------------
def update(frame):
    raw = get_measurements()
    values = [sensors[i].update(raw[i]) for i in range(7)]

    params = {
        "zoom": 1.0,
        "speed": 0.2 + values[1] * 1.0,
        "octaves": int(2 + values[2] * 3),
        "warp": values[3] * 1.5
    }

    hue = values[4]
    saturation = 0.6 + values[5] * 0.4
    contrast = 1.0 + values[6] * 2.0

    field = generate_frame(frame * 0.03, params)
    rgb = field_to_rgb(field, hue, saturation, contrast)

    image.set_data(rgb)
    return [image]

# -----------------------------
# START
# -----------------------------
threading.Thread(target=connection_loop, daemon=True).start()

ani = animation.FuncAnimation(
    fig,
    update,
    interval=30,
    blit=True,
    cache_frame_data=False
)

plt.show()