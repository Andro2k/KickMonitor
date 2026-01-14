# backend/casino.py

import random
from typing import Tuple, Optional, Dict, Any

class CasinoSystem:
    # ==========================================
    # 1. CONSTANTES Y REGLAS DE JUEGO
    # ==========================================
    
    # --- RULETA ---
    ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    ROULETTE_BLACK = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
    ROULETTE_EMOJIS = {"rojo": "🔴", "negro": "⚫", "verde": "🟢"}
    
    # --- SLOTS ---
    SLOTS_SYMBOLS = ["🍒", "🍋", "🍇", "💎", "7️⃣"]
    
    # --- CARTAS ---
    CARD_VALUES = {
        2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 
        11: "J", 12: "Q", 13: "K", 14: "A"
    }
    CARD_SUITS = ["♠️", "♥️", "♦️", "♣️"]

    def __init__(self, db):
        self.db = db

    # ==========================================
    # 2. DISPATCHER (PUNTO DE ENTRADA)
    # ==========================================
    def resolve_bet(self, user: str, amount_str: str, game_type: str, *args) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Gestiona el flujo de la apuesta.
        Retorna: (Mensaje para Chat, Diccionario para Historial o None)
        """
        # 1. Verificar si el casino está habilitado globalmente
        if not self.db.get_bool("gamble_enabled"):
            return "⛔ El casino está cerrado en este momento.", None

        # 2. DETECTAR AYUDA (NUEVO)
        # Si el usuario escribe solo el comando, amount_str llega como "help"
        if amount_str in ["help", "ayuda", "?"]:
            return self._get_game_help(game_type), None

        # 3. Parsear el monto
        amount, error_msg = self._parse_amount(user, amount_str)
        if error_msg: 
            # Si falló el parseo, devolvemos el error pero sugerimos ayuda
            return f"{error_msg} (Usa !{game_type} help para ver instrucciones)", None

        # 4. Validar límites y saldo
        is_valid, validation_msg = self._validate_bet(user, amount)
        if not is_valid:
            return validation_msg, None

        # 5. Enrutar al juego específico
        game_map = {
            "slots": lambda: self._play_slots(user, amount),
            "dice": lambda: self._play_dice(user, amount),
            "highcard": lambda: self._play_high_card(user, amount),
            # Ruleta necesita un argumento extra (la predicción)
            "roulette": lambda: self._play_roulette(user, amount, args[0] if args else None)
        }

        handler = game_map.get(game_type)
        
        if handler:
            return handler()
        else:
            return "⚠️ Error interno: Juego no reconocido.", None

    def _get_game_help(self, game_type: str) -> str:
        """Retorna instrucciones específicas para cada juego."""
        msgs = {
            "slots": "🎰 Slots: Alinea 3 símbolos iguales.\nUso: `!slots {cantidad}`",
            "dice": "🎲 Dados: Lanza un dado (1-100). Ganas si sacas 45 o menos.\nUso: `!dados {cantidad}`",
            "highcard": "🃏 Carta Alta: Saca una carta más alta que la del Bot.\nUso: `!carta {cantidad}`",
            "roulette": "🎡 Ruleta: Apuesta a color (x2) o número (x35).\nUso: `!ruleta {cantidad} {rojo/negro/verde/0-36}`"
        }
        return msgs.get(game_type, "Juego desconocido.")

    # ==========================================
    # 3. UTILIDADES DE VALIDACIÓN
    # ==========================================
    def _parse_amount(self, user: str, amount_str: str) -> Tuple[int, Optional[str]]:
        """Convierte inputs como 'all', '50%', '100' a un entero seguro."""
        try:
            current_points = self.db.get_points(user)
            s_amount = str(amount_str).lower().strip()
            
            if s_amount in ["all", "todo", "max"]:
                return current_points, None
            
            if "%" in s_amount:
                pct_str = s_amount.replace("%", "")
                if not pct_str.isdigit():
                    return 0, f"@{user} ⚠️ Porcentaje inválido."
                pct = int(pct_str)
                if pct <= 0: 
                    return 0, f"@{user} ⚠️ El porcentaje debe ser positivo."
                return int(current_points * (pct / 100)), None
            
            val = int(s_amount)
            return val, None
            
        except ValueError:
            return 0, f"@{user} ⚠️ El monto debe ser un número."

    def _validate_bet(self, user: str, amount: int) -> Tuple[bool, Optional[str]]:
        if amount <= 0:
            return False, f"@{user} 🤨 No puedes apostar 0 o negativo."

        current_points = self.db.get_points(user)
        min_bet = self.db.get_int("gamble_min", 10)
        max_bet = self.db.get_int("gamble_max", 50000)

        if amount < min_bet:
            return False, f"@{user} 📉 Mínimo: {min_bet}."
        
        if amount > max_bet:
            return False, f"@{user} 📈 Máximo: {max_bet}."
        
        if amount > current_points:
            return False, f"@{user} 💸 No tienes suficientes puntos ({current_points})."

        return True, None

    # ==========================================
    # 4. MOTORES DE JUEGO
    # ==========================================
    
    # --- SLOTS ---
    def _play_slots(self, user: str, bet: int) -> Tuple[str, Dict]:
        self.db.spend_points(user, bet)
        rollers = [random.choice(self.SLOTS_SYMBOLS) for _ in range(3)]
        result_display = f"[{' | '.join(rollers)}]"
        
        profit = -bet
        is_win = False
        
        # Victoria: 3 iguales
        if rollers[0] == rollers[1] == rollers[2]:
            multiplier = self.db.get_int("slots_jackpot_x", 10000)
            payout = int(bet * multiplier)
            self.db.add_points(user, payout)
            profit = payout - bet
            is_win = True
            msg = f"@{user} 🎰 {result_display} ¡JACKPOT! (+{payout})"
        else:
            msg = f"@{user} 🎰 {result_display} ..."
        
        return msg, self._build_history(user, "slots", result_display, profit, is_win)

    # --- DADOS ---
    def _play_dice(self, user: str, bet: int) -> Tuple[str, Dict]:
        self.db.spend_points(user, bet)
        win_rate = self.db.get_int("gamble_win_rate", 45)
        multiplier = float(self.db.get("gamble_multiplier") or "2.0")
        
        roll = random.randint(1, 100)
        is_win = roll <= win_rate
        profit = -bet
        
        if is_win:
            payout = int(bet * multiplier)
            self.db.add_points(user, payout)
            profit = payout - bet
            msg = f"@{user} 🎲 Sacaste {roll} (Necesitas ≤ {win_rate}). ¡GANASTE! (+{profit})"
        else:
            msg = f"@{user} 🎲 Sacaste {roll}. Perdiste {bet}."

        return msg, self._build_history(user, "dice", f"Roll: {roll}", profit, is_win)

    # --- RULETA (MEJORADO) ---
    def _play_roulette(self, user: str, bet: int, prediction: any) -> Tuple[str, Optional[Dict]]:
        # Si no pone predicción, devolvemos la ayuda específica
        if not prediction:
            return self._get_game_help("roulette"), None

        pred_str = str(prediction).lower().strip()
        
        # Normalizar colores (español/inglés)
        color_map = {"red": "rojo", "black": "negro", "green": "verde"}
        user_pred = color_map.get(pred_str, pred_str) # Si es "red" lo pasa a "rojo", si es "14" lo deja "14"
        
        valid_colors = ["rojo", "negro", "verde"]
        is_number_bet = user_pred.isdigit()
        
        if not is_number_bet and user_pred not in valid_colors:
            return f"@{user} ⚠️ Predicción inválida. Elige: rojo, negro, verde o un número (0-36).", None
        
        if is_number_bet and not (0 <= int(user_pred) <= 36):
             return f"@{user} ⚠️ El número debe ser entre 0 y 36.", None

        # Ejecutar apuesta
        self.db.spend_points(user, bet)
        
        # Tirada
        roll = random.randint(0, 36)
        
        # Determinar color del resultado
        if roll == 0:
            roll_color = "verde"
        elif roll in self.ROULETTE_RED:
            roll_color = "rojo"
        else:
            roll_color = "negro"
            
        result_emoji = self.ROULETTE_EMOJIS.get(roll_color, "⚪")
        result_txt = f"{result_emoji} Salió {roll_color.upper()} {roll}" # Ej: 🔴 Salió ROJO 9

        # Verificar Victoria
        did_win = False
        multi = 0.0
        
        if is_number_bet:
            # Apuesta a número exacto
            if roll == int(user_pred):
                did_win = True
                multi = float(self.db.get("roulette_multi_num") or 35.0)
        else:
            # Apuesta a color
            if user_pred == roll_color:
                did_win = True
                # El verde paga más si aciertas color
                if roll_color == "verde":
                    multi = float(self.db.get("roulette_multi_num") or 35.0)
                else:
                    multi = float(self.db.get("roulette_multi_col") or 2.0)

        # Mensaje Final
        profit = -bet
        if did_win:
            payout = int(bet * multi)
            self.db.add_points(user, payout)
            profit = payout - bet
            msg = f"@{user} {result_txt}. ¡Acertaste al {user_pred.upper()}! (+{profit})"
        else:
            # Mensaje de derrota más claro
            bet_display = user_pred.upper()
            msg = f"@{user} {result_txt}. Apostaste {bet_display} y perdiste {bet}."

        return msg, self._build_history(user, "roulette", f"{roll_color} {roll}", profit, did_win)

    # --- CARTA ALTA ---
    def _play_high_card(self, user: str, bet: int) -> Tuple[str, Dict]:
        self.db.spend_points(user, bet)
        multiplier = float(self.db.get("highcard_multiplier") or 2.0)
        
        def draw():
            val = random.choice(list(self.CARD_VALUES.keys()))
            display_val = self.CARD_VALUES[val]
            suit = random.choice(self.CARD_SUITS)
            return val, f"{display_val}{suit}"

        p_val, p_display = draw()
        b_val, b_display = draw()
        
        display_txt = f"Tú:[{p_display}] vs Bot:[{b_display}]"
        
        profit = -bet
        is_win = False
        
        if p_val > b_val:
            payout = int(bet * multiplier)
            self.db.add_points(user, payout)
            profit = payout - bet
            is_win = True
            msg = f"@{user} 🃏 {display_txt} ¡GANASTE! (+{profit})"
        elif p_val < b_val:
            msg = f"@{user} 🃏 {display_txt} Gana la casa."
        else:
            self.db.add_points(user, bet)
            profit = 0
            msg = f"@{user} 🃏 {display_txt} ¡EMPATE! (Devuelto)"

        return msg, self._build_history(user, "highcard", display_txt, profit, is_win)

    # ==========================================
    # 5. HELPER DE HISTORIAL
    # ==========================================
    def _build_history(self, user, game, res, profit, win) -> Dict[str, Any]:
        return { "user": user, "game": game, "res": res, "profit": profit, "win": win }