# backend/services/alerts_service.py

from typing import Tuple

class AlertsService:
    """
    Servicio de Automatización de Mensajes y Alertas.
    """
    
    # 🔴 1. Añadimos alert_worker al __init__
    def __init__(self, db_handler, alert_worker=None):
        self.db = db_handler
        self.alert_worker = alert_worker 
        
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

    # 🔴 2. NUEVA FUNCIÓN: El motor que dispara la alerta
    def trigger_alert(self, event_type: str, username: str, extra_data: dict = None):
        """
        Verifica si la alerta está activa, formatea el texto y la envía a OBS.
        Retorna el mensaje final por si también quieres enviarlo al chat de Kick.
        """
        msg_template, is_active = self.get_alert_config(event_type)
        
        if not is_active:
            return None # Si está apagada en la UI, no hacemos nada
            
        # A. Formatear el mensaje (reemplazar variables)
        final_msg = msg_template.replace("{user}", username)
        
        if extra_data:
            for key, value in extra_data.items():
                final_msg = final_msg.replace(f"{{{key}}}", str(value))
                
        # B. Títulos bonitos para el Overlay de OBS
        titles = {
            "follow": "¡Nuevo Seguidor!",
            "subscription": "¡Nueva Suscripción!",
            "host": "¡Raid / Host!"
        }
        title = titles.get(event_type, "¡Alerta!")

        # C. Enviar la señal visual a OBS a través del Worker
        if self.alert_worker:
            self.alert_worker.send_alert(event_type, title, final_msg)
            
        # D. Retornamos el texto para que el Bot lo escriba en el chat
        return final_msg

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