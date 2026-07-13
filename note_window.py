import sys
import uuid
from PySide6.QtCore import Qt, QPoint, QTimer, QEvent, QCoreApplication
from PySide6.QtGui import QFont, QCursor, QAction, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame, QSizeGrip,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox, QMenu
)

COLOR_PALETTES = {
    "yellow": {"body": "#FEF6C9", "header": "#FAE885", "text": "#333333", "hover": "#F5DC55"},
    "pink": {"body": "#FFDEE9", "header": "#FFB7CE", "text": "#333333", "hover": "#FF9DBB"},
    "green": {"body": "#D4F0D2", "header": "#A6E39E", "text": "#333333", "hover": "#8BD281"},
    "blue": {"body": "#D0E8FF", "header": "#A3D2FF", "text": "#333333", "hover": "#80BEFF"},
    "purple": {"body": "#EADEFF", "header": "#CCAAFF", "text": "#333333", "hover": "#B38BFF"}
}

class TodoItemWidget(QWidget):
    def __init__(self, text, done=False, on_toggle=None, on_delete=None):
        super().__init__()
        self.text = text
        self.done = done
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)
        
        # Checkbox for toggling done
        self.checkbox = QCheckBox(self)
        self.checkbox.setChecked(self.done)
        self.checkbox.stateChanged.connect(self.toggle_state)
        self.checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.checkbox)
        
        # Text label
        self.label = QLabel(self.text, self)
        self.label.setWordWrap(True)
        # Prevent mouse clicks on the label from blocking list clicks
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.update_font()
        layout.addWidget(self.label)
        layout.addStretch()
        
        # Small Delete button
        self.btn_delete = QPushButton("✕", self)
        self.btn_delete.setFixedSize(18, 18)
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.setStyleSheet("""
            QPushButton { 
                color: #888888; 
                background: transparent; 
                border-radius: 9px;
                font-size: 9px;
                font-weight: bold;
            } 
            QPushButton:hover { 
                color: white; 
                background: #FF5B5B; 
            }
        """)
        self.btn_delete.clicked.connect(self.delete_item)
        layout.addWidget(self.btn_delete)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child != self.btn_delete and child != self.checkbox:
                self.checkbox.setChecked(not self.checkbox.isChecked())
                event.accept()
                return
        super().mousePressEvent(event)

    def toggle_state(self, state):
        self.done = (state == Qt.CheckState.Checked.value or state == 2)
        self.update_font()
        if self.on_toggle:
            self.on_toggle()
            
    def update_font(self):
        font = self.label.font()
        font.setStrikeOut(self.done)
        self.label.setFont(font)
        if self.done:
            self.label.setStyleSheet("color: #888888;")
        else:
            self.label.setStyleSheet("color: inherit;")
            
    def delete_item(self):
        if self.on_delete:
            self.on_delete()

