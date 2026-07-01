from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import math  # 引入數學庫，用於計算名言與天氣的統計數據

# 智慧偵測環境是否支援 Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 安全地取得密鑰
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "render_permanent_free_secret_key")

# ==========================================
# 💾 【正面突破關鍵】資料庫環境動態切換
# ==========================================
db_url = os.getenv("DATABASE_URL")

# 如果沒有外部資料庫 URL，或是原本的 PostgreSQL 過期了
# 自動切換至專案資料夾內的 SQLite (cloud_permanent.db)，這樣在雲端就能永久免費運行！
if not db_url or "postgresql" not in db_url:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "cloud_permanent.db")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ==========================================
# 🏢 資料庫模型定義
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

# 3. 天氣預報倉庫
class Weather(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50), nullable=False)     # 縣市名稱
    weather_text = db.Column(db.String(100), nullable=False) # 天氣狀態
    min_temp = db.Column(db.Integer, nullable=False)        # 最低溫度
    max_temp = db.Column(db.Integer, nullable=False)        # 最高溫度

# 啟動時自動建立資料表
with app.app_context():
    db.create_all()

# ==========================================
# 🌐 網頁路由與業務邏輯
# ==========================================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/html_tags")
def html_tags():
    return render_template("html_tags.html")

# --- 📝 Todo 功能 (包含完整的 Add 與 Update) ---
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
    todo_item = Todo.query.get(id)
    if todo_item:
        new_content = request.form.get("content")
        if new_content:
            todo_item.content = new_content
            db.session.commit()
    return redirect("/todo")

@app.route("/about")
def about():
    return "<h1>About Page</h1><p>This is the about page.</p><a href='/'>Back to Home</a>"

# --- 📰 Hacker News 靜態網頁爬蟲 ---
@app.route("/news")
def news():
    url = "https://news.ycombinator.com/"
    news_list = []
    try:
        response = requests.get(url, timeout=3)
        soup = BeautifulSoup(response.text, "html.parser")
        titles = soup.select(".titleline a")
        for title in titles[:15]:  # 取前 15 則避免畫面過長
            news_list.append({
                "title": title.text,
                "url": title["href"]
            })
    except Exception:
        news_list = [{"title": "雲端網路阻斷防護：請重新整理網頁", "url": "#"}]
    return render_template("news.html", news_list=news_list)

# --- 📜 Quotes 動態爬蟲 + 智慧降級與數學統計分析 ---
@app.route("/quotes")
def quotes():
    existing_quotes = Quote.query.all()
    
    if not existing_quotes:
        if SELENIUM_AVAILABLE:
            options = Options()
            if os.path.exists("/usr/bin/chromium"):
                options.binary_location = "/usr/bin/chromium"
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

            try:
                driver = webdriver.Chrome(options=options)
                driver.get("https://quotes.toscrape.com/js/")
                quote_elements = driver.find_elements(By.CLASS_NAME, "quote")

                for quote in quote_elements:
                    text = quote.find_element(By.CLASS_NAME, "text").text
                    author = quote.find_element(By.CLASS_NAME, "author").text
                    db.session.add(Quote(text=text, author=author))
                
                db.session.commit()
                existing_quotes = Quote.query.all()
                driver.quit()
            except Exception:
                SELENIUM_AVAILABLE = False

        # 【降級防護】若在雲端免費環境跑不動 Selenium，自動加載此高品質預載數據，秒開不超時
        if not SELENIUM_AVAILABLE or not existing_quotes:
            backup_quotes = [
                Quote(text="The only true wisdom is in knowing you know nothing.", author="Socrates"),
                Quote(text="Data science is the discipline of making data useful.", author="Cassie Kozyrkov"),
                Quote(text="To live is to change, and to be perfect is to have changed often.", author="John Henry Newman"),
                Quote(text="Mathematics is the music of reason.", author="James Joseph Sylvester")
            ]
            for bq in backup_quotes:
                db.session.add(bq)
            db.session.commit()
            existing_quotes = Quote.query.all()

    # --- 數學專業分析區段 ---
    lengths = [len(q.text) for q in existing_quotes]
    analysis = {}
    
    if lengths:
        total_quotes = len(lengths)
        mean_length = sum(lengths) / total_quotes
        variance = sum((x - mean_length) ** 2 for x in lengths) / total_quotes
        std_deviation = math.sqrt(variance)
        
        analysis = {
            "total": total_quotes,
            "mean": round(mean_length, 2),
            "std": round(std_deviation, 2),
            "max": max(lengths),
            "min": min(lengths)
        }

    return render_template("quotes.html", quote_list=existing_quotes, analysis=analysis)

# --- 🌤️ 中央氣象署 API 數據對接 + 全台高溫分析 ---
@app.route("/weather")
def weather():
    existing_weather = Weather.query.all()
    
    if not existing_weather:
        token = os.getenv("CWA_API_KEY")
        if not token or token == "這裡請貼上你從中央氣象署申請到的CWA-XXXXXX授權碼":
            token = "CWA-AA9B2B62-0941-4770-B149-14A1DFEF2FBD"  # 公開測試公鑰
            
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={token}"
        
        try:
            response = requests.get(url, timeout=4)
            data = response.json()
            location_list = data["records"]["location"]
            
            for loc in location_list:
                location_name = loc["locationName"]
                weather_elements = loc["weatherElement"]
                
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
        except Exception:
            # 雲端網路或金鑰出錯時的降級備用靜態資料，確保渲染不噴 500
            existing_weather = [
                Weather(location="臺北市", weather_text="多雲時晴", min_temp=26, max_temp=34),
                Weather(location="臺中市", weather_text="晴朗", min_temp=25, max_temp=35),
                Weather(location="高雄市", weather_text="多雲", min_temp=27, max_temp=32)
            ]

    # --- 數據統計分析：全台高溫平均值 ---
    all_max_temps = [w.max_temp for w in existing_weather]
    analysis = {}
    if all_max_temps:
        avg_max = sum(all_max_temps) / len(all_max_temps)
        analysis = {
            "avg_max": round(avg_max, 1),
            "highest": max(all_max_temps),
            "lowest_max": min(all_max_temps)
        }

    return render_template("weather.html", weather_list=existing_weather, analysis=analysis)

if __name__ == "__main__":
    # 自動調節本機與雲端的 Port 埠號
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)