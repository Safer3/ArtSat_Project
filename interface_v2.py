from main_2 import create_animation_widget, connection_loop
import threading

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QRadioButton, QGroupBox, QStackedWidget
    
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator  # для ввода только чисел



class OrbitApp(QWidget):

    def __init__(self):
        super().__init__()

        # ---------- ХРАНЕНИЕ ДАННЫХ ----------
        self.input_data = {}   # ввод пользователя
        self.output_data = {}  # результаты

        self.setWindowTitle("Orbital Parameters Calculator")
        self.resize(1000, 560)

        # ---------- СТИЛИ (без изменений) ----------
        self.setStyleSheet("""

QWidget{
    background-color:#e9edf2;
    font-family:Segoe UI;
    font-size:14px;
    color:#1e272e;
}

QGroupBox{
    border:2px solid #c8d0d9;
    border-radius:8px;
    margin-top:12px;
    padding:10px;
    background-color:white;
    font-weight:bold;
}

QGroupBox::title{
    subcontrol-origin: margin;
    left:10px;
    padding:2px 6px;
}

QLabel{
    font-size:14px;
    color:#2f3640;
}

QLineEdit{
    background-color:#f4f6f9;
    border:2px solid #c8d0d9;
    border-radius:6px;
    padding:6px;
}

QLineEdit:focus{
    border:2px solid #3b82f6;
    background-color:white;
}

QPushButton{
    background-color:#2563eb;
    color:white;
    border:none;
    border-radius:8px;
    padding:10px;
    font-size:15px;
    font-weight:bold;
}

QPushButton:hover{
    background-color:#1d4ed8;
}

QRadioButton{
    font-size:14px;
    padding:4px;
}
                           
QRadioButton::indicator {
    width:16px;
    height:16px;
}

QRadioButton::indicator:unchecked {
    border:2px solid #555;
    border-radius:8px;
    background:white;
}

QRadioButton::indicator:checked {
    border:2px solid black;
    border-radius:8px;
    background:black;
}                           
""")

        main_layout = QHBoxLayout()

        # ---------- ЛЕВАЯ ЧАСТЬ ----------
        left_layout = QVBoxLayout()

        mode_group = QGroupBox("Режим работы")
        mode_layout = QHBoxLayout()

        self.mode1 = QRadioButton("По векторам состояния")
        self.mode2 = QRadioButton("По орбитальным элементам")

        self.mode1.setChecked(True)

        mode_layout.addWidget(self.mode1)
        mode_layout.addWidget(self.mode2)
        mode_group.setLayout(mode_layout)

        left_layout.addWidget(mode_group)

        # переключаемые интерфейсы
        self.stack = QStackedWidget()
        self.stack.addWidget(self.mode1_ui())
        self.stack.addWidget(self.mode2_ui())

        left_layout.addWidget(self.stack)

        # кнопка
        self.calc_button = QPushButton("Рассчитать")
        left_layout.addWidget(self.calc_button)

        # ---------- ПРАВАЯ ЧАСТЬ ----------
        right_layout = QVBoxLayout()

        image_box = QGroupBox("Визуализация орбиты")
        image_layout = QVBoxLayout()

        # self.image = QLabel("Здесь будет изображение орбиты")     by_Besolea
        # self.image.setAlignment(Qt.AlignCenter)

        self.canvas = create_animation_widget()
        image_layout.addWidget(self.canvas)

        # image_layout.addWidget(self.image)
        image_box.setLayout(image_layout)

        right_layout.addWidget(image_box)

        # ---------- СБОРКА ----------
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)

        # ---------- СОБЫТИЯ ----------
        self.mode1.toggled.connect(self.switch_mode)
        self.calc_button.clicked.connect(self.collect_data)

    # ---------- ВАЛИДАТОР ----------
    def set_validator(self, field):
        validator = QDoubleValidator()
        field.setValidator(validator)

    # ---------- РЕЖИМ 1 ----------
    def mode1_ui(self):

        widget = QWidget()
        layout = QVBoxLayout()

        coord = QGroupBox("Координаты спутника (км)")
        grid = QGridLayout()

        self.x = QLineEdit()
        self.y = QLineEdit()
        self.z = QLineEdit()

        self.set_validator(self.x)
        self.set_validator(self.y)
        self.set_validator(self.z)

        grid.addWidget(QLabel("x"),0,0)
        grid.addWidget(self.x,0,1)
        grid.addWidget(QLabel("y"),1,0)
        grid.addWidget(self.y,1,1)
        grid.addWidget(QLabel("z"),2,0)
        grid.addWidget(self.z,2,1)

        coord.setLayout(grid)
        layout.addWidget(coord)

        vel = QGroupBox("Скорость (км/с)")
        grid2 = QGridLayout()

        self.vx = QLineEdit()
        self.vy = QLineEdit()
        self.vz = QLineEdit()

        self.set_validator(self.vx)
        self.set_validator(self.vy)
        self.set_validator(self.vz)

        grid2.addWidget(QLabel("vx"),0,0)
        grid2.addWidget(self.vx,0,1)
        grid2.addWidget(QLabel("vy"),1,0)
        grid2.addWidget(self.vy,1,1)
        grid2.addWidget(QLabel("vz"),2,0)
        grid2.addWidget(self.vz,2,1)

        vel.setLayout(grid2)
        layout.addWidget(vel)

        # вывод
        result = QGroupBox("Параметры орбиты")
        grid3 = QGridLayout()

        self.a_out = QLabel("-")
        self.e_out = QLabel("-")
        self.type_out = QLabel("-")
        self.i_out = QLabel("-")
        self.node_out = QLabel("-")
        self.arg_out = QLabel("-")
        self.nu_out = QLabel("-")

        labels = [
            ("Большая полуось (а)",self.a_out),
            ("Эксцентриситет",self.e_out),
            ("Тип орбиты",self.type_out),
            ("Наклонение (°)",self.i_out),
            ("Долгота узла (°)",self.node_out),
            ("Аргумент перицентра (°)",self.arg_out),
            ("Истинная аномалия (°)",self.nu_out)
        ]

        for i,(text,val) in enumerate(labels):
            grid3.addWidget(QLabel(text),i,0)
            grid3.addWidget(val,i,1)

        result.setLayout(grid3)
        layout.addWidget(result)

        widget.setLayout(layout)
        return widget

    # ---------- РЕЖИМ 2 ----------
    def mode2_ui(self):

        widget = QWidget()
        layout = QVBoxLayout()

        inputs = QGroupBox("Орбитальные элементы")
        grid = QGridLayout()

        self.a = QLineEdit()
        self.e = QLineEdit()
        self.inc = QLineEdit()
        self.node = QLineEdit()
        self.arg = QLineEdit()
        self.nu = QLineEdit()

        for field in [self.a, self.e, self.inc, self.node, self.arg, self.nu]:
            self.set_validator(field)

        fields = [
            ("a (км)",self.a),
            ("e",self.e),
            ("i (°)",self.inc),
            ("Ω (°)",self.node),
            ("ω (°)",self.arg),
            ("ν (°)",self.nu)
        ]

        for i,(text,field) in enumerate(fields):
            grid.addWidget(QLabel(text),i,0)
            grid.addWidget(field,i,1)

        inputs.setLayout(grid)
        layout.addWidget(inputs)

        outputs = QGroupBox("Вектор состояния")
        grid2 = QGridLayout()

        self.x_out = QLabel("-")
        self.y_out = QLabel("-")
        self.z_out = QLabel("-")
        self.vx_out = QLabel("-")
        self.vy_out = QLabel("-")
        self.vz_out = QLabel("-")

        fields2 = [
            ("x (км)",self.x_out),
            ("y (км)",self.y_out),
            ("z (км)",self.z_out),
            ("vx (км/с)",self.vx_out),
            ("vy (км/с)",self.vy_out),
            ("vz (км/с)",self.vz_out)
        ]

        for i,(text,val) in enumerate(fields2):
            grid2.addWidget(QLabel(text),i,0)
            grid2.addWidget(val,i,1)

        outputs.setLayout(grid2)
        layout.addWidget(outputs)

        widget.setLayout(layout)
        return widget

    # ---------- ПЕРЕКЛЮЧЕНИЕ ----------
    def switch_mode(self):
        self.stack.setCurrentIndex(0 if self.mode1.isChecked() else 1)

    # ---------- СБОР ДАННЫХ ----------
    def collect_data(self):

        if self.mode1.isChecked():
            self.input_data = {
                "x": float(self.x.text() or 0),
                "y": float(self.y.text() or 0),
                "z": float(self.z.text() or 0),
                "vx": float(self.vx.text() or 0),
                "vy": float(self.vy.text() or 0),
                "vz": float(self.vz.text() or 0),
            }

        else:
            self.input_data = {
                "a": float(self.a.text() or 0),
                "e": float(self.e.text() or 0),
                "i": float(self.inc.text() or 0),
                "node": float(self.node.text() or 0),
                "arg": float(self.arg.text() or 0),
                "nu": float(self.nu.text() or 0),
            }

        print("Ввод:", self.input_data)

        # пример сохранения результата
        self.output_data = {"status": "готово"}

        print("Вывод:", self.output_data)

threading.Thread(target=connection_loop, daemon=True).start() # by Besolea

app = QApplication(sys.argv)

window = OrbitApp()
window.show()

sys.exit(app.exec())