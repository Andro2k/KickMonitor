<div align="center">
  <img src="icon.png" height="180" alt="Kick Monitor Logo" />
  <h1>KickMonitor</h1>
  <p><strong>Solución integral de escritorio All-in-One para la gestión, automatización y overlays de streams en Kick.com</strong></p>

  <p>
    <a href="https://github.com/Andro2k/KickMonitor/releases/latest">
      <img src="https://img.shields.io/github/v/release/Andro2k/KickMonitor?style=for-the-badge&logo=kick&color=10BB10&labelColor=191919" alt="Latest Release" height="35"/>
    </a>
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=blue&labelColor=191919" alt="Python Version" height="35"/>
    <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=celeste&labelColor=191919" alt="PyQt6" height="35"/>
    <img src="https://img.shields.io/github/license/Andro2k/KickMonitor?style=for-the-badge&color=blue&labelColor=191919" alt="License" height="35"/>
  </p>
  <a href="https://github.com/Andro2k/KickMonitor/releases/latest">
    <img src="https://img.shields.io/badge/DESCARGA_LA_ÚLTIMA_VERSIÓN-ffffff?style=flat&color=#0FFE27" alt="Descargar Última Versión" height="64">
  </a>
</div>

---

## Descripción General

**KickMonitor** es una aplicación de escritorio diseñada para centralizar absolutamente todas las herramientas esenciales de un streamer en la plataforma Kick. Desarrollada en Python con una interfaz gráfica moderna (PyQt6) y temática oscura, esta herramienta elimina la necesidad de tener múltiples pestañas del navegador abiertas y scripts dispersos consumiendo RAM.

El sistema combina el monitoreo de tu canal en tiempo real, un bot de chat súper rápido por WebSocket, un avanzado motor de Overlays Locales para OBS Studio, y un sistema de economía con minijuegos.

<div align="center">
  <img src="screenshots/dashboard.png" alt="Vista Principal del Dashboard" width="800"/>
  <br>
  <em>(Panel principal con estadísticas en tiempo real y control de Spotify)</em>
</div>

---

## Funcionalidades Principales

### Overlays Locales para OBS (¡NUEVO!)
Servidores web internos ultraligeros que transmiten directamente a tus fuentes de navegador de OBS:
* **Chat Pro Overlay (Puerto 6001):** Chat en pantalla 100% personalizable (burbujas, transparente, neón, horizontal), con animaciones de entrada/salida y renderizado de Emotes de Kick en alta calidad.
* **Alertas Visuales (Puerto 6002):** Alertas animadas en pantalla para Nuevos Seguidores, Suscripciones y Hosts/Raids. Funciona de forma totalmente independiente para evitar latencia.
* **Sistema de Triggers:** Dispara GIFs, videos o sonidos en pantalla al canjear recompensas o ejecutar comandos en el chat.

<div align="center">
  <img src="screenshots/chat_and_alerts.png" alt="Configuración de Chat y Alertas" width="800"/>
</div>

### Chat Bot y Moderación Automática
* **Voces IA (Edge-TTS):** Text-to-Speech de altísima calidad para leer los mensajes del chat en vivo con acentos realistas. Gestión unificada en un solo panel de control.
* **Comandos Avanzados y Alias:** Crea respuestas dinámicas, asigna hasta 5 nombres (Alias) diferentes a un mismo comando y cóbrale puntos a los usuarios por utilizarlos.
* **Variables Mágicas:** Respuestas interactivas con variables en tiempo real como `{followers}`, azar como `{8ball}`, `{coin}`, `{dice}`, y tiempo `{time}`, `{date}`.
* **Filtros Inteligentes:** Píldoras de etiquetas interactivas (Dynamic Tag Pills) para ignorar comandos de bots o silenciar usuarios molestos, autocompletando guiones y prefijos.
* **Protección API:** Límite inteligente de 500 caracteres para evitar desconexiones por spam en el chat de Kick.

### Economía, Puntos y Casino
* **Sistema de Lealtad:** Otorga puntos automáticamente a los espectadores activos por cada mensaje o por tiempo de visualización.
* **Sincronización Bidireccional:** Pausar, silenciar o banear usuarios desde la tabla de base de datos se refleja inmediatamente en el motor de lectura de voz y en la pantalla de OBS.

---

## 📥 Instalación

### Para Usuarios de Windows (Recomendado)

1. Haz clic en el gran botón verde de arriba o ve a la pestaña de **[Lanzamientos (Releases)](https://github.com/Andro2k/KickMonitor/releases)**.
2. Descarga el ejecutable `KickMonitor_Setup_vX.X.X.exe`.
3. Instala la aplicación (creará un acceso directo en tu escritorio).
4. La aplicación incluye un **Actualizador Automático** inteligente, por lo que siempre tendrás las últimas novedades sin tener que volver a descargar instaladores.

### Para Desarrolladores (Código Fuente)

**Requisitos Previos:** `Python 3.12.10` y `Git`.

```bash
# 1. Clonar el repositorio
git clone [https://github.com/Andro2k/KickMonitor.git](https://github.com/Andro2k/KickMonitor.git)
cd KickMonitor
# 2. Crear y activar un entorno virtual
python -m venv venv
.\venv\Scripts\activate
# 3. Instalar dependencias
pip install -r requirements.txt
# 4. Ejecutar la aplicación
python main.py

```

## Configuración Básica

Para conectar el Bot a tu canal de Kick, ve a la pestaña **Ajustes** dentro de la app:

* **Kick OAuth:** Simplemente haz clic en "Conectar Bot" desde el Dashboard, se abrirá tu navegador para autorizar la conexión de forma segura (sin necesidad de contraseñas). El Dashboard se actualizará en tiempo real con tu avatar.
* **Spotify (Opcional):** Crea una app en *Spotify for Developers*, obtén tu Client ID y Client Secret para mostrar la música actual en tu stream.
* **OBS Studio:** Añade fuentes de navegador apuntando a `http://localhost:6001/chat` y `http://localhost:6002/alerts`. ¡Usa los botones "Copiar URL" dentro de KickMonitor para facilitar el proceso!

---

## Stack Tecnológico

* **Core & Backend:** Python 3.12.10, `asyncio`
* **Interfaz Gráfica (GUI):** PyQt6 (Ventanas modales Frameless, Draggables y animaciones por QPropertyAnimation).
* **WebSockets & Scraping:** `aiohttp`, `Pusher`, `cloudscraper`
* **Base de Datos:** SQLite con auto-mantenimiento de espacio (VACUUM) y sincronización segura con QMutexLocker.
* **Texto a Voz (TTS):** `edge-tts`, `pyttsx3`, `pygame`
* **Empaquetado:** PyInstaller y compilador Inno Setup 6

---

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulte el archivo `LICENSE` para más detalles. Siéntete libre de clonarlo, modificarlo y contribuir con Pull Requests.

<div align="center">

<sub>Desarrollado con 💚 por <strong>TheAndro2K</strong></sub>

</div>