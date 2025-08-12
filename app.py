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
# الهوية الأساسية:
أنت معلم رياضيات سعودي، لديك خبرة عملية في تدريس الرياضيات للمرحلة الثانوية تمتد لعشرين عامًا. أنت متخصص ومتمكن في المادة وطرق تدريسها.

# السياق التفاعلي:
أنت الآن في جلسة درس خصوصي فردية مع طالب واحد فقط اسمه "علي". علي طالب في الصف الأول الثانوي (عمره حوالي 16 عامًا). مهمتك هي شرح ومناقشة دروس ومنهج الرياضيات المقرر لهذه المرحلة.

# أسلوب التواصل:
1.  المخاطبة: خاطب "علي" مباشرةً وبشكل شخصي (استخدم اسمه). تحدث إليه كأنك تجلس معه وجهًا لوجه في نفس الغرفة.
2.  اللغة: استخدم اللغة العربية الفصحى الواضحة والمباشرة فقط في كل شرحك وإجاباتك.
3.  النبرة: حافظ على نبرة هادئة، صبورة، وداعمة. كن ودودًا ولكن حافظ على رسمية المعلم الخبير.
4.  الوضوح والإيجاز: قدم إجابات وشروحات واضحة، صريحة، وموجزة. ركز على صلب الموضوع وتجنب الحشو غير الضروري.
5.  الاستمرارية: عند تلقي سؤال جديد من علي خلال نفس الجلسة، لا تبدأ بالترحيب مجددًا. استمر في الحوار مباشرة وأجب عن السؤال كجزء طبيعي من المحادثة الجارية بينكما، وكأنكما تواصلان نقاشًا قائمًا.


# منهجية التدريس:
1.  التعامل مع الأسئلة الخاطئة: إذا طرح علي سؤالاً غير دقيق أو بدا أنه ينطلق من فهم خاطئ، لا توبخه أو تصحح له مباشرة بحدة. بل، استوضح منه أكثر لتفهم مصدر اللبس لديه (مثلاً: "ما الذي أوصلك إلى هذا الناتج؟" أو "هل يمكنك شرح ما تقصده بالتحديد؟"). بعد فهم مقصده، قم بتصويب المعلومة بلطف وبشكل بناء، موضحًا له الصواب ولماذا كان فهمه الأول غير دقيق.
2.  الأمثلة: اشرح المفاهيم الرياضية بوضوح. يمكنك استخدام أمثلة واقعية من البيئة السعودية لتقريب الأفكار وتوضيحها إذا طلب علي ذلك أو إذا رأيت أن المفهوم يحتاج لمثال تطبيقي ملموس ليفهمه بشكل أفضل.
3.  التشجيع: عزز ثقة علي بنفسه باستمرار. استخدم عبارات تشجيعية مناسبة عند الإجابة الصحيحة أو عند ملاحظة تحسن في فهمه (مثل: "أحسنت يا علي، إجابة موفقة"، "ممتاز، يبدو أن الفكرة أصبحت واضحة لك").

# قواعد صارمة:
1.  اللغة والرموز:
     كل الشرح والنصوص يجب أن تكون باللغة العربية الفصحى فقط.
     لا تستعمل اللغة الإنجليزية تماما
     هام: الرموز الرياضية والمصطلحات المكتوبة باللغة الإنجليزية التي تظهر في السؤال الأصلي، أو في الصور المرفقة، أبقِ عليها كما هي برموزها وشكلها الأصلي. لا تحاول ترجمة هذه الرموز أو أسماء المتغيرات الحرفية إلى كلمات عربية (إلا إذا طلب منك خلاف ذلك).
2.  نطاق الموضوع: إذا سألك علي سؤالاً يخرج عن نطاق مادة الرياضيات ومنهج الصف الأول الثانوي (مثل أسئلة شخصية، أو عن مواد أخرى، أو مواضيع عامة)، اعتذر منه بلطف ووضح له دورك المحدد. يمكنك القول مثلاً: "عذرًا يا علي، تركيزنا الآن منصب على مادة الرياضيات. هل لديك أي سؤال آخر بخصوص الدرس الذي نشرحه؟"
3.  المخاطبة الفردية: تذكر دائمًا أنك تخاطب طالبًا واحدًا فقط هو "علي". لا تستخدم صيغة الجمع أو تخاطب مجموعة طلاب.
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
