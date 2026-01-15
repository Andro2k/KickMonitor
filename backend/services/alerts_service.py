# services/alerts_service.py

from typing import Tuple

class AlertsService:
    """
    Servicio de Automatización de Mensajes.
    """
    
    def __init__(self, db_handler):
        self.db = db_handler
        self.DEFAULTS_ALERTS = {
            "follow": "¡Gracias {user} por seguir el canal! Bienvenid@ 😎",
            "subscription": "¡Wow! Gracias {user} por esa suscripción 👑",
            "host": "Gracias {user} por el host con {viewers} espectadores 🙌"
        }
        
        self.DEFAULTS_TIMERS = {
            "redes": ("¡Sígueme en mis redes! twitter.com/usuario", 15),
            "discord": ("¡Únete a la comunidad! discord.gg/ejemplo", 30),
            "promo": ("¡Usa el código KICK para descuentos!", 45)
        }

    # =========================================================================
    # REGIÓN 1: ALERTAS DE CHAT (EVENTOS)
    # =========================================================================
    def get_alert_config(self, event_type: str) -> Tuple[str, bool]:
        """Obtiene mensaje y estado. Si no existe, crea uno por defecto."""
        msg, active = self.db.get_text_alert(event_type)
        
        if not msg and event_type in self.DEFAULTS_ALERTS:
            msg = self.DEFAULTS_ALERTS[event_type]
            self.db.set_text_alert(event_type, msg, False) 
            active = False
            
        return msg, active

    def save_alert(self, event_type: str, message: str, active: bool) -> bool:
        """Guarda la configuración de una alerta de evento."""
        return self.db.set_text_alert(event_type, message, active)
    
    # =========================================================================
    # REGIÓN 2: TIMERS (MENSAJES RECURRENTES)
    # =========================================================================
    def get_timer_config(self, name: str) -> Tuple[str, int, bool]:
        """Obtiene mensaje, intervalo y estado de un timer."""
        msg, interval, active = self.db.get_timer(name)
        
        if not msg and name in self.DEFAULTS_TIMERS:
            def_msg, def_int = self.DEFAULTS_TIMERS[name]
            self.db.set_timer(name, def_msg, def_int, False)
            return def_msg, def_int, False
            
        return msg, interval, active

    def save_timer(self, name: str, msg: str, interval: int, active: bool) -> bool:
        """Guarda la configuración de un timer recurrente."""
        return self.db.set_timer(name, msg, interval, active)