def to_raw_jamo(text):
    CHO_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    result = []
    for char in text:
        c = ord(char)
        if 0xAC00 <= c <= 0xD7A3:
            code = c - 0xAC00
            jong_idx = code % 28
            jung_idx = (code // 28) % 21
            cho_idx = (code // 28) // 21
            result.append(CHO_LIST[cho_idx])
            result.append(JUNG_LIST[jung_idx])
            if jong_idx > 0:
                result.append(JONG_LIST[jong_idx])
        else:
            result.append(char)
    return result

def combine_jamo_sequence(text):
    if sys.platform != "darwin":
        # Only run combining normalization on macOS where the IME splits first characters.
        return text
        
    CHO_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    
    DOUBLE_VOWELS = {
        ('ㅗ', 'ㅏ'): 'ㅘ',
        ('ㅗ', 'ㅐ'): 'ㅙ',
        ('ㅗ', 'ㅣ'): 'ㅚ',
        ('ㅜ', 'ㅓ'): 'ㅝ',
        ('ㅜ', 'ㅔ'): 'ㅞ',
        ('ㅜ', 'ㅣ'): 'ㅟ',
        ('ㅡ', 'ㅣ'): 'ㅢ'
    }
    
    DOUBLE_JONGS = {
        ('ㄱ', 'ㅅ'): 'ㄳ',
        ('ㄴ', 'ㅈ'): 'ㄵ',
        ('ㄴ', 'ㅎ'): 'ㄶ',
        ('ㄹ', 'ㄱ'): 'ㄺ',
        ('ㄹ', 'ㅁ'): 'ㄻ',
        ('ㄹ', 'ㅂ'): 'ㄼ',
        ('ㄹ', 'ㅅ'): 'ㄽ',
        ('ㄹ', 'ㅌ'): 'ㄾ',
        ('ㄹ', 'ㅍ'): 'ㄿ',
        ('ㄹ', 'ㅎ'): 'ㅀ',
        ('ㅂ', 'ㅅ'): 'ㅄ'
    }
    
    # First apply standard NFC normalization to resolve NFD split Jamo
    import unicodedata
    text = unicodedata.normalize('NFC', text)
    
    # Decompose any precomposed Hangul syllables to raw Jamo first
    # to support combining partially split input like "고" + "ㅁ" -> "곰"
    chars = to_raw_jamo(text)
    result = []
    i = 0
    n = len(chars)
    
    while i < n:
        if chars[i] in CHO_LIST:
            cho = chars[i]
            if i + 1 < n and chars[i+1] in JUNG_LIST:
                jung = chars[i+1]
                if i + 2 < n and (jung, chars[i+2]) in DOUBLE_VOWELS:
                    jung = DOUBLE_VOWELS[(jung, chars[i+2])]
                    vowel_len = 2
                else:
                    vowel_len = 1
                
                next_idx = i + 1 + vowel_len
                jong = ''
                jong_len = 0
                if next_idx < n and chars[next_idx] in JONG_LIST:
                    possible_jong = chars[next_idx]
                    jong_len = 1
                    is_followed_by_vowel = (next_idx + 1 < n and chars[next_idx + 1] in JUNG_LIST)
                    
                    if not is_followed_by_vowel:
                        if next_idx + 1 < n and (possible_jong, chars[next_idx + 1]) in DOUBLE_JONGS:
                            if not (next_idx + 2 < n and chars[next_idx + 2] in JUNG_LIST):
                                possible_jong = DOUBLE_JONGS[(possible_jong, chars[next_idx + 1])]
                                jong_len = 2
                        jong = possible_jong
                    else:
                        jong_len = 0
                
                cho_idx = CHO_LIST.index(cho)
                jung_idx = JUNG_LIST.index(jung)
                jong_idx = JONG_LIST.index(jong) if jong in JONG_LIST else 0
                
                syllable = chr(0xAC00 + (cho_idx * 21 + jung_idx) * 28 + jong_idx)
                result.append(syllable)
                i = next_idx + jong_len
            else:
                result.append(chars[i])
                i += 1
        else:
            result.append(chars[i])
            i += 1
            
    return "".join(result)

class NormalizedTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.on_text_changed)
        
    def on_text_changed(self):
        text = self.toPlainText()
        normalized = combine_jamo_sequence(text)
        if normalized != text:
            cursor = self.textCursor()
            cursor_pos = cursor.position()
            
            original_left = text[:cursor_pos]
            normalized_left = combine_jamo_sequence(original_left)
            new_cursor_pos = len(normalized_left)
            
            self.blockSignals(True)
            self.setPlainText(normalized)
            new_cursor = self.textCursor()
            new_cursor.setPosition(new_cursor_pos)
            self.setTextCursor(new_cursor)
            self.blockSignals(False)

class NormalizedLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.on_text_changed)
        
    def on_text_changed(self, text):
        normalized = combine_jamo_sequence(text)
        if normalized != text:
            cursor_pos = self.cursorPosition()
            original_left = text[:cursor_pos]
            normalized_left = combine_jamo_sequence(original_left)
            new_cursor_pos = len(normalized_left)
            
            self.blockSignals(True)
            self.setText(normalized)
            self.setCursorPosition(new_cursor_pos)
            self.blockSignals(False)

