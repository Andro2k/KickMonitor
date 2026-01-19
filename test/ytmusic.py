import sys
import vlc
import yt_dlp
from ytmusicapi import YTMusic
import time

class Reproductor:
    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.current_volume = 70
        
    def obtener_url_audio(self, video_id):
        print("⌛ Extrayendo audio...")
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True, # Silenciamos advertencias
            'noplaylist': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                return info['url']
        except Exception as e:
            print(f"Error extrayendo URL: {e}")
            return None

    def reproducir(self, video_id):
        self.detener() # Aseguramos detener lo anterior
        url_stream = self.obtener_url_audio(video_id)
        if url_stream:
            media = self.instance.media_new(url_stream)
            self.player.set_media(media)
            self.player.play()
            self.player.audio_set_volume(self.current_volume)
            time.sleep(1) # Espera técnica para que cargue VLC
            return True
        return False

    def pausar(self):
        self.player.set_pause(1)

    def reanudar(self):
        self.player.set_pause(0)

    def detener(self):
        self.player.stop()

    def cambiar_volumen(self, cambio):
        self.current_volume = max(0, min(100, self.current_volume + cambio))
        self.player.audio_set_volume(self.current_volume)
        print(f"🔊 Volumen: {self.current_volume}%")

    def esta_reproduciendo(self):
        return self.player.is_playing()

class AppMusica:
    def __init__(self):
        print("🎵 Iniciando Sistema de Cola...")
        try:
            self.yt = YTMusic("headers_auth.json")
        except:
            self.yt = YTMusic()
        
        self.reproductor = Reproductor()
        
        # --- NUEVO: GESTIÓN DE COLA ---
        self.cola = []           # Lista de canciones [{'title':..., 'id':...}]
        self.indice_actual = -1  # Posición actual en la lista

    def buscar_canciones(self):
        query = input("\n🔍 Buscar canción para añadir: ")
        resultados = self.yt.search(query, filter="songs", limit=5)
        
        if not resultados:
            print("❌ Sin resultados.")
            return

        print("\nResultados encontrados:")
        for i, r in enumerate(resultados):
            print(f"{i+1}. {r['title']} - {r['artists'][0]['name']}")

        try:
            sel = int(input("\nElige # para AÑADIR A LA COLA (0 cancelar): ")) - 1
            if sel == -1: return
            
            cancion_elegida = resultados[sel]
            
            # Guardamos datos importantes en la cola
            info_cancion = {
                'videoId': cancion_elegida['videoId'],
                'title': cancion_elegida['title'],
                'artist': cancion_elegida['artists'][0]['name']
            }
            
            self.cola.append(info_cancion)
            print(f"✅ Añadido a la cola: {info_cancion['title']}")
            print(f"Total en cola: {len(self.cola)} canciones.")
            
        except ValueError:
            print("Opción inválida")

    def ver_cola(self):
        if not self.cola:
            print("\n📭 La cola está vacía.")
            return False
            
        print("\n📜 Cola de Reproducción:")
        for i, c in enumerate(self.cola):
            puntero = "▶️" if i == self.indice_actual else "  "
            print(f"{puntero} {i+1}. {c['title']} - {c['artist']}")
        return True

    def iniciar_reproductor(self):
        if not self.cola:
            print("❌ Agrega canciones primero.")
            return

        # Si no hemos empezado, empezamos por la primera
        if self.indice_actual == -1:
            self.indice_actual = 0

        self.reproducir_indice_actual()
        self.modo_control()

    def reproducir_indice_actual(self):
        if 0 <= self.indice_actual < len(self.cola):
            cancion = self.cola[self.indice_actual]
            print(f"\n▶️ Cargando {self.indice_actual + 1}/{len(self.cola)}: {cancion['title']}...")
            self.reproductor.reproducir(cancion['videoId'])
        else:
            print("Fin de la lista.")

    def modo_control(self):
        print("\n🎮 MODO REPRODUCTOR")
        print("[n] Next (Siguiente)   [b] Back (Anterior)")
        print("[p] Pausa/Play         [+] Subir Vol  [-] Bajar Vol")
        print("[v] Ver Cola           [s] Salir al menú principal")

        while True:
            # Mostramos qué suena actualmente
            if 0 <= self.indice_actual < len(self.cola):
                actual = self.cola[self.indice_actual]['title']
            else:
                actual = "Nada"
                
            comando = input(f"({actual}) >> ").lower().strip()

            if comando == 'n':
                # Lógica de NEXT
                if self.indice_actual < len(self.cola) - 1:
                    self.indice_actual += 1
                    self.reproducir_indice_actual()
                else:
                    print("🚫 Estás en la última canción.")

            elif comando == 'b':
                # Lógica de ANTERIOR
                if self.indice_actual > 0:
                    self.indice_actual -= 1
                    self.reproducir_indice_actual()
                else:
                    print("🚫 Estás en la primera canción.")

            elif comando == 'p':
                if self.reproductor.esta_reproduciendo():
                    self.reproductor.pausar()
                else:
                    self.reproductor.reanudar()

            elif comando == '+':
                self.reproductor.cambiar_volumen(10)

            elif comando == '-':
                self.reproductor.cambiar_volumen(-10)

            elif comando == 'v':
                self.ver_cola()

            elif comando == 's':
                self.reproductor.detener()
                break # Sale del bucle y vuelve al menú

    def menu(self):
        while True:
            print("\n--- 🎵 MI SPOTIFY EN PYTHON 🎵 ---")
            print("1. Buscar y Añadir a Cola")
            print("2. Ver Cola")
            print("3. ▶️ ARRANCAR REPRODUCTOR")
            print("4. Salir")
            
            op = input("Opción: ")
            
            if op == '1':
                self.buscar_canciones()
            elif op == '2':
                self.ver_cola()
            elif op == '3':
                self.iniciar_reproductor()
            elif op == '4':
                sys.exit()

if __name__ == "__main__":
    app = AppMusica()
    app.menu()