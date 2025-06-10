from flask import Flask, render_template, session, url_for, request, redirect, jsonify
from werkzeug.utils import secure_filename
import os
import pymongo
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = "chave_segura"

# Configuração do MongoDB
MONGO_USER = os.getenv("Mongo_User")
MONGO_PASSWORD = os.getenv("Mongo_Password")
MONGO_HOST = os.getenv("Mongo_Host")
MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}/?retryWrites=true&w=majority"

try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["gamestore_db"]
    usuarios = db["usuarios"]
    print("Conexão com o MongoDB Atlas bem-sucedida!")
except pymongo.errors.ConfigurationError as e:
    print("Erro de configuração:", e)
except pymongo.errors.OperationFailure as e:
    print("Erro de autenticação:", e)
except Exception as e:
    print("Erro ao conectar ao MongoDB Atlas:", e)

# Configuração para upload de arquivos
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Rota principal (index)
@app.route("/", methods=["GET"])
def home():
    user_email = session.get("user")
    user = None
    if user_email:
        user = usuarios.find_one({"email": user_email})
    return render_template("index.html", user=user)

# Rota para a página de registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        profile_picture = request.files.get("profile_picture")

        # Verifica se o usuário já existe
        if usuarios.find_one({"email": email}):
            return "Usuário já cadastrado!", 400

        # Salva a foto de perfil, se fornecida
        profile_picture_path = None
        if profile_picture:
            filename = secure_filename(profile_picture.filename)
            profile_picture_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            profile_picture.save(profile_picture_path)

        # Insere o novo usuário no MongoDB
        usuarios.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "profile_picture": profile_picture_path
        })
        return redirect("/login")

    return render_template("register.html")

# Rota para a página de perfil
@app.route("/profile")
def profile():
    user_email = session.get("user")
    if not user_email:
        return redirect("/login")

    user = usuarios.find_one({"email": user_email})
    if not user:
        return redirect("/login")

    return render_template("profile.html", user=user)

# Rota para atualizar o nome do usuário
@app.route("/update-name", methods=["POST"])
def update_name():
    data = request.get_json()
    new_name = data.get("name")

    if not new_name or new_name.strip() == "":
        return jsonify({"error": "Nome inválido"}), 400

    session["user_name"] = new_name
    return jsonify({"message": "Nome atualizado com sucesso!"}), 200

# Rota para login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Verifica as credenciais
        user = usuarios.find_one({"email": email, "password": password})
        if user:
            session["user"] = email
            return redirect("/")
        else:
            return "Credenciais inválidas", 401

    return render_template("login.html")

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)