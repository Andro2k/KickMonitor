# frontend/help_content.py

import os
import markdown
from frontend.utils import resource_path

def load_help_content(topic: str) -> str:
    # Asumiendo que guardas los .md en assets/docs/
    file_path = resource_path(os.path.join("assets", "docs", f"{topic}.md"))
    
    if not os.path.exists(file_path):
        return f"<h3>Error</h3><p>No se encontró la ayuda para: {topic}</p>"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            md_text = f.read()
            
        # Convertir Markdown a HTML
        html_content = markdown.markdown(md_text)
        
        # Aquí puedes retornar solo el HTML, el estilo ya lo inyectas en InfoModal
        return html_content
    except Exception as e:
        return f"<h3>Error</h3><p>No se pudo cargar el archivo: {str(e)}</p>"