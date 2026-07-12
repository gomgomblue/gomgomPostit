import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QWidget, QGraphicsDropShadowEffect,
    QMessageBox
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QPoint
import storage

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = None
        self.mode = "login"
        self.drag_position = QPoint()
        self.allow_close = False # Prevents accidental closes from event loops / key propagations
        
        self.setWindowTitle("곰곰 포스트잇 - 로그인")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(340, 400)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Outer layout to support drop shadow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        
        # Central card container
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E2E8F0;
            }
        """)
        
        # Apply drop shadow to the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        outer_layout.addWidget(self.container)
        
        # Card contents layout
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Top close button
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.btn_close = QPushButton("✕", self.container)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #94A3B8;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #64748B;
            }
        """)
        self.btn_close.clicked.connect(self.close_dialog)
        header_layout.addWidget(self.btn_close)
        layout.addLayout(header_layout)
        
        # Brand Logo Title
        self.title_label = QLabel("곰곰 포스트잇", self.container)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Outfit", 20, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #1E293B; margin-bottom: 8px;")
        layout.addWidget(self.title_label)
        
        # Username Input
        self.input_username = QLineEdit(self.container)
        self.input_username.setPlaceholderText("이메일 주소 (Email Address)")
        self.input_username.setFixedHeight(42)
        self.input_username.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding-left: 12px;
                font-size: 13px;
                color: #334155;
                background-color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #F59E0B; /* Golden Amber highlight */
                background-color: white;
            }
        """)
        layout.addWidget(self.input_username)
        
        # Password Input
        self.input_password = QLineEdit(self.container)
        self.input_password.setPlaceholderText("비밀번호 (Password)")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setFixedHeight(42)
        self.input_password.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding-left: 12px;
                font-size: 13px;
                color: #334155;
                background-color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #F59E0B;
            }
        """)
        self.input_password.returnPressed.connect(self.handle_action)
        layout.addWidget(self.input_password)
        
        # Password Confirm Input (Only for signup)
        self.input_password_confirm = QLineEdit(self.container)
        self.input_password_confirm.setPlaceholderText("비밀번호 확인 (Confirm Password)")
        self.input_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password_confirm.setFixedHeight(42)
        self.input_password_confirm.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding-left: 12px;
                font-size: 13px;
                color: #334155;
                background-color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #F59E0B;
            }
        """)
        self.input_password_confirm.returnPressed.connect(self.handle_action)
        self.input_password_confirm.hide()
        layout.addWidget(self.input_password_confirm)
        
        # Auto Login Checkbox
        from PySide6.QtWidgets import QCheckBox
        self.checkbox_autologin = QCheckBox("자동 로그인", self.container)
        self.checkbox_autologin.setStyleSheet("""
            QCheckBox {
                color: #64748B;
                font-size: 12px;
                font-weight: 500;
                spacing: 6px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1.5px solid #CBD5E1;
                border-radius: 4px;
                background-color: #F8FAFC;
            }
            QCheckBox::indicator:checked {
                border-color: #F59E0B;
                background-color: #F59E0B;
                image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgZD0iTTIwIDZMOSAxN2wtNS01Ii8+PC9zdmc+");
            }
        """)
        layout.addWidget(self.checkbox_autologin)
        
        # Error feedback label
        self.label_status = QLabel("", self.container)
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.label_status)
        
        # Submit Button
        self.btn_submit = QPushButton("로그인", self.container)
        self.btn_submit.setFixedHeight(44)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #1E293B; /* Deep premium slate */
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #0F172A;
            }
        """)
        self.btn_submit.clicked.connect(self.handle_action)
        layout.addWidget(self.btn_submit)
        
        # Switch Mode / Change Password Links Row
        links_layout = QHBoxLayout()
        links_layout.setSpacing(10)
        
        self.btn_switch = QPushButton("새 계정 만들기 (회원가입)", self.container)
        self.btn_switch.setStyleSheet(self.get_link_button_style())
        self.btn_switch.clicked.connect(self.handle_switch_clicked)
        links_layout.addWidget(self.btn_switch)
        
        self.btn_reset_password = QPushButton("비밀번호 초기화", self.container)
        self.btn_reset_password.setStyleSheet(self.get_link_button_style())
        self.btn_reset_password.clicked.connect(self.handle_reset_password_clicked)
        links_layout.addWidget(self.btn_reset_password)
        
        self.btn_change_password = QPushButton("비밀번호 변경", self.container)
        self.btn_change_password.setStyleSheet(self.get_link_button_style())
        self.btn_change_password.clicked.connect(self.handle_change_password_clicked)
        links_layout.addWidget(self.btn_change_password)
        
        layout.addLayout(links_layout)
        layout.addStretch()

    def get_link_button_style(self):
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #64748B;
                font-size: 11px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #F59E0B;
            }
        """

    # Borderless window dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def handle_switch_clicked(self):
        if self.mode == "login":
            self.switch_mode("signup")
        else:
            self.switch_mode("login")

    def handle_change_password_clicked(self):
        self.switch_mode("change_password")

    def handle_reset_password_clicked(self):
        self.switch_mode("reset_password")

    def switch_mode(self, new_mode):
        self.mode = new_mode
        self.label_status.setText("")
        self.input_password.clear()
        self.input_password_confirm.clear()
        
        if self.mode == "login":
            self.input_username.show()
            self.input_password.show()
            self.input_password.setPlaceholderText("비밀번호 (Password)")
            self.input_password_confirm.hide()
            self.checkbox_autologin.show()
            self.btn_submit.setText("로그인")
            self.title_label.setText("곰곰 포스트잇")
            
            self.btn_switch.setText("새 계정 만들기 (회원가입)")
            self.btn_switch.show()
            self.btn_reset_password.show()
            self.btn_change_password.show()
            self.resize(340, 400)
            
        elif self.mode == "signup":
            self.input_username.show()
            self.input_password.show()
            self.input_password.setPlaceholderText("비밀번호 (Password)")
            self.input_password_confirm.setPlaceholderText("비밀번호 확인 (Confirm Password)")
            self.input_password_confirm.show()
            self.checkbox_autologin.hide()
            self.btn_submit.setText("회원가입 완료")
            self.title_label.setText("곰곰 회원가입")
            
            self.btn_switch.setText("로그인 화면으로 돌아가기")
            self.btn_switch.show()
            self.btn_reset_password.hide()
            self.btn_change_password.hide()
            self.resize(340, 420)
            
        elif self.mode == "change_password":
            self.input_username.show()
            self.input_password.show()
            self.input_password.setPlaceholderText("현재 비밀번호 (Current Password)")
            self.input_password_confirm.setPlaceholderText("새 비밀번호 (New Password)")
            self.input_password_confirm.show()
            self.checkbox_autologin.hide()
            self.btn_submit.setText("비밀번호 변경 완료")
            self.title_label.setText("비밀번호 변경")
            
            self.btn_switch.setText("로그인 화면으로 돌아가기")
            self.btn_switch.show()
            self.btn_reset_password.hide()
            self.btn_change_password.hide()
            self.resize(340, 450)
            
        elif self.mode == "reset_password":
            self.input_username.show()
            self.input_password.hide()
            self.input_password_confirm.hide()
            self.checkbox_autologin.hide()
            self.btn_submit.setText("임시 비밀번호 발송")
            self.title_label.setText("비밀번호 초기화")
            
            self.btn_switch.setText("로그인 화면으로 돌아가기")
            self.btn_switch.show()
            self.btn_reset_password.hide()
            self.btn_change_password.hide()
            self.resize(340, 360)

    def handle_action(self):
        username = self.input_username.text().strip()
        
        if not username:
            self.label_status.setText("이메일 주소를 입력해 주세요.")
            return
            
        # Email format validation
        import re
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", username):
            self.label_status.setText("유효한 이메일 형식으로 입력해 주세요.")
            return
            
        if self.mode == "reset_password":
            # Call reset helper using email as username
            success = storage.reset_password_with_email(username)
            if success:
                QMessageBox.information(
                    self, 
                    "비밀번호 초기화 성공", 
                    f"임시 비밀번호(6자리 숫자)가 생성되어 이메일({username})로 전송되었습니다.\n\n"
                    "※ 로컬 개발 환경인 경우 홈 디렉토리의 '~/.gomgom_email_logs.txt' 파일에서도 확인하실 수 있습니다."
                )
                self.switch_mode("login")
            else:
                QMessageBox.warning(
                    self, 
                    "초기화 실패", 
                    "가입되지 않은 이메일 주소입니다."
                )
            return

        password = self.input_password.text().strip()
        if not password:
            self.label_status.setText("비밀번호를 입력해 주세요.")
            return
            
        if self.mode == "signup":
            password_confirm = self.input_password_confirm.text().strip()
            if not password_confirm:
                self.label_status.setText("비밀번호 확인을 입력해 주세요.")
                return
            if password != password_confirm:
                QMessageBox.warning(self, "회원가입 실패", "비밀번호가 서로 일치하지 않습니다.")
                return
                
            # Handle user registration
            success = storage.register_user(username, password)
            if success:
                QMessageBox.information(self, "회원가입 성공", "회원가입이 완료되었습니다! 로그인해 주세요.")
                self.switch_mode("login")
            else:
                self.label_status.setStyleSheet("color: #EF4444; font-size: 11px;")
                self.label_status.setText("이미 존재하는 사용자 이메일입니다.")
        elif self.mode == "change_password":
            new_password = self.input_password_confirm.text().strip()
            if not new_password:
                self.label_status.setText("새 비밀번호를 입력해 주세요.")
                return
            if password == new_password:
                self.label_status.setText("현재 비밀번호와 새 비밀번호가 동일합니다.")
                return
                
            # Handle password update
            success = storage.change_password(username, password, new_password)
            if success:
                QMessageBox.information(self, "비밀번호 변경 완료", "비밀번호가 변경되었습니다! 새 비밀번호로 로그인해 주세요.")
                self.switch_mode("login")
            else:
                QMessageBox.warning(self, "변경 실패", "현재 비밀번호가 틀렸습니다.")
                self.input_password.clear()
                self.input_password_confirm.clear()
        else:
            # Handle login authentication
            success = storage.authenticate_user(username, password)
            if success:
                self.username = username
                if self.checkbox_autologin.isChecked():
                    storage.save_autologin_info(username, password)
                else:
                    storage.clear_autologin_info()
                self.accept()
            else:
                QMessageBox.warning(self, "로그인 실패", "이메일 또는 비밀번호를 확인해주세요.")
                self.input_password.clear()

    def close_dialog(self):
        self.allow_close = True
        self.reject()

    def reject(self):
        if getattr(self, "allow_close", False):
            super().reject()

    def accept(self):
        self.allow_close = True
        super().accept()

    def closeEvent(self, event):
        if getattr(self, "allow_close", False):
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            event.accept()
        else:
            super().keyPressEvent(event)
