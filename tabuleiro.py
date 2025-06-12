from multiprocessing import Array, Lock

class Board:
    def __init__(self, largura=40, altura=20):
        self.largura = largura
        self.altura = altura
        self.grid = Array('c', b' ' * (largura * altura), lock=False)
        self.lock = Lock()

    def set_cell(self, x, y, value):
        with self.lock:
            idx = y * self.largura + x
            self.grid[idx] = value.encode()

    def get_cell(self, x, y):
        idx = y * self.largura + x
        return self.grid[idx].decode()
