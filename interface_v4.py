from data_simulation import create_animation_widget, connection_loop
#import threading

from styles import styles

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QRadioButton, QGroupBox, QStackedWidget, QDialog, QScrollArea, QFileDialog
    
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QCursor # для ввода только чисел

import orb_mech_update

dti = {
        'a':'-',
        'e_val':'-',
        'i_deg':'-',
        "O_deg":'-',
        "w_deg":'-',
        'nu_deg':'-'

    }

dti2 = {
        'x':'-',
        'y':'-',
        'z':'-',
        "vx":'-',
        "vy":'-',
        'vz':'-'

    }

orbd = {
    'hp':'-',
    'rp':'-',
    'ha':'-',
    "ra":'-' 
}



class Overlay(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)

        # растягиваемся на всё окно родителя
        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WA_StyledBackground, True)

        # затемнённый фон
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 120);
        """)

        # контейнер для popup
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.popup = QLabel(text)
        self.popup.setFixedSize(600, 150)
        self.popup.setAlignment(Qt.AlignCenter)

        self.popup.setStyleSheet("""
            background-color: white;
            border-radius: 12px;
            font-size: 16px;
            padding: 20px;
        """)

        layout.addWidget(self.popup)

    # клик вне popup → закрыть
    def mousePressEvent(self, event):
        if not self.popup.geometry().contains(event.pos()):
            self.close()    

class OrbitApp(QWidget):

    def __init__(self):
        super().__init__()

        # ---------- ХРАНЕНИЕ ДАННЫХ ----------
        self.input_data = {}   # ввод пользователя
        self.output_data = {}  # результаты

        self.setWindowTitle("Orbital Parameters Calculator")
        self.resize(1000, 560)

        # ---------- СТИЛИ (без изменений) ----------
        self.setStyleSheet(styles)

        main_layout = QHBoxLayout()

        # ---------- ЛЕВАЯ ЧАСТЬ ----------
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_widget)
        main_layout.addWidget(scroll, 2)

        scroll.setStyleSheet("""
    QScrollArea {
        border: none;
    }
