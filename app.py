from flask import Flask, render_template, session, url_for, request, redirect, flash
import os
import pymongo
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

VISITOR_COUNT_FILE = "visitor_count.txt"
app.secret_key = "chave segura"

# Conexão com MongoDB Atlas
MONGO_USER = os.getenv("Mongo_User")
MONGO_PASSWORD = os.getenv("Mongo_Password")
MONGO_HOST = os.getenv("Mongo_Host")

MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}/?retryWrites=true&w=majority"
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["visitas_db"]
    users_collection = db["users"]
    print("Conexão com o MongoDB Atlas bem-sucedida!")
except pymongo.errors.ConfigurationError as e:
    print("Erro de configuração:", e)
except pymongo.errors.OperationFailure as e:
    print("Erro de autenticação:", e)
except Exception as e:
    print("Erro ao conectar ao MongoDB Atlas:", e)

def get_visitor_count():
    if os.path.exists(VISITOR_COUNT_FILE):
        with open(VISITOR_COUNT_FILE, "r") as file:
            return int(file.read())
    return 0

def increment_visitor_count():
    count = get_visitor_count() + 1
    with open(VISITOR_COUNT_FILE, "w") as file:
        file.write(str(count))
    return count

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    
    visitor_count = increment_visitor_count()
    games = [
        {"name": "Jogo 1", "description": "Descrição do Jogo 1"},
        {"name": "Jogo 2", "description": "Descrição do Jogo 2"},
        {"name": "Jogo 3", "description": "Descrição do Jogo 3"},
        {"name": "Jogo 4", "description": "Descrição do Jogo 4"},
    ]
    return render_template("index.html", visitor_count=visitor_count, games=games)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = users_collection.find_one({"email": email, "password": password})
        if user:
            session["user"] = user["email"]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("home"))
        else:
            flash("Email ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if users_collection.find_one({"email": email}):
            flash("Email já registrado.", "danger")
        else:
            users_collection.insert_one({"email": email, "password": password})
            flash("Cadastro realizado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)