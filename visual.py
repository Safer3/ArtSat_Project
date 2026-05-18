import numpy as np
import matplotlib.colors as mcolors
from noise_fast import warp_and_fbm   # ← скомпилированный Cython-модуль
 
from PySide6.QtCore import QTimer, QSize, Qt, QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget


latest_values = [0.0] * 5

def get_d(values):
    global latest_values
    latest_values = values
    return latest_values

conn = None

# -----------------------------
# IMAGE SETTINGS
# -----------------------------
W, H = 280, 280
BASE_SCALE = 0.015

# Предварительно создаём сетку (float64 — требование Cython-модуля)
x = np.arange(W, dtype=np.float64) * BASE_SCALE
y = np.arange(H, dtype=np.float64) * BASE_SCALE
xx, yy = np.meshgrid(x, y)          # shape (H, W), C-contiguous

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
# GENERATE FRAME
# Теперь warp + fbm — один вызов в скомпилированном C-коде
# -----------------------------
def generate_frame(t: float, params: dict) -> np.ndarray:
    return warp_and_fbm(
        xx, yy,
        t * params["speed"],
        params["warp"],
        params["octaves"],
    )

# -----------------------------
# FIELD → RGB uint8
# -----------------------------

def field_to_rgb(
    field: np.ndarray,
    hue: float,
    sat: float,
    contrast: float,
) -> np.ndarray:
    fmin = field.min()
    fmax = field.max()
    norm = (field - fmin) / (fmax - fmin + 1e-6)
    norm = np.clip((norm - 0.5) * contrast + 0.5, 0.0, 1.0)
 
    hsv = np.empty((H, W, 3), dtype=np.float32)
    hsv[..., 0] = (hue + norm) % 1.0
    hsv[..., 1] = sat
    hsv[..., 2] = norm
 
    rgb_float = mcolors.hsv_to_rgb(hsv)                  # float32 [0..1]
    return (rgb_float * 255).astype(np.uint8)             # uint8  [0..255]
 


def get_measurements():
    return latest_values


# -----------------------------
# QT WIDGET — OpenGL-рендеринг
# -----------------------------
class NoiseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.setFixedSize(W, H)
        self._rgb = np.zeros((H, W, 3), dtype=np.uint8)


    # def resizeEvent(self, event):
    #     # Находим минимальную сторону
    #     min_size = min(event.size().width(), event.size().height())
    #     self.resize(QSize(min_size, min_size))
    #     super().resizeEvent(event)

        
 
    def set_frame(self, rgb_uint8: np.ndarray):
        """Принимает uint8 массив (H, W, 3) и запрашивает перерисовку."""
        self._rgb = np.ascontiguousarray(rgb_uint8)
        self.update()                                     # schedules paintGL
 
    def paintEvent(self, event):
        img = QImage(
        self._rgb.data,
        W, H,
        W * 3,
        QImage.Format.Format_RGB888,
    )

        painter = QPainter(self)

        # фон
        painter.fillRect(self.rect(), self.palette().window())

        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        ww = self.width()
        wh = self.height()

        size = min(ww, wh)

        x = (ww - size) // 2
        y = (wh - size) // 2

        target = QRect(x - 1, y - 1, size + 2, size + 2)

        painter.drawImage(target, img)

        painter.end()
 
 
# -----------------------------
# ФАБРИЧНАЯ ФУНКЦИЯ
# -----------------------------
def create_animation_widget() -> NoiseWidget:
    widget = NoiseWidget()
    frame  = {"value": 0}
 
    def update_frame():
        frame["value"] += 1
 
        raw    = get_measurements()
        values = [sensors[i].update(raw[i]) for i in range(5)]
 
        params = {
            "speed":   0.2, # + values[0] * 1.0,
            "octaves": int(2 + values[0] * 3),
            "warp":    values[1] * 1.5,
        }
 
        hue        = values[2]
        saturation = 0.6 + values[3] * 0.4
        contrast   = 1.0 + values[4] * 2.0
 
        field = generate_frame(frame["value"] * 0.03, params)
        rgb   = field_to_rgb(field, hue, saturation, contrast)
 
        widget.set_frame(rgb)
 
    timer = QTimer()
    timer.timeout.connect(update_frame)
    timer.start(30)          # ~33 FPS
 
    widget.timer = timer     # удерживаем ссылку, чтобы не собрал GC
    return widget