import threading
import time
import random
from configuracao_jogo import (
    LARGURA_GRID, ALTURA_GRID, CELULA_VAZIA, CELULA_BATERIA, CELULA_BARREIRA,
    STATUS_VIVO, STATUS_MORTO,
    INDICE_LOCK_BATERIA, INDICE_LOCK_GRID, INDICE_LOCK_ROBOS, MAX_ROBOS
)
from sincronizacao import atualizar_status_lock, detectar_deadlock_especifico, recuperar_deadlock_simples

# Variável global para os dados compartilhados, será injetada pelo main_jogo.py
dados_compartilhados_do_jogo = None

def _calcular_poder(forca, energia):
    """Calcula o poder de ataque do robô conforme o PDF: Poder = 2F + E."""
    return (2 * forca) + energia

'''  
Robô com maior Poder vence; perdedor marca status = morto e libera célula. Empate ⇒ ambos 
destruídos.
A negociação do duelo deve ocorrer dentro de grid_mutex, sem gerente
'''
def _resolver_duelo(id_robo_1, id_robo_2, shm):
    """
    Esta função assume que os locks NECESSÁRIOS (shm.mutex_grid e shm.mutex_robos_atributos)
    JÁ foram ADQUIRIDOS pelo robô que iniciou o duelo.
    """
    print(f"Duelo entre Robô {id_robo_1} e Robô {id_robo_2}!")

    # Acessa os atributos dos robôs diretamente via shm
    poder_robo_1 = _calcular_poder(shm.forcas_robos[id_robo_1], shm.energias_robos[id_robo_1])
    poder_robo_2 = _calcular_poder(shm.forcas_robos[id_robo_2], shm.energias_robos[id_robo_2])

    pos_x_1, pos_y_1 = shm.pos_x_robos[id_robo_1], shm.pos_y_robos[id_robo_1]
    pos_x_2, pos_y_2 = shm.pos_x_robos[id_robo_2], shm.pos_y_robos[id_robo_2]

    print(f"  Robô {id_robo_1} (F={shm.forcas_robos[id_robo_1]}, E={shm.energias_robos[id_robo_1]}) Poder: {poder_robo_1}")
    print(f"  Robô {id_robo_2} (F={shm.forcas_robos[id_robo_2]}, E={shm.energias_robos[id_robo_2]}) Poder: {poder_robo_2}")

    if poder_robo_1 > poder_robo_2:
        print(f"Robô {id_robo_1} venceu Robô {id_robo_2}.")
        shm.status_robos[id_robo_2] = STATUS_MORTO # Perdedor marca status = morto
        shm.definir_char_grid(pos_x_2, pos_y_2, chr(CELULA_VAZIA)) # Libera célula
    elif poder_robo_2 > poder_robo_1:
        print(f"Robô {id_robo_2} venceu Robô {id_robo_1}.")
        shm.status_robos[id_robo_1] = STATUS_MORTO # Perdedor marca status = morto
        shm.definir_char_grid(pos_x_1, pos_y_1, chr(CELULA_VAZIA)) # Libera célula
    else: # Empate - ambos destruídos
        print(f"Robô {id_robo_1} e Robô {id_robo_2} empataram. Ambos destruídos.")
        shm.status_robos[id_robo_1] = STATUS_MORTO
        shm.status_robos[id_robo_2] = STATUS_MORTO
        shm.definir_char_grid(pos_x_1, pos_y_1, chr(CELULA_VAZIA))
        shm.definir_char_grid(pos_x_2, pos_y_2, chr(CELULA_VAZIA))

