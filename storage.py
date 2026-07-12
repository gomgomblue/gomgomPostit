import os
import json
import sqlite3
import hashlib
try:
    import pymysql
except ImportError:
    pymysql = None

def get_app_directory():
    import sys
    import platform
    # If running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        exec_path = sys.executable
        if platform.system() == 'Darwin':
            # On macOS, sys.executable is inside the .app bundle (Contents/MacOS/)
            # We want the directory containing the .app bundle
            exec_dir = os.path.dirname(exec_path)  # Contents/MacOS
            contents_dir = os.path.dirname(exec_dir)  # Contents
            app_bundle_dir = os.path.dirname(contents_dir)  # GomgomPostit.app
            app_parent_dir = os.path.dirname(app_bundle_dir)  # Folder containing the .app
            return app_parent_dir
        else:
            # On Windows/Linux, it's just the folder containing the executable (.exe)
            return os.path.dirname(exec_path)
    else:
        # Development mode
        return os.path.dirname(os.path.abspath(__file__))

# Database file for SQLite fallback
SQLITE_FILE = os.path.join(get_app_directory(), ".gomgom_postit.db")

# Base64 encrypted MariaDB connection details (XOR encrypted with a 32-byte key derived via PBKDF2 using the salt 'gominfra')
ENCRYPTED_DB_INFO = "FmWQhVYdic5/Y76Kz1dNtnw+RcM/NGYmxhTzBmN6K5tPa9jIVQbZgH178taZEBP7P2hfwiNoLWySX/oGO2AqmR9l1MoHGcqHLDa9l8QFEfc9OxvGdH88JIZfskNvcTiIDCWZmUBLkdR9Jr2Ix0hGiG8lWcUvbi0r"

def get_decrypted_db_connection_info():
    import base64
    import hashlib
    try:
        # Generate 32-byte key via PBKDF2 with salt 'gominfra' and password 'gominfra'
        salt = b"gominfra"
        password = b"gominfra"
        key = hashlib.pbkdf2_hmac("sha256", password, salt, 100000, 32)
        
        # Decode base64 and perform XOR decryption
        ciphertext = base64.b64decode(ENCRYPTED_DB_INFO.encode("utf-8"))
        plaintext = bytearray()
        for i in range(len(ciphertext)):
            plaintext.append(ciphertext[i] ^ key[i % len(key)])
            
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        print(f"Error decrypting database connection info: {e}")
        return None

FORCE_LOCAL_SQLITE = False

def set_force_local_sqlite(force):
    global FORCE_LOCAL_SQLITE
    FORCE_LOCAL_SQLITE = force

def is_force_local_sqlite():
    return FORCE_LOCAL_SQLITE

def get_db_connection_info():
    """Returns decrypted MariaDB connection config, or None if decryption fails or host is empty."""
    if FORCE_LOCAL_SQLITE:
        return None
    info = get_decrypted_db_connection_info()
    if info:
        host = info.get("host", "").strip()
        if host and host != "your_host":
            return info
    return None
def get_db_connection_info_unforced():
    """Returns decrypted MariaDB connection config regardless of FORCE_LOCAL_SQLITE state."""
    info = get_decrypted_db_connection_info()
    if info:
        host = info.get("host", "").strip()
        if host and host != "your_host":
            return info
    return None
# ==================== Password Hashing Helper ====================

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    pw_hash = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return pw_hash, salt

# ==================== SQLite Persistence (Local fallback) ====================

def init_sqlite():
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                username TEXT,
                type TEXT,
                content TEXT,
                todo_items TEXT,
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                color TEXT,
                always_on_top INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                salt TEXT
            )
        """)
        # Backward compatibility: alter tables if needed
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN username TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing SQLite DB: {e}")

def load_notes_sqlite(username):
    init_sqlite()
    notes = []
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE username = ?", (username,))
        rows = cursor.fetchall()
        for row in rows:
            notes.append({
                "id": row["id"],
                "type": row["type"],
                "content": row["content"],
                "todo_items": json.loads(row["todo_items"]) if row["todo_items"] else [],
                "x": row["x"],
                "y": row["y"],
                "width": row["width"],
                "height": row["height"],
                "color": row["color"],
                "always_on_top": bool(row["always_on_top"])
            })
        conn.close()
    except Exception as e:
        print(f"Error loading notes from SQLite: {e}")
    return notes

def save_notes_sqlite(notes, username):
    init_sqlite()
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE username = ?", (username,))
        for note in notes:
            cursor.execute("""
                INSERT INTO notes (id, username, type, content, todo_items, x, y, width, height, color, always_on_top)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note.get("id"),
                username,
                note.get("type"),
                note.get("content"),
                json.dumps(note.get("todo_items", [])),
                note.get("x"),
                note.get("y"),
                note.get("width"),
                note.get("height"),
                note.get("color"),
                1 if note.get("always_on_top") else 0
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving notes to SQLite: {e}")

