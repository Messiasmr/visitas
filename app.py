from flask import Flask, render_template, session, url_for, request, redirect
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
    usuarios = db["usuarios"]
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

@app.route("/", methods=["GET"])
def home():
    count = increment_visitor_count()
    return render_template("index.html", visitor_count=count)

# Rota para exibir o formulário de registro
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

# Rota para processar o registro do usuário
@app.route("/register", methods=["POST"])
def register_user():
    email = request.form.get("email")
    senha = request.form.get("password")

    # Verifica se o usuário já existe
    if usuarios.find_one({"email": email}):
        return "Usuário já cadastrado!", 400

    # Insere o novo usuário no MongoDB
    usuarios.insert_one({"email": email, "senha": senha})
    return "Usuário cadastrado com sucesso!"

if __name__ == "__main__":
    app.run(debug=True)