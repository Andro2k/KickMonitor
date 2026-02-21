# backend/handlers/game_handler.py

from typing import Callable

class GameHandler:
    """
    Gestiona la lógica de interacción con el Casino.
    """
    def __init__(self, db_handler, casino_system):
        self.db = db_handler
        self.casino = casino_system
        self.game_map = { 
            "!gamble": "dice", "!dados": "dice", 
            "!roulette": "roulette", "!ruleta": "roulette", 
            "!slots": "slots", "!tragamonedas": "slots", 
            "!carta": "highcard", "!highcard": "highcard" 
        }

    # =========================================================================
    # REGIÓN 1: COMANDOS DE APUESTA (INPUT)
    # =========================================================================
    def handle_command(self, user: str, msg_lower: str, 
                       send_msg: Callable[[str], None], 
                       on_game_result: Callable[[str, str, str, bool], None]) -> bool:
        args = msg_lower.split(" ")
        cmd = args[0]

        # 1. Comando de Ayuda
        if cmd == "!casino": 
            send_msg("🎰 Juegos: !dados, !ruleta, !slots, !carta")
            return True
            
        # 2. Verificar si es un comando de juego válido
        target_game = self.game_map.get(cmd)
        if target_game:
            bet = args[1] if len(args) > 1 else "help"
            extra = args[2] if len(args) > 2 else None    
            msg_response, game_data = self.casino.resolve_bet(user, bet, target_game, extra)
            send_msg(msg_response)
            
            # El juego ya se resolvió, registramos y notificamos a la UI directamente aquí
            if game_data:
                self._record_and_notify(game_data, on_game_result)
            return True
            
        return False

    def _record_and_notify(self, data: dict, callback: Callable):
        """Guarda en DB y emite la señal visual a la frontend."""
        self.db.add_gamble_entry(
            data['user'], data['game'], 
            data['res'], data['profit'], data['win']
        )       
        display_str = f"{data['res']} ({data['profit']})"
        callback(data['user'], data['game'], display_str, data['win'])