from flask import Flask, render_template, session, url_for, request, redirect, jsonify
from werkzeug.utils import secure_filename
import os
import pymongo
from dotenv import load_dotenv
import requests

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
    # Permite acessar o perfil de outro usuário via ?user=email
    user_email = request.args.get("user") or session.get("user")
    if not user_email:
        return redirect("/login")

    user = usuarios.find_one({"email": user_email})
    if not user:
        return redirect("/login")

    comments = list(db.comments.find({"profile_owner": user_email}))
    return render_template("profile.html", user=user, comments=comments)

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

# Rota para atualizar o perfil do usuário
@app.route("/update-profile", methods=["POST"])
def update_profile():
    user_email = session.get("user")
    if not user_email:
        return redirect("/login")

    user = usuarios.find_one({"email": user_email})
    if not user:
        return redirect("/login")

    update_data = {}

    # Atualiza foto de perfil
    profile_picture = request.files.get("profile_picture")
    if profile_picture and profile_picture.filename:
        filename = secure_filename(profile_picture.filename)
        profile_picture_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        profile_picture.save(profile_picture_path)
        update_data["profile_picture"] = profile_picture_path

    # Atualiza arte única
    unique_art = request.files.get("unique_art")
    if unique_art and unique_art.filename:
        art_filename = secure_filename(unique_art.filename)
        unique_art_path = os.path.join(app.config["UPLOAD_FOLDER"], art_filename)
        unique_art.save(unique_art_path)
        update_data["unique_art"] = unique_art_path

    # Atualiza bio
    bio = request.form.get("bio")
    if bio is not None:
        update_data["bio"] = bio

    if update_data:
        usuarios.update_one({"email": user_email}, {"$set": update_data})

    return redirect("/profile")

@app.route("/add-comment", methods=["POST"])
def add_comment():
    if "user" not in session:
        return redirect("/login")
    author_email = session["user"]
    author = usuarios.find_one({"email": author_email})
    author_name = author["name"] if author else "Anônimo"

    profile_owner = request.form.get("profile_owner")
    text = request.form.get("comment")

    if not text or not profile_owner:
        return redirect("/profile")

    comment = {
        "profile_owner": profile_owner,
        "author_email": author_email,
        "author_name": author_name,
        "text": text
    }
    db.comments.insert_one(comment)
    return redirect("/profile")

@app.route("/add-friend", methods=["POST"])
def add_friend():
    if "user" not in session:
        return redirect("/login")
    user_email = session["user"]
    friend_email = request.form.get("friend_email")

    if not friend_email or friend_email == user_email:
        return redirect(f"/profile?user={friend_email}")

    # Adiciona o amigo se ainda não estiver na lista
    usuarios.update_one(
        {"email": user_email},
        {"$addToSet": {"friends": friend_email}}
    )
    return redirect(f"/profile?user={friend_email}")

import os
from dotenv import load_dotenv
import requests
from flask import jsonify, request

load_dotenv()

RAWG_API_KEY = os.getenv("RAWG_API_KEY")

@app.route("/api/games")
def api_games():
    search = request.args.get("search", "")
    page = request.args.get("page", 1)
    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&page_size=10&page={page}"
    if search:
        url += f"&search={search}"

    response = requests.get(url)
    data = response.json()
    games = []
    for game in data.get("results", []):
        games.append({
            "title": game["name"],
            "image": game.get("background_image"),
            "metacritic": game.get("metacritic"),
            "storeLinks": [
                {"store": "Steam", "url": f"https://store.steampowered.com/search/?term={game['name']}"}
            ]
        })
    # Retorne também o total de jogos
    return jsonify({
        "games": games,
        "count": data.get("count", 0)
    })

# Certifique-se de ter uma pasta para uploads, por exemplo: static/uploads/backgrounds
UPLOAD_FOLDER_BG = "static/uploads/backgrounds"
os.makedirs(UPLOAD_FOLDER_BG, exist_ok=True)
app.config["UPLOAD_FOLDER_BG"] = UPLOAD_FOLDER_BG

@app.route("/update-background", methods=["POST"])
def update_background():
    if "user" not in session:
        return redirect("/login")
    user_email = session["user"]
    user = usuarios.find_one({"email": user_email})
    if not user:
        return redirect("/login")

    bg_file = request.files.get("bg_image")
    if bg_file and bg_file.filename:
        filename = secure_filename(bg_file.filename)
        bg_path = os.path.join(app.config["UPLOAD_FOLDER_BG"], filename)
        bg_file.save(bg_path)
        # Salva o caminho relativo no banco
        usuarios.update_one(
            {"email": user_email},
            {"$set": {"background_image": f"{UPLOAD_FOLDER_BG}/{filename}"}}
        )
    return redirect("/profile")

if __name__ == "__main__":
    app.run(debug=True)