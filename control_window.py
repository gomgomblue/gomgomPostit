import sys
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMenu
from PySide6.QtGui import QColor, QFont, QAction, QIcon
from PySide6.QtCore import Qt, Signal, QPoint
import storage

class ControlWindow(QWidget):
    close_requested = Signal()
    new_memo_requested = Signal()
    new_todo_requested = Signal()
    dropdown_requested = Signal()
    toggle_autologin_requested = Signal(bool)  # Emits True if setting, False if clearing
    force_local_requested = Signal()
    force_server_requested = Signal()

    def __init__(self, username, is_auto_logged_in=False, parent=None):
        super().__init__(parent)
        self.username = username
        self.is_auto_logged_in = is_auto_logged_in
        self.drag_position = QPoint()
        self.init_ui()

    def init_ui(self):
        # Frameless, Always on Top, Fixed size
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(196, 42)

        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Central widget for styling
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: #1E293B; /* Premium Dark Slate */
                border: 1.5px solid #F59E0B; /* Golden Amber border */
                border-radius: 17px; /* Perfectly semi-circular ends (34px height / 2) */
            }
        """)
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(10, 0, 6, 0)
        container_layout.setSpacing(2)

        # 0. Text Title Label (곰곰메모)
        from PySide6.QtWidgets import QLabel
        self.label_title = QLabel("곰곰메모", self.container)
        title_font_size = 12 if sys.platform == "darwin" else 8
        self.label_title.setFont(QFont("Outfit", title_font_size, QFont.Weight.Bold))
        padding_top = 6 if sys.platform == "darwin" else 1
        self.label_title.setStyleSheet(f"color: #F59E0B; padding-right: 4px; padding-left: 2px; padding-top: {padding_top}px;")
        container_layout.addWidget(self.label_title)

        # 1-2. Dropdown (▾) button for listed notes (70% Larger)
        self.btn_dropdown = QPushButton("▾", self.container)
        self.btn_dropdown.setFixedSize(28, 28)
        self.btn_dropdown.setFont(QFont("Outfit", 20))
        self.btn_dropdown.setToolTip("현재 등록된 메모 목록")
        self.btn_dropdown.setStyleSheet(self.get_button_style())
        self.btn_dropdown.clicked.connect(self.dropdown_requested.emit)
        container_layout.addWidget(self.btn_dropdown)

        # 1. Plus (+) button for adding notes
        self.btn_plus = QPushButton("+", self.container)
        self.btn_plus.setFixedSize(28, 28)
        plus_font_size = 16 if sys.platform == "darwin" else 14
        self.btn_plus.setFont(QFont("Outfit", plus_font_size, QFont.Weight.Bold))
        self.btn_plus.setToolTip("메모 및 할일 추가")
        self.btn_plus.setStyleSheet(self.get_button_style())
        self.btn_plus.clicked.connect(self.show_plus_menu)
        container_layout.addWidget(self.btn_plus)

        # 2. Settings (⚙) button (40% Larger)
        self.btn_settings = QPushButton("⚙", self.container)
        self.btn_settings.setFixedSize(28, 28)
        settings_font_size = 19 if sys.platform == "darwin" else 12
        self.btn_settings.setFont(QFont("Outfit", settings_font_size))
        self.btn_settings.setToolTip("설정 메뉴")
        self.btn_settings.setStyleSheet(self.get_button_style())
        self.btn_settings.clicked.connect(self.show_settings_menu)
        container_layout.addWidget(self.btn_settings)

        # 3. Close (✕) button (30% Larger)
        self.btn_close = QPushButton("✕", self.container)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setFont(QFont("Outfit", 16, QFont.Weight.Bold))
        self.btn_close.setToolTip("프로그램 종료")
        self.btn_close.setStyleSheet(self.get_button_style(hover_color="#FF2E93", pressed_color="#D91A75"))
        self.btn_close.clicked.connect(self.close)
        container_layout.addWidget(self.btn_close)

        layout.addWidget(self.container)

    def show_plus_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.get_menu_style())
        
        action_memo = QAction("📝 새 메모 추가", menu)
        action_memo.triggered.connect(self.new_memo_requested.emit)
        menu.addAction(action_memo)
        
        action_todo = QAction("✓ 새 할일 추가", menu)
        action_todo.triggered.connect(self.new_todo_requested.emit)
        menu.addAction(action_todo)
        
        # Position menu right below the plus button
        menu.exec(self.btn_plus.mapToGlobal(QPoint(0, self.btn_plus.height() + 4)))

    def show_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.get_menu_style())
        
        if not storage.is_force_local_sqlite():
            if self.is_auto_logged_in:
                action_auto = QAction("🔓 자동 로그인 취소", menu)
                action_auto.triggered.connect(lambda: self.handle_toggle_autologin(False))
            else:
                action_auto = QAction("🔒 자동 로그인 설정", menu)
                action_auto.triggered.connect(lambda: self.handle_toggle_autologin(True))
            menu.addAction(action_auto)
        
        if storage.is_force_local_sqlite():
            action_mode = QAction("🖥 서버 버전으로 실행", menu)
            action_mode.triggered.connect(self.force_server_requested.emit)
        else:
            action_mode = QAction("💾 로컬 버전으로 실행", menu)
            action_mode.triggered.connect(self.force_local_requested.emit)
        menu.addAction(action_mode)
        
        # Position menu right below the settings button
        menu.exec(self.btn_settings.mapToGlobal(QPoint(0, self.btn_settings.height() + 4)))

    def handle_toggle_autologin(self, enable):
        self.is_auto_logged_in = enable
        self.toggle_autologin_requested.emit(enable)

    def closeEvent(self, event):
        self.close_requested.emit()
        super().closeEvent(event)

    # Frameless window dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def get_button_style(self, hover_color="#F59E0B", pressed_color="#D97706"):
        return f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: #CBD5E1; /* Light slate text */
                border-radius: 14px; /* Perfect circle for 28x28 button */
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
                color: white;
            }}
        """

    def get_menu_style(self):
        return """
            QMenu {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
                color: #334155;
                font-size: 12px;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """
