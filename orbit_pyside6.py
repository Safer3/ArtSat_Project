"""
Orbital simulation integrated into PySide6 via QOpenGLWidget.
Dependencies: PySide6, PyOpenGL, numpy
    pip install PySide6 PyOpenGL PyOpenGL_accelerate numpy
"""

import sys, os
import math
import numpy as np

from PySide6.QtCore import Qt, QTimer, QElapsedTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QSlider, QLabel, QPushButton, QGroupBox,
    QDoubleSpinBox, QFormLayout, QSizePolicy
)
from PySide6.QtGui import QFont, QColor, QImage
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import *
from OpenGL.GLU import *

def resource_path(relative_path):
    """ Получение абсолютного пути к ресурсу. Работает и в обычном режиме, и в собранном PyInstaller'ом .exe """
    try:
        # PyInstaller создает временную папку и хранит ее путь в sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Если мы не в собранном .exe, значит, мы в режиме разработки
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ---------------------------------------------------------------------------
# Orbital math
# ---------------------------------------------------------------------------

def solve_kepler(M: float, e: float, tol: float = 1e-8) -> float:
    E = M
    for _ in range(50):
        dE = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= dE
        if abs(dE) < tol:
            break
    return E


def orbital_to_cartesian(a, e, i, Omega, omega, nu):
    r = a * (1 - e**2) / (1 + e * math.cos(nu))
    x_orb = r * math.cos(nu)
    y_orb = r * math.sin(nu)

    cos_O, sin_O = math.cos(Omega), math.sin(Omega)
    cos_i, sin_i = math.cos(i),     math.sin(i)
    cos_w, sin_w = math.cos(omega), math.sin(omega)

    x = (cos_O*cos_w - sin_O*sin_w*cos_i)*x_orb + (-cos_O*sin_w - sin_O*cos_w*cos_i)*y_orb
    y = (sin_O*cos_w + cos_O*sin_w*cos_i)*x_orb + (-sin_O*sin_w + cos_O*cos_w*cos_i)*y_orb
    z = (sin_w*sin_i)*x_orb + (cos_w*sin_i)*y_orb
    return np.array([x, z, y])   # swap y/z to match original


def build_orbit_strip(a, e, i, Omega, omega, steps=300):
    pts = []
    for nu in np.linspace(0, 2*math.pi, steps):
        pts.append(orbital_to_cartesian(a, e, i, Omega, omega, nu))
    return pts


# ---------------------------------------------------------------------------
# OpenGL viewport
# ---------------------------------------------------------------------------

