# backend/services/alerts_service.py

from typing import Tuple

class AlertsService:
    """
    Servicio de Automatización de Mensajes y Alertas.
    """
    
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

    def trigger_alert(self, event_type: str, username: str, extra_data: dict = None, custom_template: str = None):
        """
        Verifica si la alerta está activa, formatea el texto y la envía a OBS.
        Si se provee custom_template, ignora la base de datos (útil para la previsualización).
        """
        extra_data = extra_data or {}
        
        # 1. Determinar si usamos la BD o la plantilla de prueba en vivo
        if custom_template is not None:
            msg_template = custom_template
            is_active = True  # Forzamos que esté activa para que se muestre en la previsualización
        else:
            msg_template, is_active = self.get_alert_config(event_type)
        
        if not is_active:
            return None # Si está apagada en la UI (y no es prueba), no hacemos nada
            
        # 2. Extraer variables de diseño (Las sacamos del dict usando .pop para que no interfieran)
        color = extra_data.pop("color", None)
        image_url = extra_data.pop("image_url", None)
            
        # 3. Formatear el mensaje (reemplazar variables de texto)
        final_msg = msg_template.replace("{user}", username)
        
        for key, value in extra_data.items():
            final_msg = final_msg.replace(f"{{{key}}}", str(value))
                
        # 4. Títulos bonitos para el Overlay de OBS
        titles = {
            "follow": "¡Nuevo Seguidor!",
            "subscription": "¡Nueva Suscripción!",
            "host": "¡Raid / Host!"
        }
        title = titles.get(event_type, "¡Alerta!")

        # 5. Enviar la señal visual a OBS a través del Worker (AHORA CON COLOR E IMAGEN)
        if self.alert_worker:
            self.alert_worker.send_alert(
                alert_type=event_type, 
                title=title, 
                message=final_msg,
                color=color,
                image_url=image_url
            )
            
        # 6. Retornamos el texto para que el Bot lo escriba en el chat
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