from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from dotenv import load_dotenv
import sqlite3, uuid, datetime, os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default")
DB_NAME = os.getenv("DB_NAME", "database.db")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

login_manager = LoginManager()
login_manager.init_app(app)

class Admin(UserMixin):
    def __init__(self, id): self.id = id

@login_manager.user_loader
def load_user(user_id): return Admin(user_id)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                email TEXT,
                used INTEGER DEFAULT 0,
                created_at TEXT,
                activated_at TEXT,
                machine_id TEXT
            )
        ''')
        conn.commit()

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            login_user(Admin(ADMIN_USER))
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Usuário ou senha inválidos")
    return render_template("login.html")

@app.route("/admin/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def dashboard():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT key, email, used, created_at, activated_at, machine_id FROM licenses ORDER BY created_at DESC")
        licencas = c.fetchall()
    return render_template("dashboard.html", licencas=licencas)

@app.route("/admin/criar", methods=["POST"])
@login_required
def admin_criar():
    email = request.form.get("email")
    if email:
        licenca = str(uuid.uuid4()).replace("-", "")
        now = datetime.datetime.utcnow().isoformat()
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO licenses (key, email, created_at) VALUES (?, ?, ?)", (licenca, email, now))
            conn.commit()
    return redirect(url_for("dashboard"))

@app.route("/admin/remover/<key>")
@login_required
def admin_remover(key):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM licenses WHERE key = ?", (key,))
        conn.commit()
    return redirect(url_for("dashboard"))

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

@app.route("/api/ativar", methods=["POST"])
def ativar_licenca():
    data = request.get_json()
    key = data.get("key")
    machine_id = data.get("machine_id")

    if not key or not machine_id:
        return jsonify({"success": False, "message": "Chave e ID da máquina são obrigatórios"}), 400

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT used, machine_id FROM licenses WHERE key = ?", (key,))
        result = c.fetchone()

        if not result:
            return jsonify({"success": False, "message": "Chave inválida"}), 404

        used, saved_machine_id = result

        if used and saved_machine_id != machine_id:
            return jsonify({"success": False, "message": "Licença já usada em outra máquina"}), 403

        if not used:
            c.execute("UPDATE licenses SET used = 1, activated_at = ?, machine_id = ? WHERE key = ?",
                      (datetime.datetime.utcnow().isoformat(), machine_id, key))
            conn.commit()

        return jsonify({"success": True, "message": "Licença ativada com sucesso"})

@app.route("/api/verificar", methods=["POST"])
def verificar_licenca():
    data = request.get_json()
    key = data.get("key")
    machine_id = data.get("machine_id")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT used, machine_id FROM licenses WHERE key = ?", (key,))
        result = c.fetchone()
        if result and result[0] == 1 and result[1] == machine_id:
            return jsonify({"valid": True})
        return jsonify({"valid": False})

@app.route("/api/cancelar", methods=["POST"])
def cancelar_licenca():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email é obrigatório"}), 400
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM licenses WHERE email = ?", (email,))
        conn.commit()
    return jsonify({"success": True, "message": "Licença cancelada"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
