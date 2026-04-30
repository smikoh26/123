from flask import Flask,render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/html_tags")
def html_tags():
    return render_template("html_tags.html")

@app.route("/about")
def about():
    return "<h1>About Page</h1><p>This is the about page.</p><a href='/'>Back to Home</a>"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", 
        port=5000,
        debug=True
    )
    

