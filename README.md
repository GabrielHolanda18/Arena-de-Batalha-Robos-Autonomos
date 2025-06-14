# 🤖 Arena dos Processos - Batalha dos Robôs Autônomos

## Discrição
Este é um trabalho acadêmico final elaborado e desenvolvido pelo grupo de Ciência da Computação da UERJ. 

O projeto foi construído usando a liguagem de programação Python, com as bibliotecas nativas da própria linguagem. 

Motivações: Demonstrar a funcionalidade de um sistema totalmente distribuído sobre processos e threads locais. 

Jogo em modo texto (ASCII), totalmente distribuído, onde robôs autônomos duelam entre si por recursos (baterias) e sobrevivência. O jogo foi implementado em **Python com orientação a objetos**, utilizando **processos e threads locais**, além de **memória compartilhada e mecanismos de sincronização**.

---

## Objetivo

Nosso objetivo nesse trabalho foi apresentar um jogo que simula uma arena de robôs com inteligência programável disputando recursos gameficados. 
Cada robô, representado por um processo, deve se mover estrategicamente, coletar baterias para manter sua energia e duelar contra outros robôs que cruzarem seu caminho. O último robô vivo vence.

---

## Tecnologias e Conceitos

- `multiprocessing.Process` e `threading.Thread`
- `multiprocessing.Manager()` para memória compartilhada
- Locks para sincronização: `mutex_grid`, `mutex_robos_atributos`, `mutexes_bateria`
- Detecção e recuperação de **deadlock**
- Visualização em tempo real (ASCII) com cores ANSI
- Modularização por responsabilidade (arquivos separados)

---

## 📁 Estrutura de Arquivos

main.py # Menu principal do jogo

configuracao_jogo.py # Estruturas compartilhadas (memória e locks)

processo_robo.py # Lógica e comportamento dos robôs

processo_visualizador.py # Renderização em tempo real do tabuleiro

sincronizacao.py # Controle de deadlock e sincronização

demonstracao_deadlock.py # Execução de cenários de deadlock

Deadlock_robo.py # Deadlock forçado (exemplo)

Deadlock_robo_prev.py # Prevenção de deadlock (ordenação de locks)

## Como Jogar

1. **Execute o menu principal**:
   ```bash
   python main.py
Escolha uma das opções:

1: Rodar o jogo principal (simulação completa)

2: Demonstrar deadlock e prevenção

3: Sair

## Regras do Jogo
Tabuleiro: 40x20 células

Máximo de 4 robôs e 8 baterias

Cada robô possui:
- Força (F)
- Energia (E)
- Velocidade (V)
- Poder de duelo: Poder = 2F + E

Robôs podem: 
- Mover
- Coletar bateria (+20 energia)
- Duelar ao colidir com outro robô

Empates no duelo: ambos destruídos

## Sincronização e Deadlock
Ordem obrigatória de locks:

mutex_bateria

mutex_grid

mutex_robos_atributos

A violação dessa ordem é simulada para mostrar deadlocks.

Robôs detectam e tentam recuperar automaticamente de deadlocks.

## Visualização
A visualização é feita em tempo real no terminal com símbolos ASCII:

## Símbolo	Significado

"0-3"	Robôs (cores diferentes)

"#"	Barreira (fixa)

"B"	Bateria (recupera energia)

"." Célula vazia

## Condições de Término
Apenas 1 robô vivo: vitória

Todos destruídos: empate

O programa detecta o fim do jogo automaticamente e exibe o vencedor.

## Créditos e Autoria
Desenvolvido por: Leonardo Arigoni, Gabriel Holanda e Carlos Augusto

✅ Requisitos
Python 3.8+


