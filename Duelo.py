import threading
import time
import random
from configuracao_jogo import (
    LARGURA_GRID, ALTURA_GRID, CELULA_VAZIA, CELULA_BATERIA,
    STATUS_VIVO, STATUS_MORTO,
    INDICE_LOCK_BATERIA, INDICE_LOCK_GRID, INDICE_LOCK_ROBOS
)

def duel(robo1, robo2, duel_lock):
    with duel_lock:
        winner = robo1 if robo1.energy >= robo2.energy else robo2
        loser = robo2 if winner == robo1 else robo1
        print(f"{winner.name} venceu o duelo contra {loser.name}!")
        return winner

def calcular_poder(forca, energia):
    """Calcula o poder de ataque do robô conforme o PDF."""
    return 2 * forca + energia # Poder=2F+E 

def resolver_duelo(id_robo_1, id_robo_2, shm):

    print(f"Duelo entre Robô {id_robo_1} e Robô {id_robo_2}!")

    # Acessa os atributos dos robôs diretamente via shm
    poder_robo_1 = calcular_poder(shm.forcas_robos[id_robo_1], shm.energias_robos[id_robo_1]) [cite: 9]
    poder_robo_2 = calcular_poder(shm.forcas_robos[id_robo_2], shm.energias_robos[id_robo_2]) [cite: 9]

    pos_x_1, pos_y_1 = shm.pos_x_robos[id_robo_1], shm.pos_y_robos[id_robo_1]
    pos_x_2, pos_y_2 = shm.pos_x_robos[id_robo_2], shm.pos_y_robos[id_robo_2]

    if poder_robo_1 > poder_robo_2:
        print(f"Robô {id_robo_1} (Poder: {poder_robo_1}) venceu Robô {id_robo_2} (Poder: {poder_robo_2}).")
        shm.status_robos[id_robo_2] = STATUS_MORTO # Perdedor marca status = morto 
        shm.definir_char_grid(pos_x_2, pos_y_2, chr(CELULA_VAZIA)) # Libera célula 
    elif poder_robo_2 > poder_robo_1:
        print(f"Robô {id_robo_2} (Poder: {poder_robo_2}) venceu Robô {id_robo_1} (Poder: {poder_robo_1}).")
        shm.status_robos[id_robo_1] = STATUS_MORTO # Perdedor marca status = morto 
        shm.definir_char_grid(pos_x_1, pos_y_1, chr(CELULA_VAZIA)) # Libera célula 
    else: # Empate 
        print(f"Robô {id_robo_1} e Robô {id_robo_2} empataram. Ambos destruídos.") [cite: 10]
        shm.status_robos[id_robo_1] = STATUS_MORTO
        shm.status_robos[id_robo_2] = STATUS_MORTO
        shm.definir_char_grid(pos_x_1, pos_y_1, chr(CELULA_VAZIA))
        shm.definir_char_grid(pos_x_2, pos_y_2, chr(CELULA_VAZIA))