# sense_act (decide ação)
def funcao_thread_sense_act(id_robo):
    """Lógica principal de percepção e ação do robô."""
    global dados_compartilhados_do_jogo
    shm = dados_compartilhados_do_jogo # Alias para facilitar

    print(f"Robô {id_robo}: Thread sense_act iniciada.")

    while not shm.jogo_acabou.value and shm.status_robos[id_robo] == STATUS_VIVO:
        # Garante que o jogo esteja inicializado antes de o robô começar a agir de fato
        if not shm.jogo_inicializado.value:
            time.sleep(0.1)
            continue

        # 1. Tirar "snapshot" local do grid (sem lock, para decisão rápida)
        # Embora o enunciado diga "sem lock", para um snapshot consistente em Python,
        # é comum pegar um read-lock (se disponível) ou um lock de escrita rápido.
        # Aqui, pegamos o lock de escrita rapidamente para copiar.
        shm.mutex_grid.acquire()
        copia_local_grid = [[shm.obter_char_grid(x, y) for x in range(LARGURA_GRID)] for y in range(ALTURA_GRID)]
        shm.mutex_grid.release()

        # 2. Decidir a Ação.
        pos_x_atual = shm.pos_x_robos[id_robo]
        pos_y_atual = shm.pos_y_robos[id_robo]
        energia_atual = shm.energias_robos[id_robo]
        velocidade_robo = shm.velocidades_robos[id_robo]

        acao_escolhida = "esperar"
        id_bateria_alvo = -1
        # Posição planejada para a ação. Inicialmente a mesma posição atual.
        nova_pos_x, nova_pos_y = pos_x_atual, pos_y_atual

        # O robô pode tentar mover 'velocidade_robo' vezes por turno.
        # Ele priorizará ações de acordo com o que encontrar.
        # O robô faz V "tentativas" de movimento/ação por turno.
        for _ in range(velocidade_robo):
            # Tenta se mover em uma direção aleatória (ou ficar parado)
            dx, dy = random.choice([(0,1), (1,0), (0,-1), (-1,0), (0,0)]) # Norte, Leste, Sul, Oeste, Parado
            tentativa_x = (pos_x_atual + dx)
            tentativa_y = (pos_y_atual + dy)

            # Ajusta para os limites do tabuleiro
            tentativa_x = max(0, min(LARGURA_GRID - 1, tentativa_x))
            tentativa_y = max(0, min(ALTURA_GRID - 1, tentativa_y))

            conteudo_alvo_tentativa = copia_local_grid[tentativa_y][tentativa_x]

            # Prioridade de ações: Duelo > Coletar Bateria > Mover
            if '0' <= conteudo_alvo_tentativa <= str(MAX_ROBOS - 1) and int(conteudo_alvo_tentativa) != id_robo:
                id_oponente = int(conteudo_alvo_tentativa)
                if shm.status_robos[id_oponente] == STATUS_VIVO:
                    acao_escolhida = "duelar"
                    nova_pos_x, nova_pos_y = tentativa_x, tentativa_y
                    break # Ação prioritária, sair do loop de velocidade para executar
            
            elif conteudo_alvo_tentativa == chr(CELULA_BATERIA):
                acao_escolhida = "coletar_bateria"
                nova_pos_x, nova_pos_y = tentativa_x, tentativa_y
                # Encontra o ID da bateria a partir da posição armazenada
                for i, (bx, by) in enumerate(shm.posicoes_baterias):
                    if bx == nova_pos_x and by == nova_pos_y:
                        id_bateria_alvo = i
                        break
                if id_bateria_alvo != -1: # Se encontrou a bateria real
                    break # Ação prioritária, sair do loop de velocidade para executar
                else: # Bateria no grid, mas sem registro no posicoes_baterias (erro ou já foi coletada)
                    acao_escolhida = "esperar" # Não sabe o que fazer
            
            elif conteudo_alvo_tentativa == chr(CELULA_VAZIA) and energia_atual >= 1:
                acao_escolhida = "mover"
                nova_pos_x, nova_pos_y = tentativa_x, tentativa_y
                # Se decidiu mover, para simular a velocidade, a posição atual do robô é atualizada
                # para que ele possa tentar outro movimento a partir daqui no mesmo turno.
                pos_x_atual, pos_y_atual = nova_pos_x, nova_pos_y
            else:
                # Célula ocupada (barreira, robô morto) ou sem energia, não pode mover para lá
                pass # Tenta outra direção no loop de velocidade

        # Se depois de todas as tentativas de movimento não encontrou nada interessante ou não pode mover
        if acao_escolhida == "esperar" and (nova_pos_x == shm.pos_x_robos[id_robo] and nova_pos_y == shm.pos_y_robos[id_robo]):
            # Se não moveu nem escolheu outra ação, apenas espera um pouco
            time.sleep(0.05) # Pequena pausa para evitar busy-waiting
            continue # Próximo ciclo do loop principal do robô


        # 3. Adquirir locks necessários na ordem documentada.
        # Ordem de aquisição: Bateria -> Grid -> Robôs (atributos)
        locks_adquiridos_com_sucesso = {
            "bateria": False,
            "grid": False,
            "robos_atributos": False
        }
        
        # Flag para saber se precisamos re-tentar a ação completa
        re_tentar_acao = False

        try:
            # A. Tentar adquirir lock da BATERIA (se for coletar)
            if acao_escolhida == "coletar_bateria" and id_bateria_alvo != -1:
                atualizar_status_lock(id_robo, INDICE_LOCK_BATERIA, id_bateria_alvo, esta_pedindo=True)
                if not shm.mutexes_bateria[id_bateria_alvo].acquire(blocking=False):
                    print(f"Robô {id_robo}: Não conseguiu mutex_bateria[{id_bateria_alvo}]. Verificando deadlock...")
                    if detectar_deadlock_especifico(id_robo):
                        recuperar_deadlock_simples(id_robo)
                        re_tentar_acao = True
                    else:
                        print(f"Robô {id_robo}: Bloqueado esperando mutex_bateria[{id_bateria_alvo}]...")
                        shm.mutexes_bateria[id_bateria_alvo].acquire() # Bloqueia e espera
                if not re_tentar_acao: # Se não precisou recuperar, então o lock foi adquirido
                    atualizar_status_lock(id_robo, INDICE_LOCK_BATERIA, id_bateria_alvo, esta_segurando=True)
                    locks_adquiridos_com_sucesso["bateria"] = True

            if re_tentar_acao: continue # Pula para o próximo ciclo se houve recuperação (liberou tudo)

            # B. Tentar adquirir lock do GRID
            if acao_escolhida in ["mover", "coletar_bateria", "duelar"]:
                atualizar_status_lock(id_robo, INDICE_LOCK_GRID, esta_pedindo=True)
                if not shm.mutex_grid.acquire(blocking=False):
                    print(f"Robô {id_robo}: Não conseguiu mutex_grid. Verificando deadlock...")
                    if detectar_deadlock_especifico(id_robo):
                        recuperar_deadlock_simples(id_robo)
                        re_tentar_acao = True
                    else:
                        print(f"Robô {id_robo}: Bloqueado esperando mutex_grid...")
                        shm.mutex_grid.acquire() # Bloqueia e espera
                if not re_tentar_acao: # Se não precisou recuperar
                    atualizar_status_lock(id_robo, INDICE_LOCK_GRID, esta_segurando=True)
                    locks_adquiridos_com_sucesso["grid"] = True

            if re_tentar_acao: # Se recuperou aqui, libera bateria se já pegou
                if locks_adquiridos_com_sucesso["bateria"]:
                    shm.mutexes_bateria[id_bateria_alvo].release()
                    atualizar_status_lock(id_robo, INDICE_LOCK_BATERIA, id_bateria_alvo, esta_segurando=False)
                continue # Pula para o próximo ciclo se houve recuperação


            # C. Tentar adquirir lock dos ATRIBUTOS DOS ROBÔS (se for duelar)
            if acao_escolhida == "duelar":
                atualizar_status_lock(id_robo, INDICE_LOCK_ROBOS, esta_pedindo=True)
                if not shm.mutex_robos_atributos.acquire(blocking=False):
                    print(f"Robô {id_robo}: Não conseguiu mutex_robos_atributos. Verificando deadlock...")
                    if detectar_deadlock_especifico(id_robo):
                        recuperar_deadlock_simples(id_robo)
                        re_tentar_acao = True
                    else:
                        print(f"Robô {id_robo}: Bloqueado esperando mutex_robos_atributos...")
                        shm.mutex_robos_atributos.acquire() # Bloqueia e espera
                if not re_tentar_acao: # Se não precisou recuperar
                    atualizar_status_lock(id_robo, INDICE_LOCK_ROBOS, esta_segurando=True)
                    locks_adquiridos_com_sucesso["robos_atributos"] = True

            if re_tentar_acao: # Se recuperou aqui, libera grid e bateria se já pegou
                if locks_adquiridos_com_sucesso["bateria"]:
                    shm.mutexes_bateria[id_bateria_alvo].release()
                    atualizar_status_lock(id_robo, INDICE_LOCK_BATERIA, id_bateria_alvo, esta_segurando=False)
                if locks_adquiridos_com_sucesso["grid"]:
                    shm.mutex_grid.release()
                    atualizar_status_lock(id_robo, INDICE_LOCK_GRID, esta_segurando=False)
                continue # Pula para o próximo ciclo se houve recuperação


            # 4. Executar Ação (se todos os locks necessários foram adquiridos)
            if acao_escolhida == "mover" and locks_adquiridos_com_sucesso["grid"]:
                # Verifica a célula novamente sob o lock do grid para consistência
                if shm.obter_char_grid(nova_pos_x, nova_pos_y) == chr(CELULA_VAZIA) and shm.energias_robos[id_robo] >= 1:
                    shm.definir_char_grid(pos_x_atual, pos_y_atual, chr(CELULA_VAZIA))
                    shm.pos_x_robos[id_robo] = nova_pos_x
                    shm.pos_y_robos[id_robo] = nova_pos_y
                    shm.definir_char_grid(nova_pos_x, nova_pos_y, str(id_robo))
                    shm.energias_robos[id_robo] -= 1 # Consome 1 de energia
                    print(f"Robô {id_robo} moveu para ({nova_pos_x}, {nova_pos_y}). Energia: {shm.energias_robos[id_robo]}")
                else:
                    print(f"Robô {id_robo}: Não pôde mover para ({nova_pos_x}, {nova_pos_y}). Célula ocupada ou sem energia.")

            elif acao_escolhida == "coletar_bateria" and locks_adquiridos_com_sucesso["grid"] and locks_adquiridos_com_sucesso["bateria"]:
                if shm.obter_char_grid(nova_pos_x, nova_pos_y) == chr(CELULA_BATERIA):
                    shm.energias_robos[id_robo] = min(100, shm.energias_robos[id_robo] + 20) # Coletar +20 E (máx. 100)
                    shm.definir_char_grid(nova_pos_x, nova_pos_y, chr(CELULA_VAZIA)) # Bateria removida do grid
                    # A posição da bateria removida deve ser "apagada" da lista de posições de bateria
                    # para que outros robôs não tentem coletar uma bateria inexistente.
                    shm.posicoes_baterias[id_bateria_alvo] = (-1, -1) # Marca como coletada/inexistente
                    print(f"Robô {id_robo} coletou bateria em ({nova_pos_x}, {nova_pos_y}). Energia: {shm.energias_robos[id_robo]}")
                else:
                    print(f"Robô {id_robo}: Bateria em ({nova_pos_x}, {nova_pos_y}) já coletada ou não existe.")

            elif acao_escolhida == "duelar" and locks_adquiridos_com_sucesso["grid"] and locks_adquiridos_com_sucesso["robos_atributos"]:
                id_oponente = int(copia_local_grid[nova_pos_y][nova_pos_x]) # Pega o ID do oponente da cópia local
                # A negociação do duelo deve ocorrer dentro de grid_mutex, sem gerente.
                # A função _resolver_duelo será chamada aqui e já espera grid_mutex e mutex_robos_atributos adquiridos.
                if shm.status_robos[id_oponente] == STATUS_VIVO and shm.obter_char_grid(nova_pos_x, nova_pos_y) == str(id_oponente):
                    _resolver_duelo(id_robo, id_oponente, shm)
                else:
                    print(f"Robô {id_robo}: Oponente {id_oponente} em ({nova_pos_x},{nova_pos_y}) não está mais lá ou está morto para duelar.")
            # else: acao_escolhida == "esperar" ou locks não foram adquiridos, então não faz nada
        finally:
            # 5. Libera locks.
            # Libera na ordem inversa da aquisição para maior segurança (mas não estritamente obrigatório)
            if locks_adquiridos_com_sucesso["robos_atributos"]:
                shm.mutex_robos_atributos.release()
                atualizar_status_lock(id_robo, INDICE_LOCK_ROBOS, esta_segurando=False)
            if locks_adquiridos_com_sucesso["grid"]:
                shm.mutex_grid.release()
                atualizar_status_lock(id_robo, INDICE_LOCK_GRID, esta_segurando=False)
            if locks_adquiridos_com_sucesso["bateria"]:
                shm.mutexes_bateria[id_bateria_alvo].release()
                atualizar_status_lock(id_robo, INDICE_LOCK_BATERIA, id_bateria_alvo, esta_segurando=False)

        time.sleep(0.1) # Pequeno atraso para visualização

    print(f"Robô {id_robo}: Thread sense_act encerrada.")

