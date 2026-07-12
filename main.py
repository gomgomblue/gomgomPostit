import os
import sys
from PySide6.QtWidgets import QApplication, QDialog
import storage
from note_window import NoteWindow
from control_window import ControlWindow

def transform_macos_process_to_foreground():
    if sys.platform != "darwin":
        return
    try:
        import ctypes
        # Load ApplicationServices containing GetCurrentProcess and TransformProcessType
        lib = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        
        class ProcessSerialNumber(ctypes.Structure):
            _fields_ = [("highLongOfPSN", ctypes.c_uint32),
                        ("lowLongOfPSN", ctypes.c_uint32)]
                        
        psn = ProcessSerialNumber()
        if lib.GetCurrentProcess(ctypes.byref(psn)) == 0:
            # Transform background command-line process to Foreground GUI Application
            lib.TransformProcessType(ctypes.byref(psn), 1)
    except Exception as e:
        print(f"Failed to transform macOS process: {e}")

from PySide6.QtCore import QTimer

class GomgomPostitApp:
    def __init__(self):
        # On macOS, transform process type and force frontmost application state.
        # This resolves the 'error messaging the mach port for IMKCFRunLoopWakeUpReliable'
        # which causes the Korean IME to fail on initial keystrokes in command-line launched Qt apps.
        if sys.platform == "darwin":
            transform_macos_process_to_foreground()
            try:
                os.system(f"osascript -e 'tell application \"System Events\" to set frontmost of every process whose unix id is {os.getpid()} to true' &")
            except Exception:
                pass

        # Initialize QApplication
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Configure version mode (Local SQLite vs Server MariaDB)
        version_mode = storage.load_version_mode()
        logged_in = False
        
        if version_mode == "local":
            storage.set_force_local_sqlite(True)
            self.username = "local_user"
            self.password = ""
        else:
            storage.set_force_local_sqlite(False)
            # Attempt Auto Login first
            autologin_data = storage.load_autologin_info()
            if autologin_data:
                auto_user = autologin_data.get("username")
                auto_pass = autologin_data.get("password")
                if storage.authenticate_user(auto_user, auto_pass):
                    self.username = auto_user
                    self.password = auto_pass
                    logged_in = True
                else:
                    # Clear invalid credentials
                    storage.clear_autologin_info()
                    
            if not logged_in:
                # Show Login Dialog
                from login_dialog import LoginDialog
                login = LoginDialog()
                try:
                    res = login.exec()
                    if res == QDialog.Accepted:
                        self.username = login.username
                        self.password = login.input_password.text().strip()
                    else:
                        sys.exit(0)
                except Exception as e:
                    sys.exit(1)
                
        import uuid
        self.client_id = str(uuid.uuid4())
        
        self.active_notes = {}
        self.load_and_restore_notes()
        
        # Start P2P synchronization TCP listener
        self.tcp_server = None
        self.listen_port = 0
        self.start_p2p_listener()

        # Instantiate and show Control Window (Always on Top, Frameless)
        self.control_window = ControlWindow(self.username, is_auto_logged_in=logged_in)
        self.control_window.new_memo_requested.connect(lambda: self.create_new_note_window(note_type="memo"))
        self.control_window.new_todo_requested.connect(lambda: self.create_new_note_window(note_type="todo"))
        self.control_window.dropdown_requested.connect(self.show_notes_dropdown_menu)
        self.control_window.toggle_autologin_requested.connect(self.handle_toggle_autologin)
        self.control_window.force_local_requested.connect(self.handle_force_local)
        self.control_window.force_server_requested.connect(self.handle_force_server)
        self.control_window.close_requested.connect(self.quit_app)

        # Restore previous window position, or default to the center of the screen
        pos = storage.load_control_position()
        if pos:
            self.control_window.move(pos[0], pos[1])
        else:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = screen_geo.x() + (screen_geo.width() - self.control_window.width()) // 2
                y = screen_geo.y() + (screen_geo.height() - self.control_window.height()) // 2
                self.control_window.move(x, y)

        self.control_window.show()
        self.control_window.raise_()
        
    def run(self):
        # Start PySide6 event loop
        exit_code = self.app.exec()
        try:
            storage.unregister_client(self.client_id)
        except Exception:
            pass
        return exit_code

    def show_all_notes(self):
        if not self.active_notes:
            self.create_new_note_window()
        else:
            for window in self.active_notes.values():
                self.bring_note_to_top(window)

    def bring_note_to_top(self, window):
        window.show()
        window.raise_()
        window.activateWindow()

    def show_notes_dropdown_menu(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        from PySide6.QtCore import QPoint
        
        menu = QMenu(self.control_window)
        menu.setStyleSheet(self.control_window.get_menu_style())
        
        if not self.active_notes:
            no_action = QAction("등록된 메모 없음", menu)
            no_action.setEnabled(False)
            menu.addAction(no_action)
        else:
            for note_id, window in self.active_notes.items():
                if window.note_type == "memo":
                    text = window.text_edit.toPlainText().strip()
                    preview = "📝 " + (text[:15] + "..." if len(text) > 15 else (text or "빈 메모"))
                else:
                    items = window.get_todo_items_data()
                    first_text = items[0]["text"] if items else ""
                    preview = "✓ " + (first_text[:12] + "..." if len(first_text) > 12 else (first_text or "빈 할일 목록"))
                
                action = QAction(preview, menu)
                # Keep closure reference to window
                action.triggered.connect(lambda checked=False, w=window: self.bring_note_to_top(w))
                menu.addAction(action)
                
        menu.addSeparator()
        
        action_all = QAction("📂 모든 메모 표시", menu)
        action_all.triggered.connect(self.show_all_notes)
        menu.addAction(action_all)
        
        # Position menu right below the dropdown button
        menu.exec(self.control_window.btn_dropdown.mapToGlobal(QPoint(0, self.control_window.btn_dropdown.height() + 4)))

    def handle_toggle_autologin(self, enable):
        if enable:
            storage.save_autologin_info(self.username, self.password)
        else:
            storage.clear_autologin_info()

    def handle_force_local(self):
        # Close all active note windows
        for window in list(self.active_notes.values()):
            window.close()
        self.active_notes.clear()
        
        # Switch to offline local mode credentials
        self.username = "local_user"
        self.password = ""
        self.control_window.username = "local_user"
        self.control_window.is_auto_logged_in = False
        
        # Save version mode and enable SQLite forcing mode
        storage.save_version_mode("local")
        storage.set_force_local_sqlite(True)
        
        # Re-load and show notes from local SQLite
        self.load_and_restore_notes()

    def handle_force_server(self):
        # We need authentication to switch to Server mode
        from login_dialog import LoginDialog
        login = LoginDialog()
        res = login.exec()
        if res == QDialog.Accepted:
            # Close all active note windows
            for window in list(self.active_notes.values()):
                window.close()
            self.active_notes.clear()
            
            # Switch to server mode credentials
            self.username = login.username
            self.password = login.input_password.text().strip()
            self.control_window.username = self.username
            
            # Determine if auto-logged in based on checked state
            autologin_data = storage.load_autologin_info()
            self.control_window.is_auto_logged_in = (autologin_data is not None)
            
            # Save version mode and disable SQLite forcing mode
            storage.save_version_mode("server")
            storage.set_force_local_sqlite(False)
            
            # Re-load and show notes from MariaDB (falls back to SQLite if offline)
            self.load_and_restore_notes()

    def quit_app(self):
        try:
            # Save the control window's last position before exiting
            storage.save_control_position(self.control_window.x(), self.control_window.y())
        except Exception as e:
            print(f"Error saving control window position: {e}")
        try:
            storage.unregister_client(self.client_id)
        except Exception:
            pass
        self.save_all_notes()
        self.app.quit()



    def load_and_restore_notes(self):
        saved_notes = storage.load_notes(self.username)
        
        if not saved_notes:
            # Create a default first note
            self.create_new_note_window()
        else:
            for note_data in saved_notes:
                self.create_note_window_from_data(note_data)

    def create_note_window_from_data(self, data):
        note_id = data.get("id")
        window = NoteWindow(
            note_id=note_id,
            note_type=data.get("type", "memo"),
            content=data.get("content", ""),
            todo_items=data.get("todo_items", []),
            x=data.get("x", 100),
            y=data.get("y", 100),
            width=data.get("width", 300),
            height=data.get("height", 300),
            color=data.get("color", "yellow"),
            always_on_top=data.get("always_on_top", False),
            on_save_callback=self.save_all_notes,
            on_close_callback=self.handle_note_close,
            on_new_callback=self.handle_new_note_request,
            on_refresh_callback=self.reload_notes_from_db
        )
        self.active_notes[note_id] = window
        return window

    def create_new_note_window(self, x=100, y=100, note_type="memo", always_on_top=False):
        window = NoteWindow(
            note_type=note_type,
            content="",
            todo_items=[],
            x=x,
            y=y,
            width=300,
            height=300,
            color="yellow",
            always_on_top=always_on_top,
            on_save_callback=self.save_all_notes,
            on_new_callback=self.handle_new_note_request,
            on_refresh_callback=self.reload_notes_from_db
        )
        self.active_notes[window.note_id] = window
        self.save_all_notes()
        return window

    def handle_new_note_request(self, caller_window, note_type="memo"):
        # Position the new note to the right of the current window (with 10px spacing)
        new_x = caller_window.x() + caller_window.width() + 10
        new_y = caller_window.y()
        
        # Inherit always-on-top status from the caller note
        always_on_top = caller_window.always_on_top
        
        # Screen geometry check using QScreen to prevent placing window completely off-screen
        screen = self.app.primaryScreen().geometry()
        if new_x + 300 > screen.width():
            # If it goes off the right edge, wrap to the left (x=100) and shift down (y + 150)
            new_x = 100
            new_y = caller_window.y() + 150
            
        if new_y + 300 > screen.height():
            new_y = 100
            
        self.create_new_note_window(x=new_x, y=new_y, note_type=note_type, always_on_top=always_on_top)

    def handle_note_close(self, closed_window):
        note_id = closed_window.note_id
        if note_id in self.active_notes:
            del self.active_notes[note_id]
        self.save_all_notes()

    def save_all_notes(self, caller=None):
        notes_data = []
        for note_id, window in list(self.active_notes.items()):
            try:
                # Retrieve geometry and content
                notes_data.append(window.get_data())
            except Exception:
                pass
        storage.save_notes(notes_data, self.username)
        
        # Broadcast reload signal to peer clients in a background thread
        import threading
        threading.Thread(target=self.broadcast_reload, daemon=True).start()

    def start_p2p_listener(self):
        from PySide6.QtNetwork import QTcpServer, QHostAddress
        self.tcp_server = QTcpServer(self.app)
        # Port 0 lets the OS pick a free port dynamically
        if self.tcp_server.listen(QHostAddress.SpecialAddress.Any, 0):
            self.listen_port = self.tcp_server.serverPort()
            self.tcp_server.newConnection.connect(self.handle_p2p_connection)
            self.register_client_endpoint()
        else:
            print(f"Failed to start P2P TCP listener: {self.tcp_server.errorString()}")

    def register_client_endpoint(self):
        config = storage.get_db_connection_info()
        if not config:
            return
        import socket
        try:
            # Resolve local interface IP relative to DB host
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((config["host"], config["port"]))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        
        print(f"Registering client {self.client_id} at {local_ip}:{self.listen_port}")
        storage.register_client(self.client_id, local_ip, self.listen_port)

    def handle_p2p_connection(self):
        while self.tcp_server.hasPendingConnections():
            socket = self.tcp_server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self.read_p2p_data(s))

    def read_p2p_data(self, socket):
        try:
            data = socket.readAll().data().decode("utf-8")
            if data == "reload":
                print("Received P2P reload push notification.")
                self.reload_notes_from_db()
        except Exception as e:
            print(f"Error reading P2P data: {e}")
        finally:
            socket.disconnectFromHost()

    def broadcast_reload(self):
        peers = storage.get_active_clients(self.client_id)
        if not peers:
            return
        import socket
        for ip, port in peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                s.connect((ip, port))
                s.sendall(b"reload")
                s.close()
                print(f"Notified peer at {ip}:{port}")
            except Exception as e:
                print(f"Failed to notify peer at {ip}:{port}: {e}")

    def reload_notes_from_db(self):
        new_notes_data = storage.load_notes(self.username)
        new_ids = {note["id"] for note in new_notes_data}
        
        # 1. Close note windows that have been deleted in DB
        for note_id in list(self.active_notes.keys()):
            if note_id not in new_ids:
                window = self.active_notes[note_id]
                window.on_close_callback = None # disable save callback
                window.close()
                del self.active_notes[note_id]
                
        # 2. Update existing notes or create new ones
        for note_data in new_notes_data:
            note_id = note_data["id"]
            if note_id in self.active_notes:
                window = self.active_notes[note_id]
                window.on_save_callback = None # disable save callback during update
                
                # Apply updates
                window.current_color_name = note_data.get("color", "yellow")
                window.apply_theme()
                window.setGeometry(
                    note_data.get("x", window.x()),
                    note_data.get("y", window.y()),
                    note_data.get("width", window.width()),
                    note_data.get("height", window.height())
                )
                window.always_on_top = note_data.get("always_on_top", False)
                window.update_always_on_top()
                
                if window.note_type == "memo":
                    new_text = note_data.get("content", "")
                    if window.text_edit.toPlainText() != new_text:
                        cursor = window.text_edit.textCursor()
                        cursor_pos = cursor.position()
                        
                        window.text_edit.blockSignals(True)
                        window.text_edit.setPlainText(new_text)
                        
                        cursor.setPosition(min(cursor_pos, len(new_text)))
                        window.text_edit.setTextCursor(cursor)
                        window.text_edit.blockSignals(False)
                elif window.note_type == "todo":
                    window.list_widget.clear()
                    for item in note_data.get("todo_items", []):
                        window.add_todo_item_to_widget(item.get("text", ""), item.get("done", False))
                
                window.on_save_callback = self.save_all_notes
            else:
                self.create_note_window_from_data(note_data)

if __name__ == "__main__":
    app = GomgomPostitApp()
    sys.exit(app.run())