class OrbitGLWidget(QOpenGLWidget):
    timeScaleChanged = Signal(float)
    SCALE = 1 / 2000.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.earth_texture = None

        # orbital elements
        self.mu    = 398600.4418
        self.a     = 42164.17
        self.e     = 0
        self.i     = math.radians(0)
        self.Omega = math.radians(0)
        self.omega = math.radians(0)
        self.nu0   = math.radians(45)

        E0   = 2 * math.atan2(math.sqrt(1 - self.e) * math.sin(self.nu0/2),
                               math.sqrt(1 + self.e) * math.cos(self.nu0/2))
        self.M0 = E0 - self.e * math.sin(E0)
        self.n  = math.sqrt(self.mu / self.a**3)

        self.time_scale   = 1000
        
        self.sim_time     = 0.0
        self.earth_angle  = 0.0
        self.paused       = False

        # camera (spherical)
        self.cam_dist  = 18.0
        self.cam_theta = 25.0   # elevation deg
        self.cam_phi   = -30.0  # azimuth deg

        self._last_mouse = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # timer
        self._elapsed = QElapsedTimer()
        self._elapsed.start()
        self._last_ms  = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

        self._rebuild_orbit()

    def keyPressEvent(self, event):
        key = event.key()
        new_scale = self.time_scale
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            new_scale = self.time_scale * 1.5
        elif key == Qt.Key_Minus:
            new_scale = self.time_scale / 1.5
        elif key in (Qt.Key_0, Qt.Key_R):
            new_scale = 10.0
        else:
            super().keyPressEvent(event)
            return

        # Ограничиваем диапазоном слайдера
        new_scale = max(1.0, min(80000.0, new_scale))
        if new_scale != self.time_scale:
            self.time_scale = new_scale
            self.timeScaleChanged.emit(self.time_scale)

    # ---- orbit rebuild ----
    def _rebuild_orbit(self):
        self._orbit_pts = build_orbit_strip(
            self.a, self.e, self.i, self.Omega, self.omega)
        #print(self.mu, self.a, self.e, self.i, self.Omega, self.omega, self.nu0)


    # ---- simulation tick ----
    def _tick(self):
        now_ms  = self._elapsed.elapsed()
        dt      = (now_ms - self._last_ms) / 1000.0
        self._last_ms = now_ms

        if not self.paused:
            self.sim_time    += dt * self.time_scale
            self.earth_angle -= math.degrees(self.n) * dt * self.time_scale

        self.update()

    # ---- GL lifecycle ----
    def initializeGL(self):
        glClearColor(0.02, 0.02, 0.06, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glLightfv(GL_LIGHT0, GL_POSITION, [5, 8, -10, 0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.95, 0.85, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.08, 0.08, 0.12, 1.0])

        self._quad = gluNewQuadric()

        # Загрузка текстуры Земли
        #texture_path = "Earth.jpg"   # укажите путь к файлу карты
        texture_path = resource_path("Earth.jpg")
        image = QImage(texture_path)
        if image.isNull():
            print("Не удалось загрузить текстуру Земли, использую цветную заливку")
            self.earth_texture = None
        else:
            image = image.convertToFormat(QImage.Format_RGBA8888)
            # OpenGL требует размеры, кратные степени двойки – можно использовать любую текстуру, но лучше подготовить её заранее
            # В большинстве современных OpenGL это не обязательно, но для совместимости сделаем масштабирование:
            texture_img = image.scaled(1024, 512, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)  # подходящий размер
            w, h = texture_img.width(), texture_img.height()
            data = texture_img.bits().tobytes()

            self.earth_texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.earth_texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            # можно сгенерировать мип-карты (если не хотите вручную):
            from OpenGL.GL import glGenerateMipmap
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)

        # Включим текстурирование для quadric
        if self.earth_texture:
            gluQuadricTexture(self._quad, GL_TRUE)   # теперь gluSphere будет генерировать UV-координаты


        gluQuadricNormals(self._quad, GLU_SMOOTH)



    def resizeGL(self, w, h):
        glViewport(0, 0, w, max(h, 1))

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # ---- projection ----
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        w, h = self.width(), self.height()
        gluPerspective(45.0, w / max(h, 1), 0.1, 500.0)

        # ---- camera ----
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        t  = math.radians(self.cam_theta)
        p  = math.radians(self.cam_phi)
        cx = self.cam_dist * math.cos(t) * math.sin(p)
        cy = self.cam_dist * math.sin(t)
        cz = self.cam_dist * math.cos(t) * math.cos(p)
        gluLookAt(cx, cy, cz, 0, 0, 0, 0, 1, 0)

        # ---- grid ----
        self._draw_grid()

        # ---- orbit path ----
        self._draw_orbit()

        # ---- Earth ----
        self._draw_earth()

        # ---- satellite ----
        self._draw_satellite()

    def _draw_grid(self):
        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glColor4f(0.15, 0.2, 0.35, 0.5)
        glBegin(GL_LINES)
        N, step = 10, 2.0
        for k in range(-N, N+1):
            glVertex3f(k*step, 0, -N*step)
            glVertex3f(k*step, 0,  N*step)
            glVertex3f(-N*step, 0, k*step)
            glVertex3f( N*step, 0, k*step)
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_orbit(self):
        glDisable(GL_LIGHTING)
        glLineWidth(1.5)
        glColor4f(0.3, 0.65, 1.0, 0.7)
        glBegin(GL_LINE_LOOP)
        for pt in self._orbit_pts:
            glVertex3f(*(pt * self.SCALE))
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_earth(self):
        glPushMatrix()
        glRotatef(self.earth_angle, 0, 1, 0)
        glRotatef(90, 1, 0, 0)   # компенсация поворота текстуры

        if self.earth_texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.earth_texture)
            # Материал и освещение для текстуры – можно отключить цветовой материал или оставить как есть
            glEnable(GL_COLOR_MATERIAL)
            glColor3f(1, 1, 1)   # белый цвет, чтобы текстура отображалась полностью
        else:
            # fallback – цветная сфера как раньше
            glColor3f(0.15, 0.4, 0.8)

        gluSphere(self._quad, 2.0, 96, 96)

        if self.earth_texture:
            glDisable(GL_TEXTURE_2D)

        # Атмосферное свечение (без текстуры)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glColor4f(0.2, 0.5, 1.0, 0.06)
        # Придётся временно отключить текстуру для атмосферы:
        if self.earth_texture:
            glDisable(GL_TEXTURE_2D)
        gluSphere(self._quad, 2.18, 32, 32)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)

        glPopMatrix()

    def _draw_satellite(self):
        M   = self.M0 + self.n * self.sim_time
        E   = solve_kepler(M, self.e)
        nu  = 2 * math.atan2(
            math.sqrt(1 + self.e) * math.sin(E/2),
            math.sqrt(1 - self.e) * math.cos(E/2))
        pos = orbital_to_cartesian(self.a, self.e, self.i,
                                   self.Omega, self.omega, nu) * self.SCALE

        # dashed line to planet
        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glColor4f(1.0, 0.5, 0.2, 0.35)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(*pos)
        glEnd()
        glEnable(GL_LIGHTING)

        # satellite body
        glPushMatrix()
        glTranslatef(*pos)
        glColor3f(1.0, 0.35, 0.1)
        gluSphere(self._quad, 0.18, 16, 16)

        # solar panels (two flat boxes)
        glDisable(GL_LIGHTING)
        glColor4f(0.2, 0.4, 1.0, 0.9)
        for sign in (-1, 1):
            glPushMatrix()
            glTranslatef(sign * 0.45, 0, 0)
            glScalef(0.35, 0.04, 0.18)
            self._draw_box()
            glPopMatrix()
        glEnable(GL_LIGHTING)
        glPopMatrix()

    def _draw_box(self):
        verts = [
            (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
            (-1,-1, 1),(1,-1, 1),(1,1, 1),(-1,1, 1),
        ]
        faces = [
            (0,1,2,3),(4,5,6,7),(0,1,5,4),
            (2,3,7,6),(0,3,7,4),(1,2,6,5),
        ]
        glBegin(GL_QUADS)
        for f in faces:
            for idx in f:
                glVertex3fv(verts[idx])
        glEnd()

    # ---- mouse ----
    def mousePressEvent(self, ev):
        self._last_mouse = ev.position()

    def mouseMoveEvent(self, ev):
        if self._last_mouse and ev.buttons() & Qt.LeftButton:
            dx = -(ev.position().x() - self._last_mouse.x())
            dy = -(ev.position().y() - self._last_mouse.y())
            self.cam_phi   += dx * 0.4
            self.cam_theta  = max(-89, min(89, self.cam_theta - dy * 0.4))
        self._last_mouse = ev.position()

    def wheelEvent(self, ev):
        delta = ev.angleDelta().y()
        self.cam_dist = max(4.0, min(60.0, self.cam_dist - delta * 0.02))

    # ---- public API ----
    def set_time_scale(self, v: float):
        self.time_scale = v

    def set_paused(self, p: bool):
        self.paused = p

    # def set_orbital_elements(self, a=None, e=None, i_deg=None,
    #                           Omega_deg=None, omega_deg=None):
    #     if a is not None:      self.a     = a
    #     if e is not None:      self.e     = max(0.0, min(0.99, e))
    #     if i_deg is not None:  self.i     = math.radians(i_deg)
    #     if Omega_deg is not None: self.Omega = math.radians(Omega_deg)
    #     if omega_deg is not None: self.omega = math.radians(omega_deg)
    #     self.n  = math.sqrt(self.mu / self.a**3)
    #     self._rebuild_orbit()


# ---------------------------------------------------------------------------
# Control panel
# ---------------------------------------------------------------------------

class ControlPanel(QWidget):
    def __init__(self, gl: OrbitGLWidget, parent=None):
        super().__init__(parent)
        self.gl = gl
        self._paused = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        title = QLabel("ORBIT CONTROL")
        title.setFont(QFont("Courier New", 11, QFont.Bold))
        title.setStyleSheet("color:#5bf; letter-spacing:2px;")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # --- Playback ---
        pb_box = QGroupBox("Playback")
        pb_lay = QVBoxLayout(pb_box)

        self._pause_btn = QPushButton("⏸  PAUSE")
        self._pause_btn.setCheckable(True)
        self._pause_btn.clicked.connect(self._toggle_pause)
        pb_lay.addWidget(self._pause_btn)

        # time scale slider
        ts_row = QHBoxLayout()
        ts_row.addWidget(QLabel("Speed"))
        self._ts_slider = QSlider(Qt.Horizontal)
        self._ts_slider.setRange(1, 80000)
        self._ts_slider = QSlider(Qt.Horizontal)
        self._ts_lbl = QLabel("×10")
        self._ts_slider.valueChanged.connect(self._on_timescale)
        ts_row.addWidget(self._ts_slider)
        ts_row.addWidget(self._ts_lbl)
        pb_lay.addLayout(ts_row)
        root.addWidget(pb_box)


        def set_time_scale_value(self, value):
            # Обновляет положение слайдера и надпись без вызова valueChanged
            self._ts_slider.blockSignals(True)
            self._ts_slider.setValue(int(value))
            self._ts_slider.blockSignals(False)
            self._ts_lbl.setText(f"×{int(value)}")

        # --- Orbital elements ---
        # oe_box = QGroupBox("Orbital Elements")
        # oe_form = QFormLayout(oe_box)

        def spin(lo, hi, val, step=1.0, dec=1):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            s.setDecimals(dec)
            return s

        # self._sp_a     = spin(7000, 50000, 26560, 500, 0)
        # self._sp_e     = spin(0.0,  0.99,  0.74,  0.01, 3)
        # self._sp_i     = spin(0,    180,   63.4,  1.0)
        # self._sp_Omega = spin(0,    360,   90.0,  1.0)
        # self._sp_omega = spin(0,    360,   270.0, 1.0)

        # oe_form.addRow("a (km)",  self._sp_a)
        # oe_form.addRow("e",       self._sp_e)
        # oe_form.addRow("i (°)",   self._sp_i)
        # oe_form.addRow("Ω (°)",   self._sp_Omega)
        # oe_form.addRow("ω (°)",   self._sp_omega)

        # apply_btn = QPushButton("Apply")
        # 
        # apply_btn.clicked.connect(self._apply_elements)
        # oe_form.addRow(apply_btn)
        # root.addWidget(oe_box)

        # --- Camera hint ---
        hint = QLabel("LMB drag — rotate\nScroll — zoom")
        hint.setStyleSheet("color:#888; font-size:10px;")
        hint.setAlignment(Qt.AlignCenter)
        root.addWidget(hint)

        root.addStretch()

        # styling
        self.setStyleSheet("""
            QWidget          { background:#0d1117; color:#cdd9e5; font-family:'Courier New',monospace; font-size:11px; }
            QGroupBox        { border:1px solid #2a3a4a; border-radius:4px; margin-top:8px; padding-top:4px; }
            QGroupBox::title { subcontrol-origin:margin; left:8px; color:#5bf; }
            QPushButton      { background:#1a2a3a; border:1px solid #2a5a8a; border-radius:3px;
                               padding:4px 8px; color:#7df; }
            QPushButton:checked { background:#0a1a2a; color:#f80; border-color:#f80; }
            QPushButton:hover   { background:#2a3a4a; }
            QSlider::groove:horizontal { height:4px; background:#1e2e3e; border-radius:2px; }
            QSlider::handle:horizontal { width:12px; height:12px; margin:-4px 0;
                                         background:#4af; border-radius:6px; }
            QDoubleSpinBox   { background:#111a22; border:1px solid #2a4a6a; border-radius:3px;
                               padding:2px; color:#adf; }
        """)

    def _toggle_pause(self, checked):
        self._paused = checked
        self._pause_btn.setText("▶  RESUME" if checked else "⏸  PAUSE")
        self.gl.set_paused(checked)

    def _on_timescale(self, val):
        self._ts_lbl.setText(f"×{val}")
        self.gl.set_time_scale(float(val))

    # def _apply_elements(self):
    #     self.gl.set_orbital_elements(
    #         a=self._sp_a.value(),
    #         e=self._sp_e.value(),
    #         i_deg=self._sp_i.value(),
    #         Omega_deg=self._sp_Omega.value(),
    #         omega_deg=self._sp_omega.value(),
    #     )


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orbital Simulation")
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.gl = OrbitGLWidget()
        self.gl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.panel = ControlPanel(self.gl)
        self.gl.timeScaleChanged.connect(self.panel.set_time_scale_value)
        self.panel.setFixedWidth(230)

        h.addWidget(self.gl)
        h.addWidget(self.panel)

        self.setStyleSheet("QMainWindow { background:#0d1117; }")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
