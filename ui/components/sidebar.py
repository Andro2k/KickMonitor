# ui/components/sidebar.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, 
    QFrame, QScrollArea, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from ui.theme import THEME_DARK, STYLES
from ui.utils import get_icon

class SidebarButton(QPushButton):
    def __init__(self, text, icon_name, index, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.text_original = text
        self.setIcon(get_icon(icon_name))
        self.setIconSize(QSize(20, 20))
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(STYLES["sidebar_btn"])

class Sidebar(QFrame):
    page_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarContainer")
        self.setStyleSheet(STYLES["sidebar_container"])
        
        # Dimensiones
        self.full_width = 184
        self.mini_width = 64
        self.is_collapsed = False
        self.buttons = []
        
        # INICIO: Fijamos el ancho inicial
        self.setFixedWidth(self.full_width)
        
        # Layout Principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Partes del Sidebar
        self._setup_header()
        self._setup_menu()
        self._setup_footer()

        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim.finished.connect(self._on_animation_finished)

    def _setup_header(self):
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_frame.setStyleSheet("background: transparent; border: none;")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(15, 10, 15, 10)
        h_layout.setSpacing(5)

        self.lbl_title = QLabel("Kick Monitor")
        self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {THEME_DARK['White_N1']}; border:none;")
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setIcon(get_icon("chevron-left.svg")) 
        self.btn_toggle.setFixedSize(32, 32)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("QPushButton { border: none; background: transparent; border-radius: 4px; } QPushButton:hover { background: #333; }")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)

        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_toggle)
        self.layout.addWidget(header_frame)

    def _setup_menu(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # Opcional: Reducir un poco los márgenes laterales para que los iconos no queden apretados en modo mini
        self.menu_layout = QVBoxLayout(content)
        self.menu_layout.setContentsMargins(5,5,5,5)
        self.menu_layout.setSpacing(0)

        # MAIN MENU
        self._add_section_label("MAIN MENU")
        self._add_btn("Inicio", "home.svg", 0)
        self._add_btn("Chat Monitor", "chat.svg", 1)
        self._add_btn("Comandos", "terminal.svg", 2)
        
        self.menu_layout.addSpacing(10)
        
        # TOOLS
        self._add_section_label("TOOLS")
        self._add_btn("Alertas", "bell.svg", 3)
        self._add_btn("Overlay", "layers.svg", 4)
        self._add_btn("Puntos", "users.svg", 5)
        self._add_btn("Casino", "casino.svg", 6)
        
        self.menu_layout.addStretch()
        
        # OTHER
        self._add_section_label("OTHER")
        self._add_btn("Configuración", "settings.svg", 7)

        scroll.setWidget(content)
        self.layout.addWidget(scroll)

    def _setup_footer(self):
        self.footer = QFrame()
        self.footer.setFixedHeight(70)
        self.footer.setStyleSheet(f"border: none; border-top: 1px solid {THEME_DARK['Black_N2']}; background: transparent;")
        
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(15, 10, 15, 10)
        f_layout.setSpacing(15)
        
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(32, 32)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 16px;")
        
        # Icono fallback
        self.lbl_avatar.setPixmap(get_icon("user.svg").pixmap(16, 16))
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_user_text = QLabel("Usuario\nConectado")
        self.lbl_user_text.setStyleSheet("font-size: 12px; color: #aaa; line-height: 120%; border:none;")

        f_layout.addWidget(self.lbl_avatar)
        f_layout.addWidget(self.lbl_user_text)
        f_layout.addStretch()
        self.layout.addWidget(self.footer)

    def _add_section_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("SectionLabel")
        lbl.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-size: 11px; font-weight: bold; margin-left: 10px; margin-top: 5px;")
        self.menu_layout.addWidget(lbl)

    def _add_btn(self, text, icon, index):
        btn = SidebarButton(text, icon, index)
        btn.clicked.connect(lambda: self._handle_btn_click(btn))
        self.menu_layout.addWidget(btn)
        self.buttons.append(btn)

    def _handle_btn_click(self, clicked_btn):
        for btn in self.buttons:
            btn.setChecked(btn == clicked_btn)
        self.page_selected.emit(clicked_btn.index)

    def set_current_index(self, index):
        for btn in self.buttons:
            btn.setChecked(btn.index == index)

    # ==========================================
    # LÓGICA DE COLAPSO / EXPANSIÓN
    # ==========================================
    def toggle_sidebar(self):
        self.anim.stop()
        
        if self.is_collapsed:
            # --- EXPANDIR ---
            # 1. Configuramos el valor final
            self.anim.setStartValue(self.width())
            self.anim.setEndValue(self.full_width)
            
            # 2. Restauramos contenido ANTES de animar (opcional, o durante)
            self.lbl_title.show()
            self.lbl_user_text.show()
            self.lbl_avatar.show()
            self.btn_toggle.setIcon(get_icon("chevron-left.svg"))
            
            # Restaurar textos botones
            for btn in self.buttons:
                btn.setText(btn.text_original)
                btn.setStyleSheet(STYLES["sidebar_btn"]) # Reset alineación izquierda
                
            # Restaurar etiquetas secciones
            for child in self.findChildren(QLabel, "SectionLabel"):
                child.show()

        else:
            # --- COLAPSAR ---
            # 1. Configuramos el valor final
            self.anim.setStartValue(self.width())
            self.anim.setEndValue(self.mini_width)
            
            self.lbl_title.hide()
            self.lbl_user_text.hide()
            self.btn_toggle.setIcon(get_icon("menu.svg"))
            
            # Ocultar texto botones y centrar iconos
            for btn in self.buttons:
                btn.setText("")
                btn.setStyleSheet(STYLES["sidebar_btn"] + """
                    QPushButton { padding: 6px; text-align: center; }
                """)

            for child in self.findChildren(QLabel, "SectionLabel"):
                child.hide()

        self.setMinimumWidth(self.mini_width) 
        self.anim.start()

        self.is_collapsed = not self.is_collapsed

    def _on_animation_finished(self):
        # Al terminar, fijamos el tamaño para que el layout no haga cosas raras
        if self.is_collapsed:
            self.setFixedWidth(self.mini_width)
        else:
            self.setFixedWidth(self.full_width)