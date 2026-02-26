# frontend/components/sidebar.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, 
    QFrame, QScrollArea, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QUrl
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from frontend.theme import LAYOUT, THEME_DARK, STYLES
from frontend.utils import get_icon

class SidebarButton(QPushButton):
    def __init__(self, text: str, icon_name: str, index: int, parent=None):
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

    # Estilo pre-calculado para el estado colapsado para evitar sobrecarga en bucles
    COLLAPSED_BTN_STYLE = STYLES["sidebar_btn"] + """
        QPushButton { 
            padding: 8px 0px; 
            padding-left: 0px; 
            text-align: center; 
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarContainer")
        self.setStyleSheet(STYLES["sidebar_container"])
        
        # Dimensiones y estado
        self.full_width = 220
        self.mini_width = 80
        self.is_collapsed = False
        
        # Listas de caché para elementos dinámicos
        self.buttons = []
        self.section_labels = []
        
        # Gestor de descargas de red
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_avatar_downloaded)
        
        self.setFixedWidth(self.full_width)
        
        # Layout Principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 0, 20)
        self.layout.setSpacing(LAYOUT["space_01"])
        
        # Construcción de la UI
        self._setup_header()
        self._setup_menu()
        self._setup_footer()

        # Configuración de Animación
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(self._on_animation_finished)

    def _setup_header(self):
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(*LAYOUT["level_01"])
        h_layout.setSpacing(5)

        self.lbl_title = QLabel("KickMonitor")
        self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {THEME_DARK['White_N1']}; border:none;")
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setIcon(get_icon("chevron-left-pipe.svg")) 
        self.btn_toggle.setFixedSize(32, 32)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet(STYLES["btn_icon_ghost"])
        self.btn_toggle.clicked.connect(self.toggle_sidebar)

        self.header_spacer = QWidget()
        self.header_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        h_layout.addWidget(self.lbl_title)
        h_layout.addWidget(self.header_spacer)
        h_layout.addWidget(self.btn_toggle)
        self.layout.addWidget(header_frame)

    def _setup_menu(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 8px;")
        
        self.menu_layout = QVBoxLayout(content)
        self.menu_layout.setContentsMargins(*LAYOUT["level_01"])
        self.menu_layout.setSpacing(2)

        # MAIN MENU
        self._add_section_label("MENÚ PRINCIPAL")
        self._add_btn("Inicio", "home.svg", 0)
        self._add_btn("Chat Monitor", "chat.svg", 1)
        self._add_btn("Comandos", "terminal.svg", 2)
        
        self.menu_layout.addSpacing(15)
        
        # TOOLS
        self._add_section_label("HERRAMIENTAS")
        self._add_btn("Alertas", "bell.svg", 3)
        self._add_btn("Triggers", "layers.svg", 4)
        self._add_btn("Usuarios", "users.svg", 5)
        
        self.menu_layout.addStretch()
        
        # OTHER
        self.menu_layout.addSpacing(15)
        self._add_section_label("PREFERENCIAS")
        self._add_btn("Configuración", "settings.svg", 6)

        scroll.setWidget(content)
        self.layout.addWidget(scroll)

    def _setup_footer(self):
        self.footer = QFrame()
        self.footer.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 8px;")
        
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(*LAYOUT["level_01"])
        f_layout.setSpacing(5)
        
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(32, 32)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 16px;")
        self.lbl_avatar.setPixmap(get_icon("user.svg").pixmap(56, 56))
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setScaledContents(True)

        self.lbl_user_text = QLabel("Sin Conexión")
        self.lbl_user_text.setStyleSheet("font-size: 12px; font-weight: bold; color: #ddd; border:none;")

        self.footer_spacer = QWidget()
        self.footer_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        f_layout.addWidget(self.lbl_avatar)
        f_layout.addWidget(self.lbl_user_text)
        f_layout.addWidget(self.footer_spacer)
        self.layout.addWidget(self.footer)

    # ==========================================
    # ACTUALIZACIÓN DE USUARIO Y AVATAR
    # ==========================================
    def update_user_info(self, username: str, avatar_url: str):
        self.lbl_user_text.setText(username if username and username != "Streamer" else "Sin Conexión")
        
        if avatar_url:
            req = QNetworkRequest(QUrl(avatar_url))
            self.nam.get(req)
        else:
            pix = get_icon("user.svg").pixmap(56, 56)
            self._set_circular_avatar(pix)

    def _on_avatar_downloaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pix = QPixmap()
            if pix.loadFromData(data) and not pix.isNull():
                self._set_circular_avatar(pix)
        reply.deleteLater()

    def _set_circular_avatar(self, pixmap: QPixmap):
        visual_size = 48
        scale_factor = 4
        actual_size = visual_size * scale_factor

        pixmap = pixmap.scaled(
            actual_size, actual_size, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        rounded = QPixmap(actual_size, actual_size)
        rounded.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        path = QPainterPath()
        path.addEllipse(0, 0, actual_size, actual_size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        rounded.setDevicePixelRatio(scale_factor)
        self.lbl_avatar.setPixmap(rounded)

    # ==========================================
    # UTILIDADES DE MENÚ Y ESTADO
    # ==========================================
    def _add_section_label(self, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-size: 11px; font-weight: bold; margin: 5px 0px 5px 5px;")
        self.menu_layout.addWidget(lbl)
        self.section_labels.append(lbl)

    def _add_btn(self, text: str, icon: str, index: int):
        btn = SidebarButton(text, icon, index)
        btn.clicked.connect(lambda _, b=btn: self._handle_btn_click(b))
        self.menu_layout.addWidget(btn)
        self.buttons.append(btn)

    def _handle_btn_click(self, clicked_btn: SidebarButton):
        for btn in self.buttons:
            btn.setChecked(btn == clicked_btn)
        self.page_selected.emit(clicked_btn.index)

    def set_current_index(self, index: int):
        for btn in self.buttons:
            btn.setChecked(btn.index == index)

    def toggle_sidebar(self):
        self.anim.stop()
        
        target_width = self.full_width if self.is_collapsed else self.mini_width
        
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(target_width)
        self.setMinimumWidth(self.mini_width) 
        
        # Aplicamos los cambios visuales de inmediato antes de que termine la animación
        self._apply_ui_state(collapsed=not self.is_collapsed)
        
        self.anim.start()
        self.is_collapsed = not self.is_collapsed

    def _apply_ui_state(self, collapsed: bool):
        """Gestiona la visibilidad y estilos dependiendo del estado del sidebar."""
        is_visible = not collapsed
        
        self.lbl_title.setVisible(is_visible)
        self.header_spacer.setVisible(is_visible)
        self.lbl_user_text.setVisible(is_visible)
        self.footer_spacer.setVisible(is_visible)
        
        for lbl in self.section_labels:
            lbl.setVisible(is_visible)
            
        icon_name = "menu.svg" if collapsed else "chevron-left-pipe.svg"
        self.btn_toggle.setIcon(get_icon(icon_name))
        
        for btn in self.buttons:
            btn.setText("" if collapsed else btn.text_original)
            btn.setStyleSheet(self.COLLAPSED_BTN_STYLE if collapsed else STYLES["sidebar_btn"])

    def _on_animation_finished(self):
        self.setFixedWidth(self.mini_width if self.is_collapsed else self.full_width)