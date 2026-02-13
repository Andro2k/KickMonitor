# frontend/alerts/info_modal.py

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, 
    QTextBrowser
)
from PyQt6.QtCore import Qt
from frontend.components.base_modal import BaseModal
from frontend.theme import THEME_DARK, STYLES
from frontend.utils import get_icon, get_assets_path

class InfoModal(BaseModal):
    """
    Modal especializado para mostrar ayuda, tutoriales o documentación.
    """
    def __init__(self, parent, title: str, html_content: str):
        super().__init__(parent, width=700, height=700)
        
        # 1. HEADER (Icono + Título)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        icon = QLabel()
        icon.setPixmap(get_icon("help-circle.svg").pixmap(24, 24))
        icon.setStyleSheet("opacity: 0.8;")
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("h2")
        
        header_layout.addWidget(icon)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        
        img_path = get_assets_path("images") 
        docs_path = get_assets_path("docs") 
        self.browser.setSearchPaths([img_path.replace("\\", "/"), docs_path.replace("\\", "/")])
        search_path = img_path.replace("\\", "/")
        self.browser.setSearchPaths([search_path])
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {THEME_DARK['Black_N3']};
                color: {THEME_DARK['White_N1']};
                border: 1px solid {THEME_DARK['border']};
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
        """)
        
        full_html = f"""
        <style>
            h3 {{ color: {THEME_DARK['NeonGreen_Main']}; margin-bottom: 5px; }}
            p {{ line-height: 140%; color: #DDD; }}
            li {{ margin-bottom: 5px; }}
            strong {{ color: white; }}
        </style>
        {html_content}
        """
        self.browser.setHtml(full_html)
        
        # 3. FOOTER (Botón Cerrar)
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        btn_ok = QPushButton("Entendido")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(STYLES["btn_primary"])
        btn_ok.setFixedWidth(120)
        btn_ok.clicked.connect(self.accept)
        
        footer_layout.addWidget(btn_ok)
        
        self.body_layout.addLayout(header_layout)
        self.body_layout.addWidget(self.browser)
        self.body_layout.addLayout(footer_layout)