# housekeeping (atualiza energia, escreve log, opera locks)
def funcao_thread_housekeeping(id_robo):
    global dados_compartilhados_do_jogo
    shm = dados_compartilhados_do_jogo # Alias para facilitar

    print(f"Robô {id_robo}: Thread housekeeping iniciada.")

    while not shm.jogo_acabou.value and shm.status_robos[id_robo] == STATUS_VIVO:
        time.sleep(0.5) # A cada 0.5 segundos (ajuste conforme necessário)

        # Reduz energia
        shm.mutex_robos_atributos.acquire()
        shm.energias_robos[id_robo] -= 1
        if shm.energias_robos[id_robo] <= 0:
            shm.status_robos[id_robo] = STATUS_MORTO # Robô morre se a energia acabar
            print(f"Robô {id_robo} morreu por falta de energia.")
        shm.mutex_robos_atributos.release()

        # Grava log (simplesmente printa para console)
        print(f"Robô {id_robo} (HK): Energia: {shm.energias_robos[id_robo]}, Pos: ({shm.pos_x_robos[id_robo]},{shm.pos_y_robos[id_robo]}), Status: {'Vivo' if shm.status_robos[id_robo] == STATUS_VIVO else 'Morto'}")

        # Checa condição de vitória (robôs vivos == 1)
        shm.mutex_robos_atributos.acquire()
        robos_vivos = 0
        ultimo_vivo_id = -1
        for i in range(MAX_ROBOS):
            if shm.status_robos[i] == STATUS_VIVO:
                robos_vivos += 1
                ultimo_vivo_id = i

        # Condição de vitória: Apenas 1 robô vivo E o jogo já foi inicializado
        if shm.jogo_inicializado.value and robos_vivos <= 1:
            shm.jogo_acabou.value = True
            if robos_vivos == 1:
                shm.id_vencedor.value = ultimo_vivo_id
            else: # Todos mortos
                shm.id_vencedor.value = -1
            print(f"FIM DE JOGO! Robôs vivos: {robos_vivos}. Vencedor: {shm.id_vencedor.value}")
        shm.mutex_robos_atributos.release()

    print(f"Robô {id_robo}: Thread housekeeping encerrada.")


def processo_robo(id_do_robo, dados_compartilhados):
    """
    Função principal que será executada por cada processo de robô.
    Cria as threads sense_act e housekeeping.
    """
    global dados_compartilhados_do_jogo
    dados_compartilhados_do_jogo = dados_compartilhados # Injeta a referência global

    print(f"Processo do Robô {id_do_robo} iniciado.")

    thread_sa = threading.Thread(target=funcao_thread_sense_act, args=(id_do_robo,))
    thread_hk = threading.Thread(target=funcao_thread_housekeeping, args=(id_do_robo,))

    thread_sa.start()
    thread_hk.start()

    thread_sa.join() # Espera a thread sense_act terminar
    thread_hk.join() # Espera a thread housekeeping terminar

    print(f"Processo do Robô {id_do_robo} encerrado.")