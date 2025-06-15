import multiprocessing as mp
import ctypes

# Configuração de acordo com o PDF do Jogo

# Tabuleiro do jogo
LARGURA_GRID = 40
ALTURA_GRID = 20

MAX_ROBOS = 4
MAX_BATERIAS = 8 

# identificador de Células no Tabuleiro 
CELULA_VAZIA = ord('.')
CELULA_BARREIRA = ord('#')
CELULA_BATERIA = ord('B')

# Status do Robô 
STATUS_VIVO = 0
STATUS_MORTO = 1

# Controle de Locks na Detecção de Deadlock (Ordem de Aquisição) 
# 1. Mutex de Bateria | 2. Mutex do Grid | 3. Mutex de Atributos dos Robôs
INDICE_LOCK_BATERIA = 0
INDICE_LOCK_GRID = 1
INDICE_LOCK_ROBOS = 2

# Manager é uma instancia de multiprocessing.Manager() que cria objetos compartilhados.
class DadosCompartilhados:
    def __init__(self, manager):
        # Grid do jogo (matriz)
       
        self.tabuleiro_grid = manager.Array("B", b' ' * (LARGURA_GRID * ALTURA_GRID))
        for i in range(LARGURA_GRID * ALTURA_GRID):
            self.tabuleiro_grid[i] = CELULA_VAZIA # Inicializa tudo vazio

        # Atributos dos Robôs separados para cada atributo
        self.ids_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.forcas_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.energias_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.velocidades_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.pos_x_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.pos_y_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.status_robos = manager.Array('i', [0] * MAX_ROBOS) 

        # estado do Jogo

        # config inicial 
        self.jogo_inicializado = manager.Value(ctypes.c_bool, False) 

        # jogo terminou
        self.jogo_acabou = manager.Value(ctypes.c_bool, False)    

         # vencedor id robo
        self.id_vencedor = manager.Value(ctypes.c_int, -1)          

        # Posições das baterias (para mapear a célula do grid para o mutex da bateria)
        # tupla (x, y)
        self.posicoes_baterias = manager.list([(0,0)] * MAX_BATERIAS)

        # Mutexes (Locks) para Sincronização
        self.mutex_grid = manager.Lock()  # Protege o acesso ao tabuleiro_grid
        self.mutex_robos_atributos = manager.Lock() # Protege o acesso de atributos dos robôs
        self.mutexes_bateria = [manager.Lock() for _ in range(MAX_BATERIAS)] # Um lock por bateria
        self.mutex_inicializacao = manager.Lock() # Para a inicialização do jogo

        # --- Variáveis para Detecção de Deadlock ---
        self.mutex_deadlock_detector = manager.Lock() # Protege as estruturas de detecção
        
        # Para verificar se o robô tem o mutex_grid
        
        self.lock_segurado_grid = manager.Array('b', [False] * MAX_ROBOS) 
        self.lock_segurado_bateria = manager.Array('b', [False] * (MAX_ROBOS * MAX_BATERIAS))
        self.lock_segurado_robos = manager.Array('b', [False] * MAX_ROBOS)

        # Para verificar quem está pedindo qual lock
        
        self.lock_pedido_grid = manager.Array('b', [False] * MAX_ROBOS)
        self.lock_pedido_bateria = manager.Array('b', [False] * (MAX_ROBOS * MAX_BATERIAS))
        self.lock_pedido_robos = manager.Array('b', [False] * MAX_ROBOS)

        # Para registrar qual bateria um robô está tentando adquirir
        # fundamental para a detectar o deadlock verifica se o 
        # Robô B tem GRID e quer a mesma bateria que o Robô A possui
        self.tentando_pegar_bateria_id = manager.Array('i', [-1] * MAX_ROBOS) # -1 se não estiver
        for i in range(MAX_ROBOS): self.tentando_pegar_bateria_id[i] = -1

    # Funções para verifica se estão dentro do tabuleiro.
    def obter_char_grid(self, x, y):
        """Retorna o caractere da célula (x,y) do grid."""
        if 0 <= x < LARGURA_GRID and 0 <= y < ALTURA_GRID:
            return chr(self.tabuleiro_grid[y * LARGURA_GRID + x])
        return ' ' # Fora dos limites

    def definir_char_grid(self, x, y, char_val):
        """Define o caractere na célula (x,y) do grid."""
        if 0 <= x < LARGURA_GRID and 0 <= y < ALTURA_GRID:
            self.tabuleiro_grid[y * LARGURA_GRID + x] = ord(char_val)