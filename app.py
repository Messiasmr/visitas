from flask import Flask, render_template, session, url_for, request, redirect
import os
import pymongo

app = Flask(__name__)

VISITOR_COUNT_FILE = "visitor_count.txt"
app.secret_key = "chave segura"

# Conexão com o MongoDB
MONGO_URI = "mongodb+srv://messias:<db_password>@clusterapi.gnrdo.mongodb.net/?retryWrites=true&w=majority&appName=Clusterapi"
client = pymongo.MongoClient(MONGO_URI)
db = client["visitas_db"]
usuarios = db["usuarios"]

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

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("password")
    user = usuarios.find_one({"email": email, "senha": senha})
    if user:
        session["email"] = email
        return f"Bem-vindo, {email}!"
    else:
        # Se não existir, cadastra o usuário
        usuarios.insert_one({"email": email, "senha": senha})
        session["email"] = email
        return f"Usuário cadastrado e logado: {email}"

if __name__ == "__main__":
    app.run(host="localhost", port=3000, debug=True)