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
        
        # Agrega esto para evitar el AttributeError
        self.DEFAULTS_TIMERS = {
            "discord": ("¡Únete a nuestro Discord! discord.gg/tu-enlace", 15),
            "redes": ("Sígueme en mis redes sociales para no perderte nada.", 20)
        }

    # =========================================================================
    # REGIÓN 1: ALERTAS DE CHAT (EVENTOS)
    # =========================================================================
    def get_alert_config(self, event_type: str) -> dict:
        """Obtiene la configuración completa de la alerta."""
        config = self.db.get_stream_alert(event_type)
        
        if not config:
            # Valores por defecto si no existe en BD
            default_msg = self.DEFAULTS_ALERTS.get(event_type, "¡Gracias {user}!")
            config = {
                "event_type": event_type, "title_template": "¡Alerta!",
                "message_template": default_msg, "is_active": False,
                "image_url": "", "sound_url": "", "color": "#53fc18",
                "duration": 5, "layout_style": "Imagen Arriba, Texto Abajo",
                "animation": "Pop In (Rebote)"
            }
            self.save_alert(event_type, config)
            
        return config

    def save_alert(self, event_type: str, data: dict) -> bool:
        """Guarda la configuración completa."""
        return self.db.set_stream_alert(event_type, data)

    def trigger_alert(self, event_type: str, username: str, extra_data: dict = None, custom_template: str = None):
        """Dispara la alerta combinando los datos de la base de datos con posibles datos de prueba."""
        extra_data = extra_data or {}
        config = self.get_alert_config(event_type)
        
        # Si estamos en previsualización (custom_template), sobrescribimos la config de la BD
        if custom_template is not None:
            config.update(extra_data)
            config["message_template"] = custom_template
            config["is_active"] = True 
        
        if not config.get("is_active"):
            return None
            
        # Formatear textos
        final_msg = config["message_template"].replace("{user}", username)
        final_title = config["title_template"].replace("{user}", username)
        
        # Enviar al worker
        if self.alert_worker:
            self.alert_worker.send_alert(
                alert_type=event_type, 
                title=final_title, 
                message=final_msg,
                color=config.get("color"),
                image_url=config.get("image_url"),
                sound_url=config.get("sound_url"),
                duration=config.get("duration", 5),
                layout_style=config.get("layout_style"),
                animation=config.get("animation")
            )
            
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