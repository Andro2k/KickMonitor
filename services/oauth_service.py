# services/oauth_service.py

import asyncio
from typing import Optional
from aiohttp import web

class OAuthService:
    """
    Servicio de autenticación OAuth2 local (usando aiohttp).
    Levanta un servidor temporal para capturar el 'code' de redirección.
    """
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server: Optional[web.TCPSite] = None
        self.runner: Optional[web.AppRunner] = None
        self.auth_future: Optional[asyncio.Future] = None

    # =========================================================================
    # REGIÓN 1: API PÚBLICA
    # =========================================================================
    async def wait_for_code(self, timeout: int = 60) -> Optional[str]:
        """
        Ciclo completo: Inicia servidor -> Espera código -> Apaga servidor.
        Retorna el 'code' o None si expira el tiempo.
        """
        self.auth_future = asyncio.Future()
        
        # 1. Iniciar Servidor
        await self._start_server()
        
        try:
            # 2. Esperar código (bloqueante hasta timeout)
            code = await asyncio.wait_for(self.auth_future, timeout=timeout)
            return code
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"[OAuth] Error esperando código: {e}")
            return None
        finally:
            # 3. Limpieza garantizada
            await self._stop_server()

    # =========================================================================
    # REGIÓN 2: SERVIDOR INTERNO (AIOHTTP)
    # =========================================================================
    async def _start_server(self):
        app = web.Application()
        app.router.add_get('/callback', self._oauth_callback)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        # reuse_address=True permite reiniciar el proceso rápidamente sin error de puerto ocupado
        self.server = web.TCPSite(self.runner, '127.0.0.1', self.port, reuse_address=True)
        await self.server.start()

    async def _stop_server(self):
        if self.server:
            await self.server.stop()
        if self.runner:
            await self.runner.cleanup()

    async def _oauth_callback(self, request):
        """Manejador de la ruta /callback."""
        code = request.query.get('code')
        
        # Si aún estamos esperando una respuesta...
        if self.auth_future and not self.auth_future.done():
            if code:
                self.auth_future.set_result(code)
                return web.Response(text=OAuthTemplates.SUCCESS, content_type='text/html')
            else:
                self.auth_future.set_result(None)
                return web.Response(text=OAuthTemplates.FAIL, content_type='text/html')
        
        return web.Response(text="El proceso de login ya finalizó.", content_type='text/plain')


# =========================================================================
# REGIÓN 3: PLANTILLAS HTML ESTÁTICAS
# =========================================================================
class OAuthTemplates:
    # Estilos compartidos (Este string NO es f-string, así que usa llaves simples)
    _CSS_BASE = """
        body { background-color: #0b0e0f; color: #ffffff; font-family: "Google Sans", sans-serif;
               display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1a1d1e; padding: 40px; border-radius: 16px; border: 1px solid #333;
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); max-width: 400px; width: 90%;
                animation: fadeIn 0.5s ease-out; }
        .btn { border: none; padding: 12px 24px; border-radius: 6px; font-weight: bold;
               font-size: 14px; cursor: pointer; transition: transform 0.2s; text-transform: uppercase; }
        .btn:hover { transform: translateY(-2px); }
        .timer { font-size: 11px; color: #555; margin-top: 20px; }
        @keyframes fadeIn { from { opacity: 0; transform: -20px; } to { opacity: 1; transform: 0; } }
    """

    # Estos SÍ son f-strings, por lo que el CSS interno debe llevar doble llave {{ }}
    SUCCESS = f"""
    <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Éxito</title>
    <style>
        {_CSS_BASE}
        .icon {{ color: #53fc18; margin-bottom: 20px; filter: drop-shadow(0 0 10px rgba(83, 252, 24, 0.4)); }}
        h1 {{ color: #53fc18; margin: 10px 0; }}
        .btn {{ background-color: #53fc18; color: #000; }}
        .btn:hover {{ box-shadow: 0 5px 15px rgba(83, 252, 24, 0.3); }}
    </style></head>
    <body>
        <div class="card">
            <div class="icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 3a1 1 0 0 1 1 1v3h1v-1a1 1 0 0 1 .883-.993l.117-.007h1v-1a1 1 0 0 1 .883-.993l.117-.007h6a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-1v1a1 1 0 0 1-.883.993l-.117.007h-1v2h1a1 1 0 0 1 .993.883l.007.117v1h1a1 1 0 0 1 .993.883l.007.117v4a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-1h-1a1 1 0 0 1-.993-.883l-.007-.117v-1h-1v3a1 1 0 0 1-.883.993l-.117.007h-5a1 1 0 0 1-1-1v-16a1 1 0 0 1 1-1z" />
                </svg>
            </div>
            <h1>¡Conectado!</h1>
            <p style="color:#a0a0a0">Autenticación exitosa. Puedes cerrar esta ventana.</p>
            <button class="btn" onclick="window.close()">Cerrar</button>
            <div class="timer">Cerrando en breve...</div>
        </div>
        <script>setTimeout(function(){{window.close()}}, 3000);</script>
    </body></html>
    """

    FAIL = f"""
    <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Error</title>
    <style>
        {_CSS_BASE}
        .icon {{ color: #ff453a; margin-bottom: 20px; }}
        h1 {{ color: #ff453a; margin: 10px 0; }}
        .btn {{ background-color: #2c2f30; color: #fff; border: 1px solid #ff453a; }}
        .btn:hover {{ background-color: #ff453a; box-shadow: 0 5px 15px rgba(255, 69, 58, 0.2); }}
    </style></head>
    <body>
        <div class="card">
            <div class="icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10-10-4.477-10-10 4.477-10 10-10zm0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm-1 5h2v6h-2zm0 8h2v2h-2z" />
                </svg>
            </div>
            <h1>Cancelado</h1>
            <p style="color:#a0a0a0">No se pudo verificar la cuenta.</p>
            <button class="btn" onclick="window.close()">Cerrar</button>
        </div>
    </body></html>
    """