import tkinter as tk
from multiprocessing.connection import Listener
import threading
import time


ADDRESS = ('localhost', 6000)
AUTHKEY = b'secret'


class SliderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("7 Sliders Sender")

        self.sliders = []

        # Создаём 7 ползунков
        names = ['empty', 'speed', 'octaves', 'warp', 'hue', 'saturation', 'contrast']
        for i in range(7):
            scale = tk.Scale(
                root,
                from_=0,
                to=1,
                resolution=0.01,
                orient="horizontal",
                length=300,
                label=names[i]
            )
            scale.pack(pady=5)
            self.sliders.append(scale)

        self.conn = None

        # Запускаем сервер в отдельном потоке
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        listener = Listener(ADDRESS, authkey=AUTHKEY)
        print("Ожидание подключения клиента...")
        self.conn = listener.accept()
        print("Клиент подключен!")

        # Запускаем отправку данных
        threading.Thread(target=self.send_loop, daemon=True).start()

    def send_loop(self):
        while True:
            if self.conn:
                values = [slider.get() for slider in self.sliders]
                try:
                    self.conn.send(values)
                except:
                    break
            time.sleep(0.05)  # 20 раз в секунду


if __name__ == "__main__":
    root = tk.Tk()
    app = SliderApp(root)
    root.mainloop()