# ==================== MariaDB Persistence (Primary remote) ====================

def init_mariadb(config):
    import pymysql
    try:
        # Step 1: Connect to server without database to ensure DB existence
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
        conn.commit()
        conn.close()
        
        # Step 2: Connect to the database and create tables
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(50),
                type VARCHAR(10),
                content TEXT,
                todo_items TEXT,
                x INT,
                y INT,
                width INT,
                height INT,
                color VARCHAR(20),
                always_on_top TINYINT(1)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_clients (
                client_id VARCHAR(36) PRIMARY KEY,
                ip VARCHAR(45),
                port INT,
                last_seen DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password_hash VARCHAR(64),
                salt VARCHAR(32)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        # Backward compatibility: alter tables if needed
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN username VARCHAR(50)")
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing MariaDB: {e}")
        raise e

def load_notes_mariadb(username, config):
    import pymysql
    init_mariadb(config)
    notes = []
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE username = %s", (username,))
        rows = cursor.fetchall()
        for row in rows:
            notes.append({
                "id": row["id"],
                "type": row["type"],
                "content": row["content"],
                "todo_items": json.loads(row["todo_items"]) if row["todo_items"] else [],
                "x": row["x"],
                "y": row["y"],
                "width": row["width"],
                "height": row["height"],
                "color": row["color"],
                "always_on_top": bool(row["always_on_top"])
            })
        conn.close()
    except Exception as e:
        print(f"Error loading notes from MariaDB: {e}")
        raise e
    return notes

def save_notes_mariadb(notes, username, config):
    import pymysql
    init_mariadb(config)
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE username = %s", (username,))
        for note in notes:
            cursor.execute("""
                INSERT INTO notes (id, username, type, content, todo_items, x, y, width, height, color, always_on_top)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                note.get("id"),
                username,
                note.get("type"),
                note.get("content"),
                json.dumps(note.get("todo_items", [])),
                note.get("x"),
                note.get("y"),
                note.get("width"),
                note.get("height"),
                note.get("color"),
                1 if note.get("always_on_top") else 0
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving notes to MariaDB: {e}")
        raise e

# ==================== User Auth Integration ====================

def register_user(username, password):
    config = get_db_connection_info_unforced()
    if config:
        try:
            return register_user_mariadb(username, password, config)
        except Exception:
            pass
    return register_user_sqlite(username, password)

def authenticate_user(username, password):
    config = get_db_connection_info_unforced()
    if config:
        try:
            return authenticate_user_mariadb(username, password, config)
        except Exception:
            pass
    return authenticate_user_sqlite(username, password)

def change_password(username, current_password, new_password):
    # First authenticate
    if not authenticate_user(username, current_password):
        return False
        
    config = get_db_connection_info_unforced()
    if config:
        try:
            return change_password_mariadb(username, new_password, config)
        except Exception:
            pass
    return change_password_sqlite(username, new_password)

def change_password_sqlite(username, new_password):
    init_sqlite()
    pw_hash, salt = hash_password(new_password)
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", 
                       (pw_hash, salt, username))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating SQLite password: {e}")
        return False

def change_password_mariadb(username, new_password, config):
    import mysql.connector
    pw_hash, salt = hash_password(new_password)
    try:
        conn = mysql.connector.connect(
            host=config.get("host"),
            user=config.get("user"),
            password=config.get("password"),
            database=config.get("database"),
            port=config.get("port", 3306)
        )
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = %s, salt = %s WHERE username = %s", 
                       (pw_hash, salt, username))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating MariaDB password: {e}")
        raise e

def register_user_sqlite(username, password):
    init_sqlite()
    pw_hash, salt = hash_password(password)
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", 
                       (username, pw_hash, salt))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Error registering SQLite user: {e}")
        return False

def authenticate_user_sqlite(username, password):
    init_sqlite()
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            stored_hash, salt = row[0], row[1]
            pw_hash, _ = hash_password(password, salt)
            return pw_hash == stored_hash
    except Exception as e:
        print(f"Error authenticating SQLite user: {e}")
    return False

def register_user_mariadb(username, password, config):
    import pymysql
    init_mariadb(config)
    pw_hash, salt = hash_password(password)
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)", 
                       (username, pw_hash, salt))
        conn.commit()
        conn.close()
        return True
    except pymysql.err.IntegrityError:
        return False
    except Exception as e:
        print(f"Error registering MariaDB user: {e}")
        return False

def authenticate_user_mariadb(username, password, config):
    import pymysql
    init_mariadb(config)
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            stored_hash, salt = row["password_hash"], row["salt"]
            pw_hash, _ = hash_password(password, salt)
            return pw_hash == stored_hash
    except Exception as e:
        print(f"Error authenticating MariaDB user: {e}")
    return False

# ==================== Client Registry (P2P Sync) ====================

def register_client(client_id, ip, port):
    config = get_db_connection_info()
    if not config:
        return
    import pymysql
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO active_clients (client_id, ip, port, last_seen)
            VALUES (%s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE ip = VALUES(ip), port = VALUES(port), last_seen = NOW()
        """, (client_id, ip, port))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error registering client: {e}")

def unregister_client(client_id):
    config = get_db_connection_info()
    if not config:
        return
    import pymysql
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_clients WHERE client_id = %s", (client_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error unregistering client: {e}")

