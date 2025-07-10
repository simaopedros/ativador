from flask import Flask, request, jsonify
import sqlite3
import uuid
import datetime

app = Flask(__name__)
DB_NAME = "database.db"

# --- Inicialização do banco ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                email TEXT,
                used INTEGER DEFAULT 0,
                created_at TEXT,
                activated_at TEXT
            )
        ''')
        conn.commit()

# --- Criar nova licença ---
@app.route("/api/gerar", methods=["POST"])
def gerar_licenca():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email é obrigatório"}), 400

    licenca = str(uuid.uuid4()).replace("-", "")
    created_at = datetime.datetime.utcnow().isoformat()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO licenses (key, email, created_at) VALUES (?, ?, ?)", (licenca, email, created_at))
        conn.commit()

    return jsonify({"license_key": licenca})

# --- Ativar licença ---
@app.route("/api/ativar", methods=["POST"])
def ativar_licenca():
    data = request.get_json()
    key = data.get("key")

    if not key:
        return jsonify({"success": False, "message": "Chave não fornecida"}), 400

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT used FROM licenses WHERE key = ?", (key,))
        result = c.fetchone()

        if not result:
            return jsonify({"success": False, "message": "Chave inválida"}), 404

        if result[0] == 1:
            return jsonify({"success": False, "message": "Chave já utilizada"}), 403

        c.execute("UPDATE licenses SET used = 1, activated_at = ? WHERE key = ?", (datetime.datetime.utcnow().isoformat(), key))
        conn.commit()

    return jsonify({"success": True, "message": "Licença ativada com sucesso"})

# --- Verificar validade (opcional) ---
@app.route("/api/verificar", methods=["POST"])
def verificar_licenca():
    data = request.get_json()
    key = data.get("key")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT used FROM licenses WHERE key = ?", (key,))
        result = c.fetchone()

        if result and result[0] == 1:
            return jsonify({"valid": True})
        return jsonify({"valid": False})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
