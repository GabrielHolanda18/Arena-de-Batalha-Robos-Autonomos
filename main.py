import multiprocessing as mp
import random
import time
import os
import sys

# Importações dos módulos do jogo
from configuracao_jogo import (
    DadosCompartilhados, LARGURA_GRID, ALTURA_GRID, MAX_ROBOS, MAX_BATERIAS,
    CELULA_BARREIRA, CELULA_BATERIA, CELULA_VAZIA
)
from processo_robo import processo_robo
from processo_visualizador import processo_visualizador
import sincronizacao as sync_funcs

# Importa a função para a demonstração de deadlock
from demonstracao_deadlock import executar_demonstracao_deadlock, executar_demonstracao_prevencao

def limpar_terminal():
    """Limpa a tela do terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def configurar_jogo_inicial(dados_compartilhados):
    """
    Função que inicializa o tabuleiro, posiciona barreiras, baterias e robôs.
    Garante que apenas um processo faça isso.
    """
    shm = dados_compartilhados

    shm.mutex_inicializacao.acquire() # Garante exclusividade na inicialização

    if not shm.jogo_inicializado.value:
        print("--- INICIALIZANDO O JOGO: Arena dos Processos ---")

        # Gerar barreiras fixas (aleatoriamente)
        num_barreiras = (LARGURA_GRID * ALTURA_GRID) // 10 # Cerca de 10% do grid
        for _ in range(num_barreiras):
            while True:
                x = random.randint(0, LARGURA_GRID - 1)
                y = random.randint(0, ALTURA_GRID - 1)
                if shm.obter_char_grid(x, y) == chr(CELULA_VAZIA):
                    shm.definir_char_grid(x, y, chr(CELULA_BARREIRA))
                    break

        # Posicionar baterias
        for i in range(MAX_BATERIAS):
            while True:
                x = random.randint(0, LARGURA_GRID - 1)
                y = random.randint(0, ALTURA_GRID - 1)
                if shm.obter_char_grid(x, y) == chr(CELULA_VAZIA):
                    shm.definir_char_grid(x, y, chr(CELULA_BATERIA))
                    shm.posicoes_baterias[i] = (x, y) # Guarda a posição da bateria para mapear com o mutex
                    print(f"Bateria {i} posicionada em ({x},{y}).")
                    break

        # Preencher atributos dos robôs e posicioná-los
        for i in range(MAX_ROBOS):
            shm.ids_robos[i] = i
            shm.forcas_robos[i] = random.randint(1, 10) # Força (F): 1-10
            shm.energias_robos[i] = random.randint(10, 100) # Energia (E): 10-100
            shm.velocidades_robos[i] = random.randint(1, 5) # Velocidade (V): 1-5
            shm.status_robos[i] = 0 # Vivo

            while True: # Posiciona o robô em uma célula vazia
                x = random.randint(0, LARGURA_GRID - 1)
                y = random.randint(0, ALTURA_GRID - 1)
                if shm.obter_char_grid(x, y) == chr(CELULA_VAZIA):
                    shm.pos_x_robos[i] = x
                    shm.pos_y_robos[i] = y
                    shm.definir_char_grid(x, y, str(i)) # Coloca o ID do robô no grid
                    print(f"Robô {i} (Força={shm.forcas_robos[i]}, Energia={shm.energias_robos[i]}, Velocidade={shm.velocidades_robos[i]}) criado em ({x},{y}).")
                    break
        
        # Um dos robôs é o "robô do jogador", criado com atributos aleatórios.
        # O Robô 0 pode ser considerado o robô do jogador, e já está sendo criado com atributos aleatórios.

        shm.jogo_inicializado.value = True
        print("--- INICIALIZAÇÃO DO JOGO CONCLUÍDA ---")
    else:
        print("Jogo já foi inicializado por outro processo.")

    shm.mutex_inicializacao.release()

def rodar_jogo_principal():
    """Função que orquestra o jogo principal."""
    limpar_terminal()
    print("Iniciando o Jogo Principal: Arena dos Processos - Batalha dos Robôs Autônomos.")

    # O Manager é fundamental para compartilhar objetos entre processos
    gerenciador = mp.Manager()
    
    # Cria uma instância de DadosCompartilhados usando o Manager
    dados_compartilhados_do_jogo = DadosCompartilhados(gerenciador)

    # Injeta a referência global em outros módulos
    # Isso é necessário porque os módulos são importados e não sabem da instância de 'dados_compartilhados_do_jogo'
    # que é criada aqui no main.
    processo_robo.dados_compartilhados_do_jogo = dados_compartilhados_do_jogo
    processo_visualizador.dados_compartilhados_do_jogo = dados_compartilhados_do_jogo
    sync_funcs.dados_compartilhados_do_jogo = dados_compartilhados_do_jogo


    # Configura o jogo (grid, barreiras, baterias, robôs)
    configurar_jogo_inicial(dados_compartilhados_do_jogo)

    # Lista para guardar os processos de robôs
    lista_processos_robos = []
    for i in range(MAX_ROBOS):
        # Cada robô é um processo separado, passando o ID e os dados compartilhados
        p_robo = mp.Process(target=processo_robo, args=(i, dados_compartilhados_do_jogo))
        lista_processos_robos.append(p_robo)
        p_robo.start()

    # Cria e inicia o processo do visualizador
    p_visualizador = mp.Process(target=processo_visualizador, args=(dados_compartilhados_do_jogo,))
    p_visualizador.start()

    # Loop principal para esperar o jogo terminar
    while not dados_compartilhados_do_jogo.jogo_acabou.value:
        time.sleep(0.5) # Espera um pouco para não consumir CPU em excesso

    print("\n--- FIM DE JOGO DETECTADO NO MAIN ---")

    # Espera todos os processos de robôs terminarem
    for p_robo in lista_processos_robos:
        p_robo.join()

    # Espera o processo do visualizador terminar
    p_visualizador.join()

    # Encerra o Manager para liberar os recursos compartilhados
    gerenciador.shutdown()
    print("--- Todos os processos encerrados e recursos liberados. ---")


if __name__ == "__main__":
    limpar_terminal()
    print("=" * 80)
    print("ARENA DOS PROCESSOS - BATALHA DOS ROBÔS AUTÔNOMOS")
    print("=" * 80)
    print("\nEscolha uma opção:")
    print("1. Rodar o Jogo Principal")
    print("2. Rodar a Demonstração de Deadlock e Prevenção")
    print("3. Sair")

    while True:
        escolha = input("Digite sua opção (1, 2 ou 3): ").strip()
        if escolha == '1':
            rodar_jogo_principal()
            break
        elif escolha == '2':
            executar_demonstracao_deadlock()
            print("\nPreparando para a próxima demonstração...")
            time.sleep(3)
            limpar_terminal() # Limpa o terminal novamente para a nova etapa

            # 2. Demonstração da Prevenção
            executar_demonstracao_prevencao()

            print("\n\nDemonstração completa. Verifique os logs para mais detalhes.")

            break
        elif escolha == '3':
            print("Saindo do programa.")
            sys.exit(0)
        else:
            print("Opção inválida. Por favor, digite 1, 2 ou 3.")
        time.sleep(1)
        limpar_terminal()
        print("=" * 80)
        print("ARENA DOS PROCESSOS - BATALHA DOS ROBÔS AUTÔNOMOS")
        print("=" * 80)
        print("\nEscolha uma opção:")
        print("1. Rodar o Jogo Principal")
        print("2. Rodar a Demonstração de Deadlock e Prevenção")
        print("3. Sair")