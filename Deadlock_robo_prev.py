import multiprocessing
import time
import logging

logging.basicConfig(filename='deadlock_log.txt', level=logging.INFO,
                    format='[%(asctime)s] :: %(levelname)s :: %(message)s',
                    encoding='utf-8')
                    
def robo_a(battery_mutex, grid_mutex):
    """
    O Robô A tenta adquirir o lock1(battery_mutex) e depois o lock2(grid_battery).
    """
    logging.info(f"Iniciando a Prevenção de Deadlock\n")
    #print(f"Robô: Tentando travar battery_mutex...")
    logging.info(f"O Robô A Tentando travar battery_mutex...")
    battery_mutex.acquire() # Adquire o primeiro lock
    #print(f"Robô A: Trava battery_mutex. Agora tentando grid_mutex...")
    logging.info(f"O Robô A Trava battery_mutex. Agora tentando grid_mutex...")
    time.sleep(0.1) # Simula algum trabalho ou troca de contexto
    grid_mutex.acquire() # Tenta adquirir o segundo lock

    print(f"Robô A: Ambos os locks adquiridos. Executando trabalho...")
    # Seção crítica
    time.sleep(1)
    print(f"Robô A: Liberando locks.")
    grid_mutex.release()
    battery_mutex.release()

def robo_b(battery_mutex, grid_mutex):
    """
    O Robô B também tenta adquirir battery_mutex primeiro e depois grid_mutex.
    Esta ordem consistente PREVINE o deadlock.    
    """
    #print(f"Robô B: Tentando o grid_mutex...")
    logging.info(f"Robô B: Tentando o battery_mutex...")
    battery_mutex.acquire() # Adquire o primeiro lock
    #print(f"Robô B: Grid_mutex adquirido. Agora tentando travar battery_mutex...")
    logging.info(f"Robô B: battery_mutex adquirido. Agora tentando travar grid_mutex...")
    time.sleep(0.1) # Simula algum trabalho ou troca de contexto
    grid_mutex.acquire() # Tenta adquirir o segundo lock

    print(f"Robô B: Ambos os locks adquiridos. Executando trabalho...")
    # Seção crítica
    time.sleep(1)
    print(f"Robô B: Liberando locks.")
    battery_mutex.release()
    grid_mutex.release()

if __name__ == "__main__":
    print("Simulando Cenário de Deadlock com Dois Robôs.")

    # Cria dois locks (recursos) que serão compartilhados pelos robôs
    battery_mutex = multiprocessing.Lock()
    grid_mutex = multiprocessing.Lock()

    # Cria dois robôs, passando os locks como argumentos
    p1 = multiprocessing.Process(target=robo_a, args=(battery_mutex, grid_mutex))
    p2 = multiprocessing.Process(target=robo_b, args=(battery_mutex, grid_mutex))

    # Inicia os processos
    p1.start()
    p2.start()

    # Espera os robôs terminarem. Em caso de deadlock, eles nunca terminam.
    p1.join()
    p2.join()

    print("\nSimulação finalizada. Se os processos não completaram, um deadlock ocorreu.")
    logging.info(f"Simulação finalizada.\n")
    print("Para observar o deadlock, você pode precisar encerrar o programa manualmente (Ctrl+C).")
