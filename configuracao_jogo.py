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
# A ordem de aquisição deve ser documentada e seguida por todos os robôs:
# 1. Mutex de Bateria (se aplicável)
# 2. Mutex do Grid
# 3. Mutex de Atributos dos Robôs
INDICE_LOCK_BATERIA = 0
INDICE_LOCK_GRID = 1
INDICE_LOCK_ROBOS = 2


# Manager é uma instancia de multiprocessing.Manager() que cria objetos compartilhados
class DadosCompartilhados:
    def __init__(self, manager):
        # Grid do jogo (matriz)
        # CORREÇÃO AQUI: De manager.Array("c", ...) ou manager.Array(ctypes.c_char, ...)
        # Para manager.Array("B", b' ' * ...)
        self.tabuleiro_grid = manager.Array("B", b' ' * (LARGURA_GRID * ALTURA_GRID))
        for i in range(LARGURA_GRID * ALTURA_GRID):
            self.tabuleiro_grid[i] = CELULA_VAZIA # Inicializa tudo vazio

        # Atributos dos Robôs Arrays separados para cada atributo
        self.ids_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.forcas_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.energias_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.velocidades_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.pos_x_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.pos_y_robos = manager.Array('i', [0] * MAX_ROBOS)
        self.status_robos = manager.Array('i', [0] * MAX_ROBOS) # Vivo/Morto # Vivo/Morto

        # Flags do Jogo
        self.jogo_inicializado = manager.Value(ctypes.c_bool, False) # config inicial 
        self.jogo_acabou = manager.Value(ctypes.c_bool, False)      # jogo terminou
        self.id_vencedor = manager.Value(ctypes.c_int, -1)           # Quem venceu id robo

        # Posições das baterias (para mapear a célula do grid para o mutex da bateria)
        # tupla (x, y)
        self.posicoes_baterias = manager.list([(0,0)] * MAX_BATERIAS) # Inicializa com valores padrão

        # Mutexes (Locks) para Sincronização
        self.mutex_grid = manager.Lock()  # Protege o acesso ao tabuleiro_grid
        self.mutex_robos_atributos = manager.Lock() # Protege o acesso de atributos dos robôs
        self.mutexes_bateria = [manager.Lock() for _ in range(MAX_BATERIAS)] # Um lock por bateria
        self.mutex_inicializacao = manager.Lock() # Para a inicialização do jogo

        # --- Variáveis para Detecção de Deadlock ---
        self.mutex_deadlock_detector = manager.Lock() # Protege as estruturas de detecção
        
        # Para verificar se o robô tem o mutex_grid
        # exemplo: lock_segurado_grid[robo_id] = verdade se o robô tem o mutex_grid
        #lock_segurado_bateria[robo_id * MAX_BATERIAS + bateria_idx] = verdade se o robô tem a bateria
        #lock_segurado_robos[robo_id] = verdade se o robô tem o mutex_robos_atributos

        self.lock_segurado_grid = manager.Array('b', [False] * MAX_ROBOS) # 'b' para bools (0/1)
        self.lock_segurado_bateria = manager.Array('b', [False] * (MAX_ROBOS * MAX_BATERIAS))
        self.lock_segurado_robos = manager.Array('b', [False] * MAX_ROBOS)

        # Para verificar quem está pedindo qual lock
        # lock_pedido_grid[robo_id] = se o robô está pedindo o mutex_grid
        # lock_pedido_bateria[robo_id * MAX_BATERIAS + bateria_idx] = se o robô está pedindo a bateria
        # lock_pedido_robos[robo_id] = se o robô está pedindo o mutex_robos_atributos

        self.lock_pedido_grid = manager.Array('b', [False] * MAX_ROBOS)
        self.lock_pedido_bateria = manager.Array('b', [False] * (MAX_ROBOS * MAX_BATERIAS))
        self.lock_pedido_robos = manager.Array('b', [False] * MAX_ROBOS)

        # Para registrar qual bateria um robô está tentando adquirir
        # fundamental para a detectar o deadlock verifica se o 
        # Robô B tem GRID e quer a mesma bateria que o Robô A possui
        self.tentando_pegar_bateria_id = manager.Array('i', [-1] * MAX_ROBOS) # -1 se não estiver
        for i in range(MAX_ROBOS): self.tentando_pegar_bateria_id[i] = -1

    # Funções para verifica se estão dentro dos limites do tabuleiro.
    def obter_char_grid(self, x, y):
        """Retorna o caractere da célula (x,y) do grid."""
        if 0 <= x < LARGURA_GRID and 0 <= y < ALTURA_GRID:
            return chr(self.tabuleiro_grid[y * LARGURA_GRID + x])
        return ' ' # Fora dos limites

    def definir_char_grid(self, x, y, char_val):
        """Define o caractere na célula (x,y) do grid."""
        if 0 <= x < LARGURA_GRID and 0 <= y < ALTURA_GRID:
            self.tabuleiro_grid[y * LARGURA_GRID + x] = ord(char_val)