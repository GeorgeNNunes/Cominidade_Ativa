import os
import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "comunidade_ativa.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-antes-de-publicar")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PHOTO_SIZE = (600, 600)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            neighborhood TEXT NOT NULL,
            photo_filename TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Entre na sua conta para continuar.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    with get_db() as db:
        return db.execute("SELECT id, name, email FROM users WHERE id = ?",
                          (session["user_id"],)).fetchone()


def save_photo(upload):
    if not upload or not upload.filename:
        return None
    original = secure_filename(upload.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato inválido. Use JPG, PNG ou WEBP.")
    try:
        upload.stream.seek(0)
        image = Image.open(upload.stream)
        image.verify()
        upload.stream.seek(0)
        image = Image.open(upload.stream).convert("RGB")
        image = image.resize(PHOTO_SIZE, Image.Resampling.LANCZOS)
        filename = f"{uuid.uuid4().hex}.jpg"
        image.save(UPLOAD_DIR / filename, "JPEG", quality=88, optimize=True)
        return filename
    except (UnidentifiedImageError, OSError):
        raise ValueError("O arquivo enviado não é uma imagem válida.")


@app.context_processor
def inject_user():
    return {"logged_user": current_user()}


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Only serve files from the dedicated uploads directory.
    from flask import send_from_directory
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()
    query = """SELECT reports.*, users.name AS author
               FROM reports JOIN users ON users.id = reports.user_id
               WHERE 1=1"""
    params = []
    if category:
        query += " AND reports.category = ?"
        params.append(category)
    if search:
        query += """ AND (reports.title LIKE ? OR reports.description LIKE ?
                       OR reports.neighborhood LIKE ?)"""
        term = f"%{search}%"
        params.extend([term, term, term])
    query += " ORDER BY reports.created_at DESC"
    with get_db() as db:
        reports = db.execute(query, params).fetchall()
    categories = ["Iluminação", "Limpeza urbana", "Infraestrutura",
                  "Saneamento", "Acessibilidade", "Outro"]
    return render_template("index.html", reports=reports, categories=categories,
                           selected_category=category, search=search)


@app.route("/cadastro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Preencha todos os campos. A senha deve ter pelo menos 8 caracteres.", "danger")
            return render_template("register.html")
        try:
            with get_db() as db:
                db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                           (name, email, generate_password_hash(password)))
            flash("Conta criada! Agora entre com seu e-mail e senha.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("index"))
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("login.html")


@app.route("/sair")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("index"))


@app.route("/ocorrencia/nova", methods=["GET", "POST"])
@login_required
def new_report():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()
        if not all([title, category, description, neighborhood]):
            flash("Preencha todos os campos obrigatórios.", "danger")
            return render_template("report_form.html")
        try:
            photo = save_photo(request.files.get("photo"))
            with get_db() as db:
                db.execute("""INSERT INTO reports
                    (user_id, title, category, description, neighborhood, photo_filename)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (session["user_id"], title, category, description, neighborhood, photo))
            flash("Ocorrência cadastrada.", "success")
            return redirect(url_for("my_reports"))
        except ValueError as error:
            flash(str(error), "danger")
    return render_template("report_form.html")


@app.route("/minhas-ocorrencias")
@login_required
def my_reports():
    with get_db() as db:
        reports = db.execute("""SELECT * FROM reports WHERE user_id = ?
                                ORDER BY created_at DESC""",
                             (session["user_id"],)).fetchall()
    return render_template("my_reports.html", reports=reports)


@app.route("/ocorrencia/<int:report_id>")
def report_detail(report_id):
    with get_db() as db:
        report = db.execute("""SELECT reports.*, users.name AS author
                               FROM reports JOIN users ON users.id = reports.user_id
                               WHERE reports.id = ?""", (report_id,)).fetchone()
    if not report:
        abort(404)
    return render_template("detail.html", report=report)


@app.route("/ocorrencia/<int:report_id>/excluir", methods=["POST"])
@login_required
def delete_report(report_id):
    with get_db() as db:
        report = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not report:
            abort(404)
        if report["user_id"] != session["user_id"]:
            abort(403)
        db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    if report["photo_filename"]:
        try:
            (UPLOAD_DIR / report["photo_filename"]).unlink(missing_ok=True)
        except OSError:
            pass
    flash("Ocorrência excluída.", "success")
    return redirect(url_for("my_reports"))


@app.errorhandler(413)
def too_large(_error):
    flash("A imagem ultrapassa o limite de 5 MB.", "danger")
    return redirect(url_for("new_report"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
