from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os 
import requests
from bs4 import BeautifulSoup
import math  # 引入數學庫進行資料科學統計

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# 載入環境變數（包含剛剛設定的 CWA_API_KEY）
load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

db = SQLAlchemy(app)

# ==========================================
# 🏢 資料庫模型定義 (PostgreSQL 雲端大倉庫)
# ==========================================

# 1. 待辦事項倉庫
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

# 2. 名言爬蟲倉庫
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)

# 3. 天氣預報倉庫 (全新添加！)
class Weather(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50), nullable=False)     # 縣市名稱
    weather_text = db.Column(db.String(100), nullable=False) # 天氣狀態（如：多雲短暫雨）
    min_temp = db.Column(db.Integer, nullable=False)        # 最低溫度
    max_temp = db.Column(db.Integer, nullable=False)        # 最高溫度

# 啟動時自動在 PostgreSQL 裡建立上面所有的資料表
with app.app_context():
    db.create_all()

# ==========================================
# 🌐 網頁路由與業務邏輯 (餐廳內廚)
# ==========================================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/html_tags")
def html_tags():
    return render_template("html_tags.html")

# --- 📝 Todo 功能 ---
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

# --- 📰 Hacker News 靜態網頁爬蟲 ---
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

# --- 📜 Quotes 動態爬蟲 + 數學統計分析 ---
@app.route("/quotes")
def quotes():
    existing_quotes = Quote.query.all()
    
    # 如果資料庫是空的，才啟動自動化爬蟲，避免每次重複讀取太慢
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

                new_quote = Quote(text=text, author=author)
                db.session.add(new_quote)
            
            db.session.commit()
            existing_quotes = Quote.query.all()
        finally:
            driver.quit()

    # --- 數學專業分析區段 ---
    lengths = [len(q.text) for q in existing_quotes]
    analysis = {}
    
    if lengths:
        total_quotes = len(lengths)
        mean_length = sum(lengths) / total_quotes # 平均值
        variance = sum((x - mean_length) ** 2 for x in lengths) / total_quotes # 方差
        std_deviation = math.sqrt(variance) # 標準差
        
        analysis = {
            "total": total_quotes,
            "mean": round(mean_length, 2),
            "std": round(std_deviation, 2),
            "max": max(lengths),
            "min": min(lengths)
        }

    return render_template("quotes.html", quote_list=existing_quotes, analysis=analysis)

# --- 🌤️ 中央氣象署 API 數據對接 + 全台高溫分析 (新功能！) ---
@app.route("/weather")
def weather():
    existing_weather = Weather.query.all()
    
    # 如果資料庫今天還沒有存過天氣，就去跟氣象署總部調報表
    if not existing_weather:
        token = os.getenv("CWA_API_KEY") # 從剛剛環境變數安全地取出密鑰
        if not token:
            return "<h1>錯誤：請先在 env.txt 中設定 CWA_API_KEY</h1>"
            
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={token}"
        
        try:
            response = requests.get(url)
            data = response.json()
            location_list = data["records"]["location"]
            
            for loc in location_list:
                location_name = loc["locationName"]
                weather_elements = loc["weatherElement"]
                
                # 抓取未來的預報數據
                wx = weather_elements[0]["time"][0]["parameter"]["parameterName"]
                min_t = weather_elements[2]["time"][0]["parameter"]["parameterName"]
                max_t = weather_elements[4]["time"][0]["parameter"]["parameterName"]
                
                new_weather = Weather(
                    location=location_name,
                    weather_text=wx,
                    min_temp=int(min_t),
                    max_temp=int(max_t)
                )
                db.session.add(new_weather)
                
            db.session.commit()
            existing_weather = Weather.query.all()
        except Exception as e:
            return f"<h1>氣象資料抓取失敗：{str(e)}</h1>"

    # --- 數據統計分析：全台高溫平均值 ---
    all_max_temps = [w.max_temp for w in existing_weather]
    analysis = {}
    if all_max_temps:
        avg_max = sum(all_max_temps) / len(all_max_temps) # 全台最高溫的平均數
        analysis = {
            "avg_max": round(avg_max, 1),
            "highest": max(all_max_temps),
            "lowest_max": min(all_max_temps)
        }

    return render_template("weather.html", weather_list=existing_weather, analysis=analysis)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)