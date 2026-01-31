### Paso 1: Vincular tu Carpeta de Medios

Lo primero es decirle a la aplicación dónde están guardados tus videos (MP4, WEBM...) y audios (MP3, WAV...).

1. Haz clic en el botón con icono de **Carpeta** (ubicado en la barra superior, a la izquierda).
2. Selecciona el directorio en tu computadora que contiene tus archivos.

Una vez hecho esto, la aplicación escaneará la carpeta y mostrará todos los archivos compatibles en una lista desplegable, como se ve en la imagen:

<img src="overlay_help01.png" width="620" alt="Selección de carpeta exitosa">

---

### Paso 2: Conexión con OBS Studio

Para que las alertas sean visibles para tu audiencia, debes conectar la aplicación con OBS.

* En la barra superior de esta app, haz clic en el icono de **ojo** para revelar la URL del servidor local (ej. `http://127.0.0.1:XXX`) y cópiala.
* En OBS Studio, agrega una nueva fuente de tipo **"Navegador" (Browser)** a tu escena.
* Pega la URL que copiaste en el campo "URL" de las propiedades de la fuente en OBS. Se recomienda configurar la resolución a **1920x1080**.

<img src="overlay_help02.png" width="625" alt="Propiedades de Fuente de Navegador en OBS">

---

### Paso 3: Configurar Alertas Individuales

Ahora, asignemos comandos a tus archivos. Haz clic en el nombre de cualquier archivo en la lista para desplegar sus opciones.

* **Comando (!):** Escribe el comando de chat que activará la alerta (ej: `!susto` o `!aplausos`). Presiona **Enter** o haz clic fuera del campo para guardar automáticamente.
* **Volumen:** Ajusta el deslizador para definir qué tan fuerte sonará esa alerta específica en el stream.
* **Botón Probar (▶):** Haz clic para simular la alerta y verificar cómo se ve y suena en OBS sin necesidad de usar el chat.

*Nota: Si intentas usar un comando que ya está asignado a otro archivo, la aplicación lo moverá automáticamente al archivo que estás editando actualmente.*

<img src="overlay_help03.png" width="400" alt="Configuración de un archivo individual">

---

### Controles Globales

* **Interruptor Principal (Switch):** Ubicado arriba a la derecha. Si lo apagas, **ninguna** alerta funcionará, incluso si escriben el comando correcto en el chat. Útil para momentos de seriedad en el stream.
* **Importar/Exportar (Pie de página):** Usa estos botones para guardar una copia de seguridad de todas tus configuraciones de comandos y volúmenes en un archivo JSON, o para cargar una configuración previa.