def get_active_clients(exclude_client_id):
    config = get_db_connection_info()
    if not config:
        return []
    import pymysql
    clients = []
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ip, port FROM active_clients 
            WHERE client_id != %s AND last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        """, (exclude_client_id,))
        rows = cursor.fetchall()
        for row in rows:
            clients.append((row["ip"], row["port"]))
        conn.close()
    except Exception as e:
        print(f"Error fetching active clients: {e}")
    return clients

# ==================== Unified Interface ====================

def load_notes(username):
    """Loads notes from DB. Fallback to SQLite if MariaDB is unavailable or not configured."""
    config = get_db_connection_info()
    if config:
        try:
            print("Connecting to MariaDB...")
            return load_notes_mariadb(username, config)
        except Exception as e:
            print(f"Failed to connect to MariaDB: {e}. Falling back to local SQLite DB.")
    
    print("Using local SQLite DB...")
    return load_notes_sqlite(username)

def save_notes(notes, username):
    """Saves notes to DB. Fallback to SQLite if MariaDB is unavailable or not configured."""
    config = get_db_connection_info()
    if config:
        try:
            save_notes_mariadb(notes, username, config)
            return
        except Exception as e:
            print(f"Failed to save to MariaDB: {e}. Falling back to local SQLite DB.")
            
    save_notes_sqlite(notes, username)

# ==================== Auto Login Helpers ====================

def get_machine_key():
    import uuid
    import hashlib
    # Combine MAC address and a fixed app-specific salt
    mac = str(uuid.getnode())
    salt = b"gomgom_app_salt_for_security"
    return hashlib.pbkdf2_hmac("sha256", mac.encode("utf-8"), salt, 50000, 32)

def save_autologin_info(username, password):
    import json
    import base64
    try:
        data = {"username": username, "password": password}
        plaintext = json.dumps(data).encode("utf-8")
        key = get_machine_key()
        
        # XOR encrypt
        ciphertext = bytearray()
        for i in range(len(plaintext)):
            ciphertext.append(plaintext[i] ^ key[i % len(key)])
            
        encoded = base64.b64encode(ciphertext).decode("utf-8")
        
        # Save to ~/.gomgom_autologin
        file_path = os.path.expanduser("~/.gomgom_autologin")
        with open(file_path, "w") as f:
            f.write(encoded)
        return True
    except Exception as e:
        print(f"Error saving autologin info: {e}")
        return False

def load_autologin_info():
    import json
    import base64
    file_path = os.path.expanduser("~/.gomgom_autologin")
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r") as f:
            encoded = f.read().strip()
        if not encoded:
            return None
            
        ciphertext = base64.b64decode(encoded.encode("utf-8"))
        key = get_machine_key()
        
        # XOR decrypt
        plaintext = bytearray()
        for i in range(len(ciphertext)):
            plaintext.append(ciphertext[i] ^ key[i % len(key)])
            
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        print(f"Error loading autologin info: {e}")
        return None

def clear_autologin_info():
    file_path = os.path.expanduser("~/.gomgom_autologin")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

# ==================== Unified Config Helpers ====================

CONFIG_FILE = os.path.join(get_app_directory(), ".gomgom_config")

def load_unified_config():
    import json
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_unified_config(data):
    import json
    try:
        current_config = load_unified_config()
        current_config.update(data)
        with open(CONFIG_FILE, "w") as f:
            json.dump(current_config, f)
        return True
    except Exception as e:
        print(f"Error saving unified config: {e}")
        return False

# ==================== Control Position Helpers ====================

def save_control_position(x, y):
    return save_unified_config({"control_position": {"x": x, "y": y}})

def load_control_position():
    config = load_unified_config()
    pos = config.get("control_position")
    if pos and "x" in pos and "y" in pos:
        return pos["x"], pos["y"]
    return None

# ==================== Version Mode Helpers ====================

def save_version_mode(mode):
    return save_unified_config({"version_mode": mode})

def load_version_mode():
    config = load_unified_config()
    return config.get("version_mode", "local")  # Default to local mode on first execution

# ==================== Password Reset Helpers ====================

def reset_password_with_email(email):
    # Verify if user exists (since email is the username)
    if not check_user_exists(email):
        return False
        
    # Generate 6-digit random number
    import random
    import string
    new_password = "".join(random.choices(string.digits, k=6))
    
    # Hash and update in DB
    success = False
    config = get_db_connection_info_unforced()
    if config:
        try:
            success = change_password_mariadb(email, new_password, config)
        except Exception:
            pass
    if not success:
        success = change_password_sqlite(email, new_password)
        
    if success:
        # Send Email to the username (which is email)
        send_reset_email(email, email, new_password)
        return True
        
    return False

def check_user_exists(username):
    config = get_db_connection_info_unforced()
    if config:
        try:
            import pymysql
            init_mariadb(config)
            conn = pymysql.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
                charset="utf8mb4"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return True
        except Exception:
            pass
            
    # Fallback to local SQLite
    init_sqlite()
    try:
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return True
    except Exception as e:
        print(f"Error checking user existence: {e}")
    return False

def decrypt_smtp_credential(encoded_data: str) -> str:
    import base64
    key = "GomgomPostitSecretKey"
    try:
        decoded_bytes = base64.b64decode(encoded_data.encode('utf-8'))
        decoded_str = decoded_bytes.decode('latin1')
        decrypted = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(decoded_str))
        return decrypted
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""

def send_reset_email(to_email, username, new_password):
    import smtplib
    from email.mime.text import MIMEText
    
    subject = "[곰곰메모] 비밀번호가 초기화되었습니다."
    body = f"안녕하세요, {username}님.\n요청하신 비밀번호 초기화가 완료되었습니다.\n\n임시 비밀번호: {new_password}\n\n로그인 후 새로운 비밀번호로 변경하여 사용해 주시기 바랍니다."
    
    # Decrypt SMTP Credentials
    enc_user = "IAAAAAAAfg0fAQwWNgQRMgIZKgwVaQwCCg=="
    enc_pass = "MwoFAgoOIwYUGA0SKQkKBg=="
    
    smtp_user = decrypt_smtp_credential(enc_user)
    smtp_pass = decrypt_smtp_credential(enc_pass)
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email
    
    # Fallback to local logs
    try:
        log_path = os.path.expanduser("~/.gomgom_email_logs.txt")
        with open(log_path, "a") as f:
            f.write(f"=== EMAIL TO: {to_email} (User: {username}) ===\n{body}\n=========================================\n\n")
        print(f"Password reset mail logged successfully to {log_path}")
    except Exception as e:
        print(f"Error logging reset email: {e}")
        
    try:
        # Connect to Gmail SMTP server using SSL on Port 465
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        print("SMTP mail sent successfully via Gmail!")
        return True
    except Exception as e:
        print(f"SMTP sending failed: {e}")
        return False
