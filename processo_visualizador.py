import multiprocessing as mp
import time
import os
from configuracao_jogo import (LARGURA_GRID, ALTURA_GRID, CELULA_VAZIA, CELULA_BARREIRA, CELULA_BATERIA, MAX_ROBOS, STATUS_VIVO)

# Variável global para os dados compartilhados, será injetada pelo main_jogo.py
dados_compartilhados_do_jogo = None

def limpar_tela_terminal():
    """Limpa a tela do terminal usando comandos ANSI."""
    # Equivalente ao cls no Windows ou clear no Unix
    os.system('cls' if os.name == 'nt' else 'clear')

def processo_visualizador(dados_compartilhados):
    """
    Função principal que será executada pelo processo visualizador.
    Apenas renderiza o grid e o status dos robôs.
    """
    global dados_compartilhados_do_jogo
    dados_compartilhados_do_jogo = dados_compartilhados # Injeta a referência global
    shm = dados_compartilhados_do_jogo # Alias para facilitar

    print("Processo do Visualizador iniciado.")

    while not shm.jogo_acabou.value:
        limpar_tela_terminal()

        # 1. Copiar o GRID para exibição (com lock para consistência)
        # O visualizador deve ser passivo, então pega o lock do grid apenas para ler.
        shm.mutex_grid.acquire()
        grid_para_exibir = [[shm.obter_char_grid(x, y) for x in range(LARGURA_GRID)] for y in range(ALTURA_GRID)]
        shm.mutex_grid.release()

        # 2. Exibir o Tabuleiro em ASCII (com cores ANSI básicas)
        print("-" * (LARGURA_GRID + 2))
        for y in range(ALTURA_GRID):
            linha = ["|"]
            for x in range(LARGURA_GRID):
                char = grid_para_exibir[y][x]
                # Aplica cores ANSI para diferentes elementos
                if '0' <= char <= str(MAX_ROBOS - 1): # Robôs
                    # Cores diferentes para cada robô (ex: 91m=vermelho, 92m=verde, etc)
                    cor = 91 + int(char) % 7 # Ciclagem de cores
                    linha.append(f"\033[{cor}m{char}\033[0m")
                elif char == chr(CELULA_BARREIRA): # Barreiras
                    linha.append(f"\033[90m{char}\033[0m") # Cinza
                elif char == chr(CELULA_BATERIA): # Baterias
                    linha.append(f"\033[93m{char}\033[0m") # Amarelo
                else:
                    linha.append(char) # Célula vazia ou outro
            linha.append("|")
            print("".join(linha))
        print("-" * (LARGURA_GRID + 2))

        # 3. Exibir Status dos Robôs
        shm.mutex_robos_atributos.acquire() # Adquire o lock para ler atributos dos robôs
        print("\n--- Status dos Robôs ---")
        for i in range(MAX_ROBOS):
            status_str = "Vivo" if shm.status_robos[i] == STATUS_VIVO else "Morto"
            print(f"Robô {i}: Força={shm.forcas_robos[i]}, Energia={shm.energias_robos[i]}, Velocidade={shm.velocidades_robos[i]}, Pos=({shm.pos_x_robos[i]},{shm.pos_y_robos[i]}), Status={status_str}")
        shm.mutex_robos_atributos.release() # Libera o lock

        time.sleep(0.1) # Atualiza a cada 100ms (50-200 ms conforme PDF)

    print("Processo do Visualizador encerrado.")
    if shm.id_vencedor.value != -1:
        print(f"O VENCEDOR É O ROBÔ {shm.id_vencedor.value}!")
    else:
        print("Nenhum robô sobreviveu. Fim de jogo sem vencedor claro.")