""")

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

        image_box = QGroupBox()
        image_layout = QVBoxLayout()

        # self.image = QLabel("Здесь будет изображение орбиты")     by_Besolea
        # self.image.setAlignment(Qt.AlignCenter)

        #self.canvas = create_animation_widget()
        #image_layout.addWidget(self.canvas)

        tabs_group = QGroupBox("Отображение")
        tabs_layout = QHBoxLayout()

        self.view1 = QRadioButton("Визуализация")
        self.view2 = QRadioButton("Орбита")

        self.view1.setChecked(True)

        tabs_layout.addWidget(self.view1)
        tabs_layout.addWidget(self.view2)
        tabs_group.setLayout(tabs_layout)

        right_layout.addWidget(tabs_group)


        self.right_stack = QStackedWidget()

        # первое окно
        self.canvas = create_animation_widget()
        self.right_stack.addWidget(self.canvas)

        # второе окно
        self.second_page = QLabel("Второе окно")
        self.second_page.setAlignment(Qt.AlignCenter)
        self.right_stack.addWidget(self.second_page)

        image_layout.addWidget(self.right_stack)

        # image_layout.addWidget(self.image)
        image_box.setLayout(image_layout)

        right_layout.addWidget(image_box)


        # кнопка загрузки файла
        self.load_button = QPushButton("Загрузить файл")

        # контейнер для выравнивания вправо вниз
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # сдвигает кнопку вправо
        btn_layout.addWidget(self.load_button)

        right_layout.addLayout(btn_layout)


        self.view1.toggled.connect(self.switch_right_view)

        # ---------- СБОРКА ----------
        #main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)

        # ---------- СОБЫТИЯ ----------
        self.mode1.toggled.connect(self.switch_mode)
        self.calc_button.clicked.connect(self.collect_data)
        self.load_button.clicked.connect(self.open_file)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите текстовый файл",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                # пробуем разные кодировки
                for enc in ["utf-8", "utf-16", "cp1251"]:
                    try:
                        with open(file_path, "r", encoding=enc) as f:
                            content = f.read()
                        print(f"Файл прочитан в кодировке: {enc}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise Exception("Не удалось определить кодировку")

                print(content)
                self.loaded_text = content
                get_d(list(map(int, content.split())))
                
                

            except Exception as e:
                #self.overlay = Overlay(f"Ошибка чтения файла: {e}", self)
                #self.overlay.show()  
                print(f"Ошибка чтения файла: {str(e)}", self)  

    def switch_right_view(self):
        self.right_stack.setCurrentIndex(0 if self.view1.isChecked() else 1)    

    # ---------- ВАЛИДАТОР ----------
    def set_validator(self, field):
        validator = QDoubleValidator()
        field.setValidator(validator)

    # ---------- РЕЖИМ 1 ----------
    def mode1_ui(self):

        widget = QWidget()
        layout = QVBoxLayout()

        mu_box = QGroupBox("Гравитационный параметр (км^3/с^2)")
        mu_layout = QHBoxLayout()

        self.mu1 = QLineEdit()
        self.set_validator(self.mu1)

        mu_layout.addWidget(QLabel("μ"))
        mu_layout.addWidget(self.mu1)

        mu_box.setLayout(mu_layout)
        layout.addWidget(mu_box)

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


        self.a_out = QLabel(dti["a"])
        self.e_out = QLabel(dti["e_val"])
        self.type_out = QLabel("-")
        self.i_out = QLabel(dti["i_deg"])
        self.node_out = QLabel(dti["O_deg"])
        self.arg_out = QLabel(dti["w_deg"])
        self.nu_out = QLabel(dti["nu_deg"])

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

        aux_box = QGroupBox("Орбита")
        aux_layout = QGridLayout()

        
        self.hp1 = QLabel(orbd["hp"])
        self.rp1 = QLabel(orbd["rp"])
        self.ha1 = QLabel(orbd["ha"])
        self.ra1 = QLabel(orbd["ra"])

        aux_fields = [
            
            ("Высота перицентра", self.hp1),
            ("Перицентрное расстояние", self.rp1),
            ("Высота апоцентра", self.ha1),
            ("Апоцентрное расстояние", self.ra1),
        ]

        for i, (text, val) in enumerate(aux_fields):
            aux_layout.addWidget(QLabel(text), i, 0)
            aux_layout.addWidget(val, i, 1)

        aux_box.setLayout(aux_layout)
        layout.addWidget(aux_box)

        widget.setLayout(layout)
        return widget

    # ---------- РЕЖИМ 2 ----------
    def mode2_ui(self):

        widget = QWidget()
        layout = QVBoxLayout()

        mu_box = QGroupBox("Гравитационный параметр (км^3/с^2)")
        mu_layout = QHBoxLayout()

        self.mu2 = QLineEdit()
        self.set_validator(self.mu2)

        mu_layout.addWidget(QLabel("μ"))
        mu_layout.addWidget(self.mu2)

        mu_box.setLayout(mu_layout)
        layout.addWidget(mu_box)

        inputs = QGroupBox("Орбитальные элементы")
        grid = QGridLayout()

        self.a = QLineEdit()
        self.e_val = QLineEdit()
        self.i_deg = QLineEdit()
        self.O_deg = QLineEdit()
        self.w_deg = QLineEdit()
        self.nu_deg = QLineEdit()

        for field in [self.a, self.e_val, self.i_deg, self.O_deg, self.w_deg, self.nu_deg]:
            self.set_validator(field)

        fields = [
            ("a (км)",self.a),
            ("e_val",self.e_val),
            ("i_deg (°)",self.i_deg),
            ("Ω (°)",self.O_deg),
            ("ω (°)",self.w_deg),
            ("ν (°)",self.nu_deg)
        ]

        for i,(text,field) in enumerate(fields):
            grid.addWidget(QLabel(text),i,0)
            grid.addWidget(field,i,1)

        inputs.setLayout(grid)
        layout.addWidget(inputs)

        outputs = QGroupBox("Вектор состояния")
        grid2 = QGridLayout()

        self.x_out = QLabel(dti2["x"])
        self.y_out = QLabel(dti2["y"])
        self.z_out = QLabel(dti2["z"])
        self.vx_out = QLabel(dti2["vx"])
        self.vy_out = QLabel(dti2["vy"])
        self.vz_out = QLabel(dti2["vz"])

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

        aux_box = QGroupBox("Орбита")
        aux_layout = QGridLayout()

        
        self.hp2 = QLabel(orbd["hp"])
        self.rp2 = QLabel(orbd["rp"])
        self.ha2 = QLabel(orbd["ha"])
        self.ra2 = QLabel(orbd["ra"])

        aux_fields = [
            
            ("Высота перицентра", self.hp2),
            ("Перицентрное расстояние", self.rp2),
            ("Высота апоцентра", self.ha2),
            ("Апоцентрное расстояние", self.ra2),
        ]

        for i, (text, val) in enumerate(aux_fields):
            aux_layout.addWidget(QLabel(text), i, 0)
            aux_layout.addWidget(val, i, 1)

        aux_box.setLayout(aux_layout)
        layout.addWidget(aux_box)


        widget.setLayout(layout)
        return widget

    # ---------- ПЕРЕКЛЮЧЕНИЕ ----------
    def switch_mode(self):
        self.stack.setCurrentIndex(0 if self.mode1.isChecked() else 1)

    # ---------- СБОР ДАННЫХ ----------

    def update_output_1(self, dti):
        self.a_out.setText(str(dti["a"]))
        self.e_out.setText(str(dti["e_val"]))
        self.i_out.setText(str(dti["i_deg"]))
        self.node_out.setText(str(dti["O_deg"]))
        self.arg_out.setText(str(dti["w_deg"]))
        self.nu_out.setText(str(dti["nu_deg"]))

    def update_output_2(self, dti2):
        self.x_out.setText(str(dti2["x"]))
        self.y_out.setText(str(dti2["y"]))
        self.z_out.setText(str(dti2["z"]))
        self.vx_out.setText(str(dti2["vx"]))
        self.vy_out.setText(str(dti2["vy"]))
        self.vz_out.setText(str(dti2["vz"]))

    def update_aux1(self, data):

        self.hp1.setText(str(data["h_p"]))
        self.rp1.setText(str(data.get("r_p", "-")))
        self.ha1.setText(str(data.get("h_a", "-")))
        self.ra1.setText(str(data.get("r_a", "-")))

    def update_aux2(self, data):

        self.hp2.setText(str(data["h_p"]))
        self.rp2.setText(str(data.get("r_p", "-")))
        self.ha2.setText(str(data.get("h_a", "-")))
        self.ra2.setText(str(data.get("r_a", "-")))











    def collect_data(self):
        

        if self.mode1.isChecked():
            self.input_data = {
                "mu": float(self.mu1.text().replace(',', '.') or 398600.4418),
                "x": float(self.x.text().replace(',', '.') or 0),
                "y": float(self.y.text().replace(',', '.') or 0),
                "z": float(self.z.text().replace(',', '.') or 0),
                "vx": float(self.vx.text().replace(',', '.') or 0),
                "vy": float(self.vy.text().replace(',', '.') or 0),
                "vz": float(self.vz.text().replace(',', '.') or 0),
            }
            datapack = orb_mech_update.state_vector_to_elements(**self.input_data)
            #print(datapack)
            if datapack[1] == -1:
                self.overlay = Overlay(datapack[0], self)
                self.overlay.show()
                print(datapack[0])

            else:

                dti = datapack[0]
                

                if isinstance(dti, str):
                    self.overlay = Overlay(dti, self)
                    self.overlay.show()
                    print(dti)
                else:
                    self.update_output_1(dti)
                    print(dti)

                if isinstance(datapack[1], str):
                    self.overlay = Overlay(datapack[1], self)
                    self.overlay.show()
                    print(datapack[1])
                else:
                    self.update_aux1(datapack[1])

                    print(datapack[1])
            
            

        else:
            self.input_data = {
                "mu": float(self.mu2.text().replace(',', '.') or 398600.4418),
                "a": float(self.a.text().replace(',', '.') or 0),
                "e_val": float(self.e_val.text().replace(',', '.') or 0),
                "i_deg": float(self.i_deg.text().replace(',', '.') or 0),
                "O_deg": float(self.O_deg.text().replace(',', '.') or 0),
                "w_deg": float(self.w_deg.text().replace(',', '.') or 0),
                "nu_deg": float(self.nu_deg.text().replace(',', '.') or 0),
            }
            datapack = orb_mech_update.elements_to_state_vector(**self.input_data)
            dti2 = datapack[0]
            if isinstance(datapack[1], str):
                self.overlay = Overlay(datapack[1], self)
                self.overlay.show()
            else:
                self.update_aux2(datapack[1])


           # print(dti2)
            print(datapack[1])
            self.update_output_2(dti2)
            
       # print("Ввод:", self.input_data)

        # пример сохранения результата
        #self.output_data = {"status": "готово"}

       # print("Вывод:", self.output_data)


#threading.Thread(target=connection_loop, daemon=True).start() # by Besolea

app = QApplication(sys.argv)

window = OrbitApp()
window.show()

sys.exit(app.exec())