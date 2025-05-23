from flask import Flask, render_template
import os

app = Flask(__name__)

VISITOR_COUNT_FILE = "visitor_count.txt"

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
    count = increment_visitor_count()
    return render_template("index.html", visitor_count=count)

if __name__ == "__main__":
    app.run(host="192.168.56.1", port=5000, debug=True)