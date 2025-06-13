def duel(robo1, robo2, duel_lock):
    with duel_lock:
        winner = robo1 if robo1.energy >= robo2.energy else robo2
        loser = robo2 if winner == robo1 else robo1
        print(f"{winner.name} venceu o duelo contra {loser.name}!")
        return winner

def _calcular_poder(forca, energia):
    """Calcula o poder de ataque do robô conforme o PDF."""
    return 2 * forca + energia # Poder=2F+E 

