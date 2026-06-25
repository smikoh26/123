from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os 
import requests
from bs4 import BeautifulSoup
import math # 引入數學庫進行資料分析

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

db = SQLAlchemy(app)

# 1. 原有的 Todo 模型
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

# 2. 為了滿足「爬蟲資料放資料庫」額外添加的 Quote 模型
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/html_tags")
def html_tags():
    return render_template("html_tags.html")

@app.route("/todo")
def todo():
    todos = Todo.query.all()
    return render_template("todo.html", todos=todos)

@app.route("/add", methods=["POST"])
def add_todo():
    content = request.form.get("content")
    if content:
        new_todo = Todo(content=content)
        db.session.add(new_todo)
        db.session.commit()
    return redirect("/todo")

@app.route("/update/<int:id>", methods=["POST"])
def update_todo(id):
    todo = Todo.query.get(id)
    if todo:
        new_content = request.form.get("content")
        if new_content:
            todo.content = new_content
            db.session.commit()
    return redirect("/todo")

@app.route("/about")
def about():
    return "<h1>About Page</h1><p>This is the about page.</p><a href='/'>Back to Home</a>"

@app.route("/news")
def news():
    url = "https://news.ycombinator.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    titles = soup.select(".titleline a")
    news_list = []
    for title in titles:
        news_list.append({
            "title": title.text,
            "url": title["href"]
        })
    return render_template("news.html", news_list=news_list)

# 3. 修改後的 Quotes 路由：結合「動態爬蟲存入資料庫」與「數學資料分析」
@app.route("/quotes")
def quotes():
    # 先檢查資料庫有沒有資料，如果沒有，才執行 Selenium 爬蟲（避免每次重複爬取導致速度極慢）
    existing_quotes = Quote.query.all()
    
    if not existing_quotes:
        options = Options()
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=options)

        try:
            driver.get("https://quotes.toscrape.com/js/")
            quote_elements = driver.find_elements(By.CLASS_NAME, "quote")

            for quote in quote_elements:
                text = quote.find_element(By.CLASS_NAME, "text").text
                author = quote.find_element(By.CLASS_NAME, "author").text

                # 將爬取到的資料建立物件並存入 PostgreSQL 資料庫
                new_quote = Quote(text=text, author=author)
                db.session.add(new_quote)
            
            db.session.commit()
            # 重新從資料庫撈取最新資料
            existing_quotes = Quote.query.all()
        finally:
            driver.quit()

    # --- 數學專業資料分析區段 (Data Analysis) ---
    lengths = [len(q.text) for q in existing_quotes]
    analysis = {}
    
    if lengths:
        total_quotes = len(lengths)
        mean_length = sum(lengths) / total_quotes # 平均數 $\mu$
        
        # 計算標準差 $\sigma$ (展現數學統計專業)
        variance = sum((x - mean_length) ** 2 for x in lengths) / total_quotes
        std_deviation = math.sqrt(variance)
        
        analysis = {
            "total": total_quotes,
            "mean": round(mean_length, 2),
            "std": round(std_deviation, 2),
            "max": max(lengths),
            "min": min(lengths)
        }

    return render_template(
        "quotes.html",
        quote_list=existing_quotes,
        analysis=analysis # 將分析結果傳給前端
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)