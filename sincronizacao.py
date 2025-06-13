import time
import random
from configuracao_jogo import (
    LARGURA_GRID, ALTURA_GRID, MAX_ROBOS, MAX_BATERIAS,
    INDICE_LOCK_BATERIA, INDICE_LOCK_GRID, INDICE_LOCK_ROBOS,
    STATUS_VIVO 
)

# Variável global para os dados compartilhados, será injetada pelo main_jogo.py
dados_compartilhados_do_jogo = None

def atualizar_status_lock(id_robo, tipo_lock, indice_lock=None, esta_pedindo=False, esta_segurando=False):

    # Atualiza o estado de locks na memória compartilhada para detecção de deadlock.
    
    global dados_compartilhados_do_jogo
    if dados_compartilhados_do_jogo is None:
        print("Erro: dados do jogo não inicializado em sincronizacao.")
        return

    # Essas chamadas estao no configuracao_jogo para verificar 
    with dados_compartilhados_do_jogo.mutex_deadlock_detector:
        if tipo_lock == INDICE_LOCK_BATERIA:
            if esta_pedindo:
                dados_compartilhados_do_jogo.lock_pedido_bateria[id_robo * MAX_BATERIAS + indice_lock] = True
                dados_compartilhados_do_jogo.tentando_pegar_bateria_id[id_robo] = indice_lock
            else:
                dados_compartilhados_do_jogo.lock_pedido_bateria[id_robo * MAX_BATERIAS + indice_lock] = False
                dados_compartilhados_do_jogo.tentando_pegar_bateria_id[id_robo] = -1

            dados_compartilhados_do_jogo.lock_segurado_bateria[id_robo * MAX_BATERIAS + indice_lock] = esta_segurando
        elif tipo_lock == INDICE_LOCK_GRID:
            dados_compartilhados_do_jogo.lock_pedido_grid[id_robo] = esta_pedindo
            dados_compartilhados_do_jogo.lock_segurado_grid[id_robo] = esta_segurando
        elif tipo_lock == INDICE_LOCK_ROBOS:
            dados_compartilhados_do_jogo.lock_pedido_robos[id_robo] = esta_pedindo
            dados_compartilhados_do_jogo.lock_segurado_robos[id_robo] = esta_segurando


def detectar_deadlock_especifico(id_robo_tentando_lock):
    # Feito para detectar deadlocks caso ocorra durante o jogo 
    # a classe deadlock_robo.py força um deadlock 
    global dados_compartilhados_do_jogo
    if dados_compartilhados_do_jogo is None: return False

    with dados_compartilhados_do_jogo.mutex_deadlock_detector:
        # Verifica se o robô atual (A) está pedindo o mutex_grid
        if dados_compartilhados_do_jogo.lock_pedido_grid[id_robo_tentando_lock]:
            # E se o robô atual (A) está segurando alguma bateria
            for idx_bateria_a in range(MAX_BATERIAS):
                if dados_compartilhados_do_jogo.lock_segurado_bateria[id_robo_tentando_lock * MAX_BATERIAS + idx_bateria_a]:
                    # Agora, procura por outro robô (B) que:
                    # 1. Está segurando o mutex_grid
                    # 2. Está pedindo a mesma bateria (idx_bateria_a)
                    for id_outro_robo in range(MAX_ROBOS):
                        if id_outro_robo == id_robo_tentando_lock:
                            continue # Não é o mesmo robô

                        if dados_compartilhados_do_jogo.lock_segurado_grid[id_outro_robo]: # Robô B tem grid
                            # Verifica se B está tentando pegar a bateria que A já tem
                            if dados_compartilhados_do_jogo.tentando_pegar_bateria_id[id_outro_robo] == idx_bateria_a:
                                print(f"DEADLOCK Aconteceu! Robô {id_robo_tentando_lock} (A) tem bateria {idx_bateria_a} e quer GRID. Robô {id_outro_robo} (B) tem GRID e quer bateria {idx_bateria_a}.")
                                return True # Deadlock encontrado!
    return False

def recuperar_deadlock_simples(id_robo_envolvido):
    """
    Recuperação simples: o robô envolvido no deadlock libera todos os seus locks
    e espera um tempo aleatório para tentar novamente.
    """
    global dados_compartilhados_do_jogo
    if dados_compartilhados_do_jogo is None: return False

    print(f"Robô {id_robo_envolvido}: Iniciando recuperação de deadlock. Liberando locks...")

    # Tenta liberar o mutex_grid se estiver segurando
    if dados_compartilhados_do_jogo.lock_segurado_grid[id_robo_envolvido]:
        try:
            dados_compartilhados_do_jogo.mutex_grid.release()
            atualizar_status_lock(id_robo_envolvido, INDICE_LOCK_GRID, esta_segurando=False)
            print(f"  Robô {id_robo_envolvido} liberou mutex_grid.")
        except Exception as e:
            print(f"  Erro ao liberar mutex_grid para robô {id_robo_envolvido}: {e}")

    # Tenta liberar mutexes de bateria se estiver segurando
    for idx_bateria in range(MAX_BATERIAS):
        if dados_compartilhados_do_jogo.lock_segurado_bateria[id_robo_envolvido * MAX_BATERIAS + idx_bateria]:
            try:
                dados_compartilhados_do_jogo.mutexes_bateria[idx_bateria].release()
                atualizar_status_lock(id_robo_envolvido, INDICE_LOCK_BATERIA, idx_bateria, esta_segurando=False)
                print(f"  Robô {id_robo_envolvido} liberou mutex_bateria[{idx_bateria}].")
            except Exception as e:
                print(f"  Erro ao liberar mutex_bateria[{idx_bateria}] para robô {id_robo_envolvido}: {e}")

    # Tenta liberar o mutex_robos_atributos se estiver segurando
    if dados_compartilhados_do_jogo.lock_segurado_robos[id_robo_envolvido]:
        try:
            dados_compartilhados_do_jogo.mutex_robos_atributos.release()
            atualizar_status_lock(id_robo_envolvido, INDICE_LOCK_ROBOS, esta_segurando=False)
            print(f"  Robô {id_robo_envolvido} liberou mutex_robos_atributos.")
        except Exception as e:
            print(f"  Erro ao liberar mutex_robos_atributos para robô {id_robo_envolvido}: {e}")

    # Espera um tempo aleatório para evitar um novo deadlock imediato
    tempo_espera = random.uniform(0.1, 0.5)
    print(f"Robô {id_robo_envolvido}: Esperando {tempo_espera:.2f} segundos antes de re-tentar.")
    time.sleep(tempo_espera)
    return True # Indica que a recuperação foi tentada com sucesso, o robô deve re-tentar sua ação