from flask import Flask
app = Flask(__name__)

# ----------------------------------------------------
# flask Configuration
from flask import render_template

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", error_message="")

@app.route("/search")
def search():
    return render_template("search.html")

# ----------------------------------------------------
# define routes


# ----------------------------------------------------
if(__name__ == "__main__"):
    app.run(debug=True, port=5000)
