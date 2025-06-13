from flask import Flask, render_template, session, url_for, request, redirect, jsonify
from werkzeug.utils import secure_filename
import os
import pymongo
from dotenv import load_dotenv
import requests
import uuid
from datetime import datetime

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
    logged_user = None
    if "user" in session:
        logged_user = usuarios.find_one({"email": session["user"]})
    return render_template("index.html", logged_user=logged_user, user=user)

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

        user_id = str(uuid.uuid4())

        # Insere o novo usuário no MongoDB
        usuarios.insert_one({
            "user_id": user_id,
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
    user_id = request.args.get("id")
    user_email = request.args.get("user") or session.get("user")

    if user_id:
        user = usuarios.find_one({"user_id": user_id})
    elif user_email:
        user = usuarios.find_one({"email": user_email})
    else:
        user = None

    if not user:
        return "Perfil não encontrado", 404

    # Se o usuário estiver logado, pega o email/id dele
    logged_user_email = session.get("user")
    logged_user = usuarios.find_one({"email": logged_user_email}) if logged_user_email else None

    comments = list(db.comments.find({"profile_owner": user.get("email")}))
    # Busque amigos se quiser mostrar
    friend_ids = user.get("friends", [])
    friends = list(usuarios.find({"user_id": {"$in": friend_ids}}))

    favorite_games = []
    if user.get("favorite_games"):
        # Supondo que você tem uma função para buscar os dados dos jogos pelo ID
        favorite_games = buscar_jogos_por_ids(user["favorite_games"])

    return render_template(
        "profile.html",
        user=user,
        comments=comments,
        friends=friends,
        logged_user=logged_user,
        usuarios=usuarios,  # <-- Adicione esta linha!
        favorite_games=favorite_games
    )

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
from flask import session

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = usuarios.find_one({"email": email, "password": password})
        if user:
            session["user"] = email  # <-- Isso é essencial!
            return redirect("/")
        else:
            return render_template("login.html", error="Usuário ou senha inválidos")
    return render_template("login.html")

# Rota para logout
@app.route("/logout")
def logout():
    session.pop("user", None)
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

    # Atualiza imagem de fundo
    bg_file = request.files.get("bg_image")
    if bg_file and bg_file.filename:
        filename = secure_filename(bg_file.filename)
        bg_path = os.path.join(app.config["UPLOAD_FOLDER_BG"], filename)
        bg_file.save(bg_path)
        update_data["background_image"] = f"{UPLOAD_FOLDER_BG}/{filename}"

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
    friend_id = request.form.get("friend_id")

    if not friend_id:
        return redirect("/profile")

    # Busca o amigo pelo user_id
    friend = usuarios.find_one({"user_id": friend_id})
    if not friend or friend["email"] == user_email:
        return redirect("/profile")

    # Adiciona o amigo se ainda não estiver na lista
    usuarios.update_one(
        {"email": user_email},
        {"$addToSet": {"friends": friend_id}}
    )
    return redirect(f"/profile?id={friend_id}")

@app.route("/send-friend-request", methods=["POST"])
def send_friend_request():
    if "user" not in session:
        return redirect("/login")
    from_user = usuarios.find_one({"email": session["user"]})
    to_user_id = request.form.get("to_user_id")
    if not from_user or not to_user_id or from_user["user_id"] == to_user_id:
        return redirect("/profile")
    # Adiciona solicitação se ainda não enviada
    usuarios.update_one(
        {"user_id": to_user_id},
        {"$addToSet": {"friend_requests": from_user["user_id"]}}
    )
    return redirect(f"/profile?id={to_user_id}")

@app.route("/respond-friend-request", methods=["POST"])
def respond_friend_request():
    if "user" not in session:
        return redirect("/login")
    user = usuarios.find_one({"email": session["user"]})
    from_user_id = request.form.get("from_user_id")
    action = request.form.get("action")
    if not user or not from_user_id or action not in ["accept", "reject"]:
        return redirect("/profile")
    # Remove solicitação
    usuarios.update_one(
        {"user_id": user["user_id"]},
        {"$pull": {"friend_requests": from_user_id}}
    )
    if action == "accept":
        # Adiciona cada um na lista de amigos do outro
        usuarios.update_one(
            {"user_id": user["user_id"]},
            {"$addToSet": {"friends": from_user_id}}
        )
        usuarios.update_one(
            {"user_id": from_user_id},
            {"$addToSet": {"friends": user["user_id"]}}
        )
    return redirect("/profile")

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

@app.route("/search-users")
def search_users():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    # Busca por nome (case-insensitive) ou por user_id exato
    users = list(usuarios.find({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"user_id": query}
        ]
    }, {"password": 0}))  # Nunca envie a senha!

    # Retorne apenas dados necessários
    result = []
    for user in users:
        result.append({
            "user_id": user.get("user_id"),
            "name": user.get("name"),
            "email": user.get("email"),
            "profile_picture": user.get("profile_picture")
        })
    return jsonify(result)

# Adiciona user_id para usuários existentes
for user in usuarios.find({"user_id": {"$exists": False}}):
    usuarios.update_one(
        {"_id": user["_id"]},
        {"$set": {"user_id": str(uuid.uuid4())}}
    )
print("Todos os usuários agora têm user_id.")

@app.route("/toggle-favorite", methods=["POST"])
def toggle_favorite():
    if "user" not in session:
        return redirect("/login")
    user = usuarios.find_one({"email": session["user"]})
    game_id = request.form.get("game_id")
    if not user or not game_id:
        return redirect("/")
    if "favorite_games" not in user:
        user["favorite_games"] = []
    if game_id in user["favorite_games"]:
        usuarios.update_one({"email": user["email"]}, {"$pull": {"favorite_games": game_id}})
    else:
        usuarios.update_one({"email": user["email"]}, {"$addToSet": {"favorite_games": game_id}})
    return redirect(request.referrer or "/")

# Exemplo de adicionar notificação
@app.route("/add-notification", methods=["POST"])
def add_notification():
    if "user" not in session:
        return redirect("/login")
    user = usuarios.find_one({"email": session["user"]})
    game_id = request.form.get("game_id")
    game_name = request.form.get("game_name")
    discount_percent = request.form.get("discount")

    if not user or not game_id or not game_name or not discount_percent:
        return redirect("/")

    # Adiciona notificação
    usuarios.update_one(
        {"email": user["email"]},
        {"$push": {"notifications": {
            "type": "promo",
            "game_id": game_id,
            "game_name": game_name,
            "discount": discount_percent,
            "timestamp": datetime.utcnow()
        }}}
    )
    return redirect(request.referrer or "/")

def buscar_jogos_por_ids(ids):
    return list(jogos.find({"id": {"$in": ids}}))

if __name__ == "__main__":
    app.run(debug=True)