# backend/core/kick/auth_manager.py

import os
import json
import base64
import hashlib
import urllib.parse
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from backend.utils.logger_text import LoggerText
from backend.services.oauth_service import OAuthService
from backend.utils.paths import get_config_path

class KickAuthManager:
    def __init__(self, config, http_session, log_callback):
        self.config = config
        self.session = http_session
        self.log = log_callback
        self.access_token = None
        
        config_dir = get_config_path()
        self.session_file = os.path.join(config_dir, "session.json")

    def _generate_pkce(self):
        verifier_bytes = os.urandom(32)
        verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b'=').decode('utf-8')
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
        return verifier, challenge

    async def ensure_authentication(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    if data.get("access_token"):
                        self.access_token = data["access_token"]
                        self.log(LoggerText.success("Token de acceso restaurado."))
                        return True
            except Exception as e:
                self.log(LoggerText.warning(f"Sesión corrupta: {e}"))
        
        return await self.perform_oauth_login()

    async def perform_oauth_login(self):
        self.log(LoggerText.system("Iniciando Login OAuth (Abre tu navegador)."))
        verifier, challenge = self._generate_pkce()
        state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('utf-8')
        scopes = ["user:read", "channel:read", "channel:write", "chat:write", "events:subscribe", "channel:rewards:read", "channel:rewards:write"]
        
        params = {
            "client_id": self.config.get('client_id'), 
            "code_challenge": challenge, 
            "code_challenge_method": "S256",
            "redirect_uri": self.config.get('redirect_uri'), 
            "response_type": "code", 
            "scope": " ".join(scopes), 
            "state": state
        }
        
        auth_url = f"https://id.kick.com/oauth/authorize?{urllib.parse.urlencode(params)}"
        
        try:
            oauth_service = OAuthService(port=8080)
            QDesktopServices.openUrl(QUrl(auth_url))
            code = await oauth_service.wait_for_code(timeout=60)
            
            if not code: 
                self.log(LoggerText.error("Login cancelado o tiempo de espera agotado."))
                return False
            
            token_url = "https://id.kick.com/oauth/token"
            payload = {
                "grant_type": "authorization_code", 
                "client_id": self.config.get("client_id"), 
                "client_secret": self.config.get("client_secret"),
                "code": code, 
                "redirect_uri": self.config.get("redirect_uri"), 
                "code_verifier": verifier
            }
            
            async with self.session.post(token_url, data=payload) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self._save_session(token_data)
                    self.access_token = token_data.get("access_token")
                    return True
                else:
                    self.log(LoggerText.error(f"Error obteniendo token: {await resp.text()}"))
                    return False
        except Exception as e:
            self.log(LoggerText.error(f"Excepción durante Login: {e}"))
            return False

    async def refresh_token_silently(self):
        if not os.path.exists(self.session_file): return False
        try:
            with open(self.session_file, 'r') as f: 
                refresh_token = json.load(f).get("refresh_token")
            if not refresh_token: return False

            payload = {
                "grant_type": "refresh_token",
                "client_id": self.config.get("client_id"),
                "client_secret": self.config.get("client_secret"),
                "refresh_token": refresh_token
            }
            async with self.session.post("https://id.kick.com/oauth/token", data=payload) as resp:
                if resp.status == 200:
                    new_data = await resp.json()
                    new_data["refresh_token"] = new_data.get("refresh_token", refresh_token)
                    self._save_session(new_data)
                    self.access_token = new_data.get("access_token")
                    self.log(LoggerText.debug("Token renovado automáticamente."))
                    return True
        except Exception as e:
            self.log(LoggerText.debug(f"Error renovando token: {e}"))
        return False

    def _save_session(self, data):
        with open(self.session_file, 'w') as f: 
            json.dump(data, f, indent=4)