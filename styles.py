styles = """

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
"""

