import subprocess
import time
import os

def limpar_terminal():
    """Limpa a tela do terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def executar_demonstracao_deadlock():
    """
    Executa o script que provoca o deadlock.
    """
    print("\n" + "="*70)
    print("DEMONSTRAÇÃO 1: PROVOCAÇÃO DO DEADLOCK")
    print("="*70 + "\n")
    print("Nesta parte, os robôs tentarão adquirir locks em ordens diferentes,")
    print("levando a um 'abraço mortal' e o programa ficará travado.")
    print("Você precisará encerrar manualmente (Ctrl+C) após observar o deadlock.")
    print("\nIniciando 'Deadlock_robo.py'...")

    try:
        # Executa o script e permite que ele seja encerrado manualmente
        processo = subprocess.Popen(['python', 'Deadlock_robo.py'])
        
        # Espera um tempo para o deadlock ocorrer.
        # Você pode precisar ajustar este tempo dependendo da sua máquina.
        print("\nObservando o deadlock. O programa ficará travado...")
        print("Pressione Ctrl+C NO TERMINAL para encerrar esta parte da demonstração.")
        processo.wait() # Espera o processo terminar (ou ser interrompido)
        
    except KeyboardInterrupt:
        print("\n\nDeadlock observado e processo encerrado (Ctrl+C).")
    except Exception as e:
        print(f"\nOcorreu um erro ao executar a demonstração de deadlock: {e}")

    time.sleep(2) # Pequena pausa antes de continuar

def executar_demonstracao_prevencao():
    """
    Executa o script que implementa a prevenção do deadlock.
    """
    print("\n" + "="*70)
    print("DEMONSTRAÇÃO 2: PREVENÇÃO DO DEADLOCK (Ordenamento de Recursos)")
    print("="*70 + "\n")
    print("Nesta parte, os robôs tentarão adquirir os locks na MESMA ordem,")
    print("prevenindo o deadlock. O programa deverá ser executado até o fim.")
    print("\nIniciando 'Deadlock_robo_prev.py'...")

    try:
        # Executa o script e espera que ele termine normalmente
        subprocess.run(['python', 'Deadlock_robo_prev.py'], check=True)
        print("\nPrevenção bem-sucedida! O programa terminou sem deadlock.")
    except subprocess.CalledProcessError as e:
        print(f"\nO script de prevenção falhou com erro: {e}")
    except Exception as e:
        print(f"\nOcorreu um erro ao executar a demonstração de prevenção: {e}")

    time.sleep(2) # Pequena pausa antes de finalizar

if __name__ == "__main__":
    limpar_terminal()
    print("Iniciando a Demonstração de Deadlock e Prevenção.")
    
    # 1. Demonstração do Deadlock
    executar_demonstracao_deadlock()
    
    # Pausa antes da próxima demonstração
    print("\nPreparando para a próxima demonstração...")
    time.sleep(3)
    limpar_terminal() # Limpa o terminal novamente para a nova etapa

    # 2. Demonstração da Prevenção
    executar_demonstracao_prevencao()

    print("\n\nDemonstração completa. Verifique os logs para mais detalhes.")