class NoteWindow(QWidget):
    def __init__(self, note_id=None, note_type="memo", content="", todo_items=None, x=100, y=100, width=300, height=300, color="yellow", always_on_top=False, on_save_callback=None, on_close_callback=None, on_new_callback=None, on_refresh_callback=None, is_important=False):
        super().__init__()
        
        self.note_id = note_id if note_id else str(uuid.uuid4())
        self.note_type = note_type if note_type in ["memo", "todo"] else "memo"
        self.initial_content = content
        self.initial_todo_items = todo_items if todo_items else []
        self.current_color_name = color if color in COLOR_PALETTES else "yellow"
        self.always_on_top = always_on_top
        self.is_important = is_important
        self.on_save_callback = on_save_callback
        self.on_close_callback = on_close_callback
        self.on_new_callback = on_new_callback
        self.on_refresh_callback = on_refresh_callback
        
        # Debounce timer for saving to avoid breaking macOS IME (Korean)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(500)  # Wait 500ms after last keystroke
        self.save_timer.timeout.connect(self.perform_save)
        
        self.drag_position = QPoint()
        
        # Configure window: frameless and translucent
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Ensure the note window is visible on one of the connected screens
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QRect
        screens = QGuiApplication.screens()
        on_screen = False
        
        for screen in screens:
            geom = screen.availableGeometry()
            note_rect = QRect(x, y, width, height)
            if geom.intersects(note_rect):
                # Adjust y if title bar goes beyond the top screen limit
                if y < geom.y():
                    y = geom.y()
                # Adjust y if title bar goes beyond the bottom screen limit
                if y > geom.y() + geom.height() - 40:
                    y = geom.y() + geom.height() - 200
                # Adjust x if the note goes too far left
                if x + width < geom.x() + 50:
                    x = geom.x()
                # Adjust x if the note goes too far right
                if x > geom.x() + geom.width() - 50:
                    x = geom.x() + geom.width() - 200
                on_screen = True
                break
                
        # If the note is completely off-screen, center it on the primary screen
        if not on_screen and screens:
            primary = QGuiApplication.primaryScreen()
            if primary:
                p_geom = primary.availableGeometry()
                x = p_geom.x() + (p_geom.width() - width) // 2
                y = p_geom.y() + (p_geom.height() - height) // 2

        self.setGeometry(x, y, width, height)
        self.setMinimumSize(220, 180)
        
        self.setup_ui()
        
        # Populate initial content depending on type
        if self.note_type == "memo":
            self.text_edit.setPlainText(self.initial_content)
            self.text_edit.textChanged.connect(self.trigger_save)
        elif self.note_type == "todo":
            for item in self.initial_todo_items:
                self.add_todo_item_to_widget(item.get("text", ""), item.get("done", False))
        
        # Update flags and styles
        self.update_always_on_top(init=True)
        self.apply_theme()
        
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Show the window
        self.show()
        self.raise_()
        
        # Delay activation and focus slightly (300ms) to ensure macOS AppKit maps the native window
        # and binds the IME composition context before the first keystroke is processed.
        def set_initial_focus():
            self.activateWindow()
            target_widget = self.text_edit if self.note_type == "memo" else self.todo_input
            target_widget.setFocus()
            
            # On macOS, simulate typing "곰" (ㄱ, ㅗ, ㅁ) and then Backspace it.
            # This programmatically initializes the macOS IME composition engine for this text field
            # so that when the user performs their first manual keystroke, the IME is already warm and active.
            if sys.platform == "darwin":
                try:
                    # Space Press & Release to ensure widget registers input session
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " "))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " "))
                    
                    # 'ㄱ' Press & Release
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, "ㄱ"))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, "ㄱ"))
                    # 'ㅗ' Press & Release
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, "ㅗ"))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, "ㅗ"))
                    # 'ㅁ' Press & Release
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, "ㅁ"))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, "ㅁ"))
                    
                    # Backspace 4 times to clean up Space + 'ㄱ', 'ㅗ', 'ㅁ'
                    for _ in range(4):
                        QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
                        QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
                except Exception:
                    pass
                
        QTimer.singleShot(300, set_initial_focus)
        
        # Listen to global input method locale changes to warm up the IME on language switches (e.g. English -> Korean)
        if sys.platform == "darwin":
            try:
                from PySide6.QtGui import QGuiApplication
                QGuiApplication.inputMethod().localeChanged.connect(self.handle_locale_changed)
            except Exception:
                pass

    def setup_ui(self):
        # Root layout (handles padding for dropshadow or margins)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(5, 5, 5, 5)
        
        # Main container QFrame (provides rounded corners and borders)
        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root_layout.addWidget(self.container)
        
        # Inner layout of container
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title bar (custom header)
        self.title_bar = QFrame(self.container)
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(34)
        self.title_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        title_layout.setSpacing(4)
        
        # Left side buttons: New Note dropdown trigger, Pin, Color
        self.btn_new = QPushButton("＋", self.title_bar)
        self.btn_new.setFixedSize(26, 26)
        self.btn_new.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_new.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_new.clicked.connect(self.show_new_menu)
        title_layout.addWidget(self.btn_new)
        
        self.btn_pin = QPushButton("📌", self.title_bar)
        self.btn_pin.setFixedSize(26, 26)
        self.btn_pin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_pin.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_pin.clicked.connect(self.toggle_pin)
        title_layout.addWidget(self.btn_pin)
        
        self.btn_star = QPushButton("☆", self.title_bar)
        self.btn_star.setFixedSize(26, 26)
        self.btn_star.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_star.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_star.clicked.connect(self.toggle_important)
        title_layout.addWidget(self.btn_star)
        
        self.btn_color = QPushButton("🎨", self.title_bar)
        self.btn_color.setFixedSize(26, 26)
        self.btn_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_color.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_color.clicked.connect(self.cycle_color)
        title_layout.addWidget(self.btn_color)
        
        self.btn_refresh = QPushButton("⟳", self.title_bar)
        self.btn_refresh.setFixedSize(26, 26)
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_refresh.clicked.connect(self.trigger_refresh)
        title_layout.addWidget(self.btn_refresh)
        
        # Spacer
        title_layout.addStretch()
        
        # Right side button: Close
        self.btn_close = QPushButton("✕", self.title_bar)
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.clicked.connect(self.close_note)
        title_layout.addWidget(self.btn_close)
        
        layout.addWidget(self.title_bar)
        
        # Content panel based on note_type
        if self.note_type == "memo":
            self.text_edit = NormalizedTextEdit(self.container)
            self.text_edit.setFrameStyle(QFrame.Shape.NoFrame)
            self.text_edit.setAcceptRichText(False)
            font = QFont("Segoe UI" if sys.platform == "win32" else "Helvetica", 11)
            self.text_edit.setFont(font)
            layout.addWidget(self.text_edit)
        elif self.note_type == "todo":
            todo_container = QWidget(self.container)
            todo_layout = QVBoxLayout(todo_container)
            todo_layout.setContentsMargins(0, 0, 0, 0)
            todo_layout.setSpacing(4)
            
            # Text input for adding todo items
            self.todo_input = NormalizedLineEdit(todo_container)
            self.todo_input.setPlaceholderText("할 일 추가... (Enter)")
            self.todo_input.setFrame(False)
            self.todo_input.setFixedHeight(30)
            self.todo_input.returnPressed.connect(self.handle_add_todo)
            font = QFont("Segoe UI" if sys.platform == "win32" else "Helvetica", 11)
            self.todo_input.setFont(font)
            todo_layout.addWidget(self.todo_input)
            
            # List box containing items
            self.list_widget = QListWidget(todo_container)
            self.list_widget.setFrameStyle(QFrame.Shape.NoFrame)
            self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
            self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            todo_layout.addWidget(self.list_widget)
            
            layout.addWidget(todo_container)
        
        # Bottom layout for resizing (places the size grip in the bottom-right corner)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        bottom_bar.addStretch()
        
        # Native Qt Size Grip for resizing frameless windows
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setFixedSize(14, 14)
        bottom_bar.addWidget(self.sizegrip)
        
        layout.addLayout(bottom_bar)

    def apply_theme(self):
        palette = COLOR_PALETTES[self.current_color_name]
        
        # QSS stylesheet for rounded corners, scrollbars, and button hover states
        qss = f"""
            QFrame#container {{
                background-color: {palette["body"]};
                border: 1px solid {palette["header"]};
                border-radius: 12px;
            }}
            QFrame#title_bar {{
                background-color: {palette["header"]};
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {palette["text"]};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {palette["hover"]};
            }}
            QPushButton#btn_close:hover {{
                background-color: #FF5B5B;
                color: white;
            }}
            QTextEdit, QListWidget {{
                background-color: transparent;
                color: {palette["text"]};
                border: none;
            }}
            QTextEdit {{
                padding: 10px;
                line-height: 1.4;
            }}
            QLineEdit {{
                background-color: rgba(0, 0, 0, 0.03);
                border: none;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                color: {palette["text"]};
                padding-left: 10px;
                padding-right: 10px;
            }}
            QLineEdit:focus {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
            QListWidget {{
                padding-top: 4px;
            }}
            QListWidget::item {{
                background: transparent;
                border-bottom: 1px dashed rgba(0, 0, 0, 0.05);
            }}
            QListWidget::item:selected {{
                background: transparent;
                color: {palette["text"]};
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 0, 0, 0.15);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0, 0, 0, 0.3);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """
        self.setStyleSheet(qss)
        self.update_pin_button_style()
        self.update_star_button_style()

    def show_new_menu(self):
        # Create dropdown QMenu for type selection
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
                color: #333333;
            }}
            QMenu::item:selected {{
                background-color: #E6E6E6;
                color: black;
            }}
        """)
        
        action_memo = QAction("일반 메모 추가", menu)
        action_memo.triggered.connect(lambda: self.on_new_click("memo"))
        menu.addAction(action_memo)
        
        action_todo = QAction("할 일 목록 추가", menu)
        action_todo.triggered.connect(lambda: self.on_new_click("todo"))
        menu.addAction(action_todo)
        
        # Popup exactly below the '+' button
        btn_pos = self.btn_new.mapToGlobal(QPoint(0, self.btn_new.height()))
        menu.exec(btn_pos)

    def cycle_color(self):
        color_keys = list(COLOR_PALETTES.keys())
        idx = color_keys.index(self.current_color_name)
        self.current_color_name = color_keys[(idx + 1) % len(color_keys)]
        self.apply_theme()
        self.trigger_save_immediately()

    def toggle_pin(self):
        self.always_on_top = not self.always_on_top
        self.update_always_on_top()
        self.trigger_save_immediately()

    def trigger_refresh(self):
        if self.on_refresh_callback:
            self.on_refresh_callback()

    def update_always_on_top(self, init=False):
        flags = self.windowFlags()
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        if not init:
            self.show()
        self.update_pin_button_style()

    def update_pin_button_style(self):
        palette = COLOR_PALETTES[self.current_color_name]
        if self.always_on_top:
            self.btn_pin.setStyleSheet(f"background-color: {palette['hover']}; border: 1px solid rgba(0, 0, 0, 0.1);")
        else:
            self.btn_pin.setStyleSheet("background-color: transparent; border: none;")

    def toggle_important(self):
        self.is_important = not self.is_important
        self.update_star_button_style()
        self.trigger_save_immediately()

    def update_star_button_style(self):
        palette = COLOR_PALETTES[self.current_color_name]
        if self.is_important:
            self.btn_star.setText("★")
            self.btn_star.setStyleSheet(f"color: #F59E0B; font-size: 15px; font-weight: bold; background-color: {palette['hover']}; border: 1px solid rgba(0, 0, 0, 0.1);")
        else:
            self.btn_star.setText("☆")
            self.btn_star.setStyleSheet("color: #64748B; font-size: 15px; background-color: transparent; border: none;")

    # Todo list item interaction
    def handle_add_todo(self):
        text = self.todo_input.text().strip()
        if text:
            self.add_todo_item_to_widget(text, False)
            self.todo_input.clear()
            self.trigger_save_immediately()

    def add_todo_item_to_widget(self, text, done=False):
        item = QListWidgetItem(self.list_widget)
        # Create a custom widget wrapper
        widget = TodoItemWidget(
            text=text, 
            done=done, 
            on_toggle=self.trigger_save_immediately,
            on_delete=lambda: self.delete_todo_item(item)
        )
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def delete_todo_item(self, item):
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self.trigger_save_immediately()

    def get_todo_items_data(self):
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, TodoItemWidget):
                items.append({"text": widget.text, "done": widget.done})
        return items

    # Frameless window dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            self.trigger_save_immediately()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()

    # Track resize events to save window dimensions
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.trigger_save_immediately()

    def handle_locale_changed(self):
        # When language switches, programmatically warm up the active input widget 
        # to prevent first-character split in the newly selected language.
        target_widget = self.text_edit if self.note_type == "memo" else self.todo_input
        if target_widget.hasFocus():
            def warm_up():
                try:
                    # Space Press & Release
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " "))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " "))
                    # Backspace Press & Release
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
                    QCoreApplication.postEvent(target_widget, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier))
                except Exception:
                    pass
            # 150ms delay to let the operating system finish input method swap
            QTimer.singleShot(150, warm_up)

    # Callbacks and hooks
    def trigger_save(self):
        # Starts the 1000ms delay timer (debounces key presses to avoid macOS IME separation bugs)
        self.save_timer.start()

    def trigger_save_immediately(self):
        self.save_timer.stop()
        self.perform_save()

    def perform_save(self):
        if self.on_save_callback:
            self.on_save_callback(self)

    def on_new_click(self, note_type="memo"):
        if self.on_new_callback:
            # Propagate selected type to callback
            self.on_new_callback(self, note_type)

    def close_note(self):
        if self.is_important:
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("경고")
            msg.setText("중요 설정(★)된 메시지는 삭제할 수 없습니다.")
            msg.addButton("확인", QMessageBox.ButtonRole.AcceptRole)
            msg.exec()
            return
            
        # Save immediately before closing
        self.trigger_save_immediately()
        if self.on_close_callback:
            self.on_close_callback(self)
        self.close()

    def get_data(self):
        """Returns serializable data for this note."""
        data = {
            "id": self.note_id,
            "type": self.note_type,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "color": self.current_color_name,
            "always_on_top": self.always_on_top,
            "is_important": self.is_important
        }
        if self.note_type == "memo":
            data["content"] = self.text_edit.toPlainText()
        elif self.note_type == "todo":
            data["todo_items"] = self.get_todo_items_data()
        return data
