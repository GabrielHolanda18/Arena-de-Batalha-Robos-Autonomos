import multiprocessing
import random
import time

class robo(multiprocessing.Process):
    def __init__(self, nome, tabuleiro, locks, posicao, energia):
        super().__init__()
        self.nome = nome
        self.tabuleiro = tabuleiro
        self.locks = locks  # {'tabuleiro': Lock, 'bateria': Lock}
        self.x, self.y = posicao
        self.energia = energia

    def run(self):
        while True:
            self.move()
            time.sleep(0.5)

    def move(self):
        # lógica básica de movimentação
        dx, dy = random.choice([(0,1), (1,0), (0,-1), (-1,0)])
        new_x = (self.x + dx) % self.tabuleiro.width
        new_y = (self.y + dy) % self.tabuleiro.height

        with self.locks['tabuleiro']:
            if self.tabuleiro.get_cell(new_x, new_y) == ' ':
                self.tabuleiro.set_cell(self.x, self.y, ' ')
                self.x, self.y = new_x, new_y
                self.tabuleiro.set_cell(self.x, self.y, self.nome[0])
