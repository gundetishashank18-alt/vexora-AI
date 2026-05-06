from dotenv import load_dotenv
load_dotenv()

import os
import requests
import secrets
import re
import urllib.parse
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from groq import Groq

app = Flask(__name__)
# Render lo Environment Variable nunchi techukuntam, lekapothe random generate avtadi
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ==== API KEYS - RENDER LO ENVIRONMENT VARIABLES GA PETTALI ====
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID')
# ===============================================================

# ==== LOGIN DETAILS -.ENV NUNCHI VASTADI ====
VALID_USERNAME = os.environ.get('VALID_USERNAME', "shashank")
VALID_PASSWORD = os.environ.get('VALID_PASSWORD')
# ==========================================

client = Groq(api_key=GROQ_API_KEY)

def needs_search(user_message):
    msg = user_message.lower()
    if len(msg.split()) <= 2 and msg in ["hi", "hello", "hii", "ok", "thanks", "bye"]:
        return False
    return True

def is_image_request(user_message):
    """Image generate cheyyala check chestadi"""
    msg = user_message.lower()
    image_keywords = ['draw', 'generate', 'create', 'image', 'picture', 'gese', 'chey', 'photo', 'drawing', 'paint', 'sketch']
    return any(word in msg for word in image_keywords)

def generate_image_url(prompt):
    """Pollinations.ai tho image URL create chestadi"""
    # Prompt clean chey - "dog drawing chey" → "dog"
    clean_prompt = re.sub(r'(draw|generate|create|image|picture|gese|chey|photo|drawing|paint|sketch|kavali|create|generate)', '', prompt, flags=re.IGNORECASE).strip()
    if not clean_prompt:
        clean_prompt = prompt

    encoded_prompt = urllib.parse.quote(clean_prompt)
    # model=flux best quality, nologo=true ads teesestadi
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&model=flux&nologo=true"
    return image_url, clean_prompt

def google_search(query):
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": GOOGLE_API_KEY, "cx": SEARCH_ENGINE_ID, "q": query, "num": 5}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = []
        if "items" in data:
            for item in data["items"]:
                results.append(f"Source: {item.get('title', '')}\nInfo: {item.get('snippet', '')}")
        return "\n\n---\n\n".join(results) if results else "No web results found"
    except Exception as e:
        print(f"Google search failed: {e}")
        return ""

def get_vexora_response(user_message):
    try:
        # Live date techukuntam - prati sari current date vastadi
        today = datetime.now().strftime("%A, %B %d, %Y")

        search_context = ""
        if needs_search(user_message):
            search_data = google_search(user_message)
            if search_data:
                search_context = f"\n\n[REAL-TIME WEB DATA]\n{search_data}\n[END WEB DATA]\n"

        messages = [
            {
                "role": "system",
                "content": f"""You are Vexora, a helpful AI assistant created by Shashank from Hyderabad.
                1. LANGUAGE: If user asks in English, reply ONLY in English. If Telugu/Mix, reply in Telugu+English mix.
                2. IDENTITY: If asked 'who created you', reply: 'I was created by Shashank from Hyderabad.' OR Telugu lo 'Nenu Vexora. Nannu Shashank create chesadu.'
                3. ACCURACY: For factual questions, use [REAL-TIME WEB DATA] as primary source.
                4. DATE: Today is {today}. Always use this exact date and day.
                5. STYLE: Short, direct answers. Don't say "Based on search results".
                {search_context}"""
            },
            {"role": "user", "content": user_message}
        ]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return f"Error mama: {str(e)}"

# Google ki chat API ni index cheyyoddu ani cheptam
@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /api/\nAllow: /login\nAllow: /"

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('chat'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('chat'))
        return render_template('login.html', error="Username or Password tappu mama")
    return render_template('login.html')

@app.route('/chat')
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('chat.html', username=session.get('username', 'User'))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if not session.get('logged_in'):
        return jsonify({'reply': 'Login avvu mama'}), 401

    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'reply': 'Emanna type chey mama'})

    # Image request aa check chey
    if is_image_request(user_message):
        image_url, clean_prompt = generate_image_url(user_message)
        return jsonify({
            'reply': f'Ikkada nee image: {clean_prompt} 🎨',
            'image_url': image_url,
            'is_image': True
        })

    # Normal text chat
    reply = get_vexora_response(user_message)
    return jsonify({'reply': reply, 'is_image': False})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 Vexora Starting - Public URL Ready")
    # host='0.0.0.0' pettam kabatti Render lo panichestadi
    # debug=False pettam kabatti safe
    app.run(host='0.0.0.0', port=5001, debug=False)