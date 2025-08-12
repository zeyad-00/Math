from flask import Flask, render_template, request, session, Response
import base64
import os
from dotenv import load_dotenv
from uuid import uuid4
import google.generativeai as genai
from PIL import Image
import io

# Load environment variables and configure Gemini
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("", "")
genai.configure(api_key=os.getenv(""))

# System promp
system_prompt="""
مدرس رياضيات
"""

chat_histories = {}

# Ensure user session
@app.before_request
def ensure_session():
    if 'user_id' not in session:
        session['user_id'] = str(uuid4())
    if session['user_id'] not in chat_histories:
        chat_histories[session['user_id']] = [system_prompt]

# Encode image as PIL Image
def load_image(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return Image.open(io.BytesIO(image_bytes))

@app.route('/')
def index():
    image_files = sorted([f for f in os.listdir('static/images') if f.endswith('.jpg')])
    return render_template('index.html', image_files=image_files)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    img_data = data.get('image')
    prompt = data.get('prompt', '').strip()
    user_id = session['user_id']

    if not prompt:
        return {"error": "Prompt is required"}, 400

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
        recent_history = chat_histories[user_id][-12:]
        parts = [system_prompt] + recent_history + [prompt]

        if img_data and img_data.startswith("data:image"):
            crop_path = 'static/cropped.jpg'
            with open(crop_path, "wb") as fh:
                fh.write(base64.b64decode(img_data.split(',')[1]))
            image = load_image(crop_path)
            parts.append(image)

        stream = model.generate_content(parts, stream=True)

        def generate():
            full_response = ""
            for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text
            chat_histories[user_id].append(prompt)
            chat_histories[user_id].append(full_response)

        return Response(generate(), content_type='text/plain; charset=utf-8')

    except Exception as e:
        return {"error": str(e)}, 500    
if __name__ == "__main__":
    app.run(debug=True)

