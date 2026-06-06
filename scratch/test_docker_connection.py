import os
import sys
import sqlite3
import base64

# Add web_app to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from services import his_service

SECRET_KEY = "bnkBHYT_encryptionKey_2026"

def encrypt_password(password: str) -> str:
    if not password:
        return ""
    encrypted_chars = []
    for i, char in enumerate(password):
        key_char = SECRET_KEY[i % len(SECRET_KEY)]
        encrypted_chars.append(chr(ord(char) ^ ord(key_char)))
    encrypted_str = "".join(encrypted_chars)
    return base64.b64encode(encrypted_str.encode('utf-8')).decode('utf-8')

def main():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app", "app_state.db"))
    print(f"[*] SQLite DB Path: {db_path}")
    if not os.path.exists(db_path):
        print("[-] Error: app_state.db not found.")
        sys.exit(1)

    # 1. Update SQLite config
    print("[*] Updating SQL Server Docker connection parameters in SQLite...")
    conn_sqlite = sqlite3.connect(db_path)
    cursor = conn_sqlite.cursor()
    
    # Check if there is a row in app_config
    cursor.execute("SELECT COUNT(*) FROM app_config")
    cnt = cursor.fetchone()[0]
    
    driver = "ODBC Driver 17 for SQL Server" # Default
    # Let's check which ODBC drivers are installed on this host
    import pyodbc
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    print(f"[*] Available ODBC Drivers on this host: {drivers}")
    if drivers:
        # Prefer ODBC Driver 17 or 18 if available
        for d in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
            if d in drivers:
                driver = d
                break
        else:
            driver = drivers[0]
            
    print(f"[*] Using ODBC Driver: {driver}")
    enc_pw = encrypt_password("Nguyenhong123@")
    
    if cnt == 0:
        cursor.execute("""
            INSERT INTO app_config (driver, server, database, auth, user, password, sp_op, sp_ip, listbh_key_col, listbh_date_col, auto_sync_enabled, auto_sync_time)
            VALUES (?, ?, ?, 'SQL Auth', 'sa', ?, 'sp_LayDanhSachNgoaiTru', 'sp_LayDanhSachNoiTru', 'Mã liên kết', 'Ngày ra', 0, '00:30')
        """, (driver, "localhost,1433", "eHospital_ThienHanh", enc_pw))
    else:
        cursor.execute("""
            UPDATE app_config
            SET driver = ?,
                server = 'localhost,1433',
                database = 'eHospital_ThienHanh',
                auth = 'SQL Auth',
                user = 'sa',
                password = ?,
                sp_op = 'sp_LayDanhSachNgoaiTru',
                sp_ip = 'sp_LayDanhSachNoiTru'
        """, (driver, enc_pw))
        
    conn_sqlite.commit()
    conn_sqlite.close()
    print("[+] Config updated in SQLite successfully! [OK]")

    # 2. Test Connection
    print("[*] Attempting test connection to Docker SQL Server...")
    cfg = {
        "driver": driver,
        "server": "localhost,1433",
        "database": "eHospital_ThienHanh",
        "auth": "SQL Auth",
        "user": "sa",
        "password": "Nguyenhong123@"
    }
    
    try:
        success = his_service.test_connection(cfg)
        if success:
            print("[+] DATABASE CONNECTION SUCCESSFUL! [OK] ODBC pyodbc connection is fully working.")
        else:
            print("[-] Connection failed. Please check parameters.")
    except Exception as e:
        print(f"[-] Connection failed with error: {e}")

if __name__ == "__main__":
    main()
