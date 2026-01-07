import streamlit as st
import os, json, time
# from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient
from fpdf import FPDF
import reportlab
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
from streamlit_mic_recorder import mic_recorder

def voice_input(key):
    audio = mic_recorder(
        start_prompt="🎤 Speak",
        stop_prompt="⏹ Stop",
        just_once=True,
        key=key
    )
    if audio and "text" in audio:
        return audio["text"]
    return ""




# 🔍 DEBUG (TEMPORARY)
# st.write("GROQ:", os.getenv("GROQ_API_KEY"))

# st.write("ENV KEY PRESENT:", bool(os.getenv("GROQ_API_KEY")))
# st.write("KEY VALUE:", os.getenv("GROQ_API_KEY"))
# st.stop()

# ================= LOAD ENV =================

# load_dotenv()

# ================= CONFIG =================
st.set_page_config(page_title="AI UPSC Mentor", layout="wide")
st.title("🏛️ AI UPSC Mentor – Complete UPSC Preparation Platform")

# ================= KEYS =================
if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ API key missing")
    st.stop()

TAVILY_ENABLED = bool(os.getenv("TAVILY_API_KEY"))

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY")) if TAVILY_ENABLED else None

# ================= STORAGE =================
HISTORY_FILE = "user_history.json"
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump({}, f)

def save_history(user, entry):
    with open(HISTORY_FILE, "r") as f:
        data = json.load(f)
    data.setdefault(user, []).append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ================= PLAN STORAGE =================
PLAN_FILE = "user_plans.json"

if not os.path.exists(PLAN_FILE):
    with open(PLAN_FILE, "w") as f:
        json.dump({}, f)

def get_user_plan(email):
    with open(PLAN_FILE) as f:
        plans = json.load(f)
    return plans.get(email, "FREE")

def save_user_plan(email, plan):
    with open(PLAN_FILE) as f:
        plans = json.load(f)
    plans[email] = plan
    with open(PLAN_FILE, "w") as f:
        json.dump(plans, f, indent=2)


# ================= SAFE JSON EXTRACTOR =================
def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end+1])
    except json.JSONDecodeError:
        return None

# ================= LOGIN =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔐 Login")
    name = st.text_input("Name")
    email = st.text_input("Email")
    plan = st.radio("Plan", ["FREE", "PREMIUM"])

    if st.button("Login"):
        if name and email:
            st.session_state.logged_in = True
            st.session_state.user = email
            st.session_state.plan = get_user_plan(email)
            st.rerun()
    st.stop()

# ================= PLAN BADGE =================
# if st.session_state.plan == "PREMIUM":
#     st.success("🌟 PREMIUM ACCESS ENABLED")
# else:
#     st.info("🔓 Free Plan – Limited Access")


# ================= MODE =================
mode = st.sidebar.radio(
    "Select Section",
    [
        "💬 Ask Anything (UPSC AI Chat)",
        "📝 Make UPSC Notes",
        "🧠 Ask UPSC Syllabus",
        "🧪 Prelims Practice",
        "📘 Mains Practice",
        "📜 Previous Year Papers (PYQs)",
        "📝 PYQ Practice",
        "📚 GS Full-Length Mocks",
        "📰 Daily News",
        "🗓️ Monthly Current Affairs",
        "🎤 Interview",
        "📊 Dashboard",
        "📚 UPSC Syllabus",
        # "💳 Upgrade to Premium"

    ]
)


# =====================================================
# 💬 ASK ANYTHING – UPSC AI CHAT (UNIVERSAL)
# =====================================================
if mode == "💬 Ask Anything (UPSC AI Chat)":

    st.header("💬 Ask Anything – UPSC AI Mentor")
    st.caption(
        "Ask any doubt, topic, strategy, or concept.\n"
        "This works like ChatGPT but answers ONLY in UPSC-focused depth."
    )

    # user_query = st.text_area(
    #     "✍️ Ask your question",
    #     placeholder=(
    #         "Examples:\n"
    #         "- Explain inflation for Prelims + Mains\n"
    #         "- How to prepare GS Paper 2 effectively?\n"
    #         "- Difference between FRs and DPSPs with cases\n"
    #         "- Ethics case study approach\n"
    #         "- Best strategy for first attempt UPSC aspirant"
    #     ),
    #     height=180
    # )
     
    
    voice_text = voice_input("chat_voice")

    user_query = st.text_area(
          "✍️ Ask your question",
           value=voice_text,
           height=180
)


    if st.button("🚀 Get Detailed Answer"):
        if not user_query.strip():
            st.warning("Please enter a question.")
            st.stop()

        prompt = f"""
You are a senior UPSC mentor and topper.

Answer the following query in a VERY DETAILED and STRUCTURED manner:

"{user_query}"

Your answer MUST include:
1. Concept explanation (simple → advanced)
2. UPSC syllabus linkage (Prelims / Mains / GS Paper)
3. Important subtopics
4. Examples (India + current relevance)
5. Previous Year Questions (if applicable)
6. Answer writing / preparation tips

Write like UPSC topper notes.
Use headings and bullet points.
Avoid unnecessary fluff.
"""

        with st.spinner("Thinking like a UPSC mentor..."):
            res = groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

        st.markdown("## 📘 Detailed UPSC Answer")
        st.write(res.choices[0].message.content)


# =====================================================
# 📝 MAKE UPSC NOTES (ASK → NOTES → DOWNLOAD)
# =====================================================
if mode == "📝 Make UPSC Notes":

    st.header("📝 AI UPSC Notes Maker")
    st.caption("Ask anything → Get deep UPSC notes → Download")

    # topic = st.text_input(
    #     "📌 Topic / Area",
    #     placeholder="Example: Inflation, Parliament, Ethics case studies"
    # )

    voice_text = voice_input("notes_voice")

    user_query = st.text_area(
         "✍️ What exactly do you want to know?",
         value=voice_text,
         height=160
)


    # user_query = st.text_area(
    #     "✍️ What exactly do you want to know?",
    #     placeholder=(
    #         "Example:\n"
    #         "Explain inflation for Prelims + Mains.\n"
    #         "Include causes, types, PYQs and answer-writing tips."
    #     ),
    #     height=160
    # )

    voice_text = voice_input("chat_voice")

    user_query = st.text_area(
         "✍️ Ask your question",
         value=voice_text,
         height=180
)


    if st.button("📚 Generate UPSC Notes"):
        if not topic or not user_query.strip():
            st.warning("Please enter topic and your question.")
            st.stop()

        prompt = f"""
You are a senior UPSC mentor.

Create HIGH-QUALITY UPSC NOTES on:

Topic: {topic}
Student Requirement: {user_query}

FORMAT STRICTLY AS UPSC NOTES:
- Clear headings
- Bullet points
- Simple + deep explanation
- Prelims facts
- Mains-ready analysis
- Examples (India + current relevance)
- PYQ reference (if applicable)
- Answer writing tips

Make notes revision-friendly.
Avoid unnecessary fluff.
"""

        with st.spinner("Creating topper-level notes..."):
            res = groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

        notes_text = res.choices[0].message.content

        # Save in session
        st.session_state.generated_notes = notes_text
        st.session_state.notes_topic = topic

        st.markdown("## 📘 Generated UPSC Notes")
        st.write(notes_text)

    # ================= DOWNLOAD NOTES =================
    if "generated_notes" in st.session_state:
        st.markdown("---")

        st.download_button(
            label="⬇️ Download Notes (TXT)",
            data=st.session_state.generated_notes,
            file_name=f"{st.session_state.notes_topic.replace(' ', '_')}_UPSC_Notes.txt",
            mime="text/plain"
        )


# =====================================================
# 🧠 ASK UPSC SYLLABUS (AI DEEP EXPLAINER)
# =====================================================
if mode == "🧠 Ask UPSC Syllabus":

    st.header("🧠 Ask Anything About UPSC Syllabus")
    st.caption("Type any topic, paper, or doubt — get deep UPSC-level clarity")

    user_query = st.text_area(
        "✍️ Ask your question (GS, Prelims, Mains, Optional, Strategy, etc.)",
        placeholder="Example: Explain GS Paper 2 – Parliament vs Executive with examples and PYQ relevance",
        height=120
    )

    if st.button("🔍 Explain in Depth"):
        if not user_query.strip():
            st.warning("Please type a question first.")
            st.stop()

        prompt = f"""
You are a senior UPSC mentor.

Explain the following query in DEPTH for a UPSC aspirant:

"{user_query}"

STRUCTURE YOUR ANSWER AS:
1. Concept clarity (simple + deep)
2. Syllabus linkage (Prelims / Mains / GS Paper)
3. Important subtopics
4. Examples (India + current relevance)
5. Previous Year Question (if applicable)
6. How to prepare this topic effectively

Use clear headings and bullet points.
Avoid fluff. Write like topper notes.
"""

        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        st.markdown("### 📘 Detailed Explanation")
        st.write(res.choices[0].message.content)


# =====================================================
# 🧪 PRELIMS PRACTICE
# =====================================================
# if st.session_state.plan == "FREE":
#     st.warning("🔓 Free users can attempt limited Prelims tests per day.")

if mode == "🧪 Prelims Practice":
    topic = st.text_input("Enter Topic")

    if st.button("Start Prelims Test"):
        prompt = f"""
Return ONLY valid JSON. No extra text.

You are a UPSC Prelims paper setter.

Generate 10–15 HIGH-QUALITY UPSC Prelims MCQs on "{topic}".

RULES:
- Analytical, not definition-based
- Indian economy / polity / current relevance
- All options must be meaningful
- One correct answer only

JSON FORMAT:
{{
 "questions":[
  {{
   "id":1,
   "question":"UPSC-level analytical question",
   "options": {{
     "A":"Meaningful option",
     "B":"Meaningful option",
     "C":"Meaningful option",
     "D":"Meaningful option"
   }},
   "correct":"A",
   "explanation":"Why A is correct"
  }}
 ]
}}
"""

        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        raw_output = res.choices[0].message.content.strip()
        data = extract_json(raw_output)

        if not data or "questions" not in data:
            st.error("⚠️ AI response not usable. Please click Start Prelims Test again.")
            st.stop()

        # Remove questions with empty options
        clean_mcqs = []
        for q in data ["questions"]:
            if all(q["options"].get(opt, "").strip() for opt in ["A", "B", "C", "D"]):
                clean_mcqs.append(q)

        if not clean_mcqs:
            st.error("⚠️ Generated questions were not UPSC quality. Please regenerate.")
            st.stop()

        st.session_state.mcqs = clean_mcqs
        st.session_state.answers = {}
        st.session_state.done = False
        st.rerun()

    if "mcqs" in st.session_state and not st.session_state.done:
        for q in st.session_state.mcqs:
            st.markdown(f"**Q{q['id']}. {q['question']}**")
            option_map = {
                 f"A. {q['options']['A']}": "A",
                 f"B. {q['options']['B']}": "B",
                 f"C. {q['options']['C']}": "C",
                 f"D. {q['options']['D']}": "D",
            }

            selected = st.radio(
                 "Choose one option",
                  list(option_map.keys()),
                  key=f"q_{q['id']}"
            )

            st.session_state.answers[q["id"]] = option_map[selected]


        if st.button("Submit"):
            correct, wrong = 0, 0
            for q in st.session_state.mcqs:
                if st.session_state.answers[q["id"]] == q["correct"]:
                    correct += 1
                else:
                    wrong += 1

            score = correct * 2 - wrong * 0.66
            st.success(f"Score: {round(score, 2)}")

            for q in st.session_state.mcqs:
                st.info(f"{q['correct']} → {q['explanation']}")

            save_history(
                st.session_state.user,
                {"type": "prelims", "topic": topic, "score": score}
            )
            st.session_state.done = True

# =====================================================
# 📘 MAINS PRACTICE
# =====================================================
if mode == "📘 Mains Practice":
    q = st.text_input("Enter GS Question")
    if st.button("Get Model Answer"):
        prompt = f"""
Write a UPSC GS answer with:
- Introduction
- Body (analysis, examples)
- Conclusion (way forward)

Question:
{q}
"""
        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        st.write(res.choices[0].message.content)


# =====================================================
# 📜 PREVIOUS YEAR PAPERS (PRELIMS + MAINS)
# =====================================================
if mode == "📜 Previous Year Papers (PYQs)":

    st.header("📜 UPSC Previous Year Question Papers")

    exam = st.selectbox(
        "Select Examination",
        ["Preliminary Examination", "Mains Examination"]
    )

    year = st.selectbox(
        "Select Year",
        [str(y) for y in range(2024, 1994, -1)]
    )

    # ================= PRELIMS =================
    if exam == "Preliminary Examination":

        paper = st.selectbox(
            "Select Paper",
            [
                "GS Paper I (General Studies)",
                "CSAT Paper II"
            ]
        )

        # -------- PRELIMS GS PAPER I --------
        if paper == "GS Paper I (General Studies)":

            st.subheader(f"🧪 UPSC Prelims {year} – GS Paper I")

            if st.button("Generate FULL Question Paper"):
                q_prompt = f"""
Generate the COMPLETE UPSC Prelims {year} GS Paper I.

Rules:
- Exactly 100 MCQs
- 4 options (A–D)
- Do NOT include answers
"""
                res = groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": q_prompt}],
                    temperature=0.2
                )
                st.session_state.prelims_gs_qp = res.choices[0].message.content
                st.write(st.session_state.prelims_gs_qp)

            if "prelims_gs_qp" in st.session_state:
                if st.button("Show Answer Key & Explanations"):
                    a_prompt = f"""
Provide FULL answer key with explanations
for UPSC Prelims {year} GS Paper I.
"""
                    ans = groq.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": a_prompt}],
                        temperature=0.2
                    )
                    st.subheader("📘 Answer Key & Explanations")
                    st.write(ans.choices[0].message.content)

        # -------- PRELIMS CSAT PAPER II --------
        # if st.session_state.plan != "PREMIUM":
        #      st.warning("🔒 CSAT full papers are available for Premium users only.")
        #      st.stop()

        if paper == "CSAT Paper II":
                # if st.session_state.plan != "PREMIUM":
                #     st.warning("🔒 CSAT Paper II is available for Premium users only.")
                #     st.stop()


                    st.subheader(f"🧪 UPSC Prelims {year} – CSAT (Paper II)")

        if st.button("Generate FULL CSAT Paper"):
                q_prompt = f"""
Generate the COMPLETE UPSC Prelims {year} CSAT Paper II.

Rules:
- Exactly 80 questions
- Focus on comprehension, reasoning, numeracy
- Do NOT include answers
"""
                res = groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": q_prompt}],
                    temperature=0.2
                )
                st.session_state.csat_qp = res.choices[0].message.content
                st.write(st.session_state.csat_qp)

        if "csat_qp" in st.session_state:
                if st.button("Show CSAT Answer Key"):
                    a_prompt = f"""
Provide FULL answer key with explanations
for UPSC Prelims {year} CSAT Paper II.
"""
                    ans = groq.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": a_prompt}],
                        temperature=0.2
                    )
                    st.subheader("📘 CSAT Answer Key & Explanations")
                    st.write(ans.choices[0].message.content)

    # ================= MAINS =================
    if exam == "Mains Examination":

        paper = st.selectbox(
            "Select Paper",
            [
                "GS Paper 1",
                "GS Paper 2",
                "GS Paper 3",
                "GS Paper 4 (Ethics)",
                "Essay"
            ]
        )

        st.subheader(f"📘 UPSC Mains {year} – {paper}")

        if st.button("Generate FULL Question Paper"):
            q_prompt = f"""
Generate the COMPLETE UPSC Mains {year} {paper} question paper.

Rules:
- Include ALL questions
- Mention marks
- Do NOT include answers
"""
            res = groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": q_prompt}],
                temperature=0.2
            )
            st.session_state.mains_qp = res.choices[0].message.content
            st.write(st.session_state.mains_qp)

        if "mains_qp" in st.session_state:
            if st.button("Show Model Answer Pointers"):
                a_prompt = f"""
Provide MODEL ANSWER POINTERS
for UPSC Mains {year} {paper}.
"""
                ans = groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": a_prompt}],
                    temperature=0.2
                )
                st.subheader("📘 Model Answer Pointers")
                st.write(ans.choices[0].message.content)



# =====================================================
# 📝 PYQ PRACTICE
# =====================================================
if mode == "📝 PYQ Practice":
    # if st.session_state.plan != "PREMIUM":
    #       st.warning("🔒 CSAT Paper II is available for Premium users only.")
    #       st.stop()

    topic = st.text_input("Enter Topic")
    if st.button("Generate PYQs"):
        prompt = f"Generate 3 UPSC Mains PYQ-style questions on {topic}"
        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        st.write(res.choices[0].message.content)

# =====================================================
# 📚 GS FULL-LENGTH MOCKS (GS-4 ENHANCED)
# =====================================================
# if st.session_state.plan != "PREMIUM":
#     st.warning("🔒 CSAT full papers are available for Premium users only.")
#     st.stop()

if mode == "📚 GS Full-Length Mocks":
    # if st.session_state.plan != "PREMIUM":
    #        st.warning("🔒 Full-length GS mocks are available for Premium users only.")
    #        st.stop()


    paper = st.selectbox(
        "Select GS Paper",
        ["GS-1", "GS-2", "GS-3", "GS-4"]
    )

    exam_type = st.radio("Select Exam Type", ["Mains", "Preliminary"])
    topic = st.text_input("Enter Topic (optional, leave blank for full syllabus)")

    if st.button("Start Mock"):

        # ================= GS-4 MAINS =================
        if paper == "GS-4" and exam_type == "Mains":
            prompt = f"""
You are a UPSC Ethics (GS-4) examiner.

Generate a FULL-LENGTH UPSC GS-4 MAINS mock paper.

STRICT UPSC PATTERN:
Section A:
- 6 short theory questions (10 marks each)
- Ethics, integrity, aptitude, attitude, emotional intelligence

Section B:
- 4 CASE STUDIES (20 marks each)
- Realistic administrative situations
- Moral dilemmas, conflict of interest, probity in governance

Rules:
- Use UPSC GS-4 language
- Ask analytical questions, not definitions
- If topic is provided, give extra focus to that area

Topic focus: {topic if topic else "Full GS-4 syllabus"}

Only output questions. No answers.
"""

        # ================= GS-4 PRELIMS =================
        # if paper == "GS-4" and st.session_state.plan != "PREMIUM":
        #      st.warning("🔒 GS-4 Ethics is a Premium feature.")
        #      st.stop()

        elif paper == "GS-4" and exam_type == "Preliminary":
            prompt = f"""
You are a UPSC Prelims Ethics question setter.

Generate a FULL-LENGTH UPSC GS-4 PRELIMINARY mock paper.

Requirements:
- 20–25 MCQs
- Ethics, values, attitude, integrity, public service
- Situational judgement based questions
- 4 options (A–D) each
- One correct answer only

FORMAT STRICTLY LIKE THIS:

Q1. Question text
A) Option text
B) Option text
C) Option text
D) Option text

--- Answer Key ---
1. B
2. D
3. A

Topic focus: {topic if topic else "Full GS-4 syllabus"}
"""

        # ================= OTHER GS PAPERS =================
        else:
            if exam_type == "Mains":
                prompt = f"""
You are a UPSC examiner.

Generate a FULL-LENGTH UPSC {paper} MAINS mock paper.

Requirements:
- 10–12 descriptive questions
- Mix of 10, 15 and 20 mark questions
- Cover full syllabus
- UPSC language
- If topic is provided, give extra weight to it

Topic focus: {topic if topic else "Full syllabus"}

Only output questions. No answers.
"""
            else:
                prompt = f"""
You are a UPSC Prelims paper setter.

Generate a FULL-LENGTH UPSC {paper} PRELIMINARY mock paper.

Requirements:
- 20–25 MCQs
- Analytical UPSC level
- 4 options (A–D)
- One correct answer
- Answer key at the end

FORMAT:

Q1. Question
A) ...
B) ...
C) ...
D) ...

--- Answer Key ---
1. C
2. A

Topic focus: {topic if topic else "Full syllabus"}
"""

        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        st.subheader(f"{paper} {exam_type} Mock Paper")
        st.write(res.choices[0].message.content)


# =====================================================
# 📰 DAILY NEWS (WITH DATE + NEWSPAPER + DEEP DIVE)
# =====================================================
if mode == "📰 Daily News":

    from datetime import date

    st.subheader("📰 Daily UPSC News & Editorial Analysis")

    # 📅 Date selector
    news_date = st.date_input(
        "Select Date",
        value=date.today()
    )

    # 🗞️ Newspaper selector
    newspaper = st.selectbox(
        "Select Newspaper / Source",
        ["The Hindu", "Indian Express", "PIB", "All"]
    )

    # ✅ Show selected info clearly
    st.markdown(
        f"### 🗞️ Source: **{newspaper}** | 📅 Date: **{news_date.strftime('%d %B %Y')}**"
    )

    # 🔎 Search query
    if newspaper == "The Hindu":
        query = f"site:thehindu.com UPSC editorials {news_date}"
    elif newspaper == "Indian Express":
        query = f"site:indianexpress.com UPSC editorials {news_date}"
    elif newspaper == "PIB":
        query = f"site:pib.gov.in government releases {news_date}"
    else:
        query = f"UPSC current affairs India {news_date}"

    # 🌐 Fetch news
    web = ""
    if TAVILY_ENABLED:
        try:
            r = tavily.search(query=query, max_results=15)
            web = "\n".join(i["content"] for i in r["results"])
        except:
            web = ""

    # 🧠 MAIN DAILY NEWS PROMPT
    prompt = f"""
You are a SENIOR UPSC FACULTY preparing DAILY CURRENT AFFAIRS NOTES
for serious CSE aspirants.

SOURCE: {newspaper}
DATE: {news_date.strftime('%d %B %Y')}

You MUST prepare **10–15 DISTINCT UPSC-RELEVANT TOPICS**.

For EACH topic include:
• Why in News  
• Background / Context  
• GS Paper & Syllabus Linkage  
• Key Facts / Data  
• Mains Perspective (Issues + Way Forward)  
• Prelims Pointers  

Write detailed topper-style notes.
Bullet points only.

CONTENT SOURCE:
{web}
"""

    res = groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    daily_notes = res.choices[0].message.content
    st.markdown("## 📘 Daily UPSC Current Affairs Notes")
    st.write(daily_notes)

    # =====================================================
    # 🔍 DEEP DIVE INTO A PARTICULAR TOPIC
    # =====================================================
    st.markdown("---")
    st.subheader("🔍 Deep Dive into a Particular Topic")

    deep_topic = st.text_input(
        "Enter topic name exactly as shown above",
        placeholder="Example: Supreme Court on Electoral Bonds"
    )

    if st.button("📖 Explain This Topic in Depth"):
        if not deep_topic.strip():
            st.warning("Please enter a topic name.")
            st.stop()

        deep_prompt = f"""
You are a senior UPSC mentor.

SOURCE: {newspaper}
DATE: {news_date.strftime('%d %B %Y')}
TOPIC: {deep_topic}

Explain this topic in FULL UPSC DEPTH with:
1. Background & context
2. Constitutional / legal / economic dimensions
3. Current relevance
4. GS Paper & syllabus mapping
5. Previous Year Questions
6. Mains answer framework
7. Prelims facts
8. Way forward

Write like topper notes.
Use headings & bullet points.
"""

        deep_res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": deep_prompt}],
            temperature=0.3
        )

        st.markdown("### 📚 Detailed Topic Analysis")
        st.write(deep_res.choices[0].message.content)




# =====================================================
# 🗓️ MONTHLY CURRENT AFFAIRS (WITH YEAR SELECTION)
# =====================================================
if mode == "🗓️ Monthly Current Affairs":

    col1, col2 = st.columns(2)

    with col1:
        month = st.selectbox(
            "Select Month",
            [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
        )

    with col2:
        year = st.selectbox(
            "Select Year",
            ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]
        )

    prompt = f"""
You are a UPSC current affairs expert.

Prepare MONTHLY CURRENT AFFAIRS notes for:
Month: {month}
Year: {year}

Requirements:
- UPSC-focused
- GS-wise segregation (GS-1, GS-2, GS-3, GS-4)
- Cover major national & international events
- Include data, examples, and prelims pointers
- Add mains-ready analysis and way forward

Write in concise topper-style notes.
"""

    res = groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    st.subheader(f"📚 Monthly Current Affairs – {month} {year}")
    st.write(res.choices[0].message.content)


# =====================================================
# 🎤 INTERVIEW
# =====================================================
if mode == "🎤 Interview":
    bg = st.text_input("Background")
    if st.button("Generate Questions"):
        prompt = f"Generate UPSC interview questions with follow-ups.\n{bg}"
        res = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        st.write(res.choices[0].message.content)

# =====================================================
# 📊 DASHBOARD (CORRECTED & READABLE)
# =====================================================
# if st.session_state.plan == "PREMIUM":
#     st.subheader("📈 Advanced Analytics (Premium)")
#     st.write("• Accuracy trends\n• Weak topic analysis\n• Improvement tracking")
# else:
#     st.info("Upgrade to Premium to unlock advanced analytics")


if mode == "📊 Dashboard":

    st.header("📊 My UPSC Practice Dashboard")

    # Load history ONLY here
    with open(HISTORY_FILE) as f:
        data = json.load(f)

    user_data = data.get(st.session_state.user, [])

    if not user_data:
        st.info("No activity yet. Start practicing!")
        st.stop()

    # ---------------- SUMMARY ----------------
    prelims_attempts = [d for d in user_data if d.get("type") == "prelims"]
    notes_data = [d for d in user_data if d.get("type") == "notes"]

    col1, col2 = st.columns(2)
    col1.metric("Prelims Tests Taken", len(prelims_attempts))
    col2.metric("Saved UPSC Notes", len(notes_data))

    st.markdown("---")

    # ---------------- SAVED UPSC NOTES ----------------
    st.subheader("📝 My Saved UPSC Notes")

    if not notes_data:
        st.info("No notes created yet.")
    else:
        for i, note in enumerate(notes_data[::-1], 1):
            with st.expander(f"{i}. 📘 {note.get('topic', 'UPSC Notes')}"):
                st.write(note["content"])

    st.markdown("---")

    # ---------------- PRELIMS PERFORMANCE ----------------
    if prelims_attempts:
        st.subheader("🧪 Recent Prelims Practice")

        for p in prelims_attempts[-5:][::-1]:
            st.write(
                f"• **{p['topic']}** | Score: {round(p['score'], 2)}"
            )

    st.markdown("---")

    # ---------------- FULL ACTIVITY LOG ----------------
    with st.expander("📋 View Full Activity History"):
        for i, d in enumerate(user_data, start=1):
            st.write(f"{i}. {d}")



# st.subheader("📝 My Saved UPSC Notes")

# notes_data = [d for d in user_data if d.get("type") == "notes"]

# if not notes_data:
#     st.info("No notes created yet.")
# else:
#     for n in notes_data[::-1][:5]:
#         with st.expander(f"📘 {n['topic']} ({n['paper']})"):
#             st.write(n["content"])

# =====================================================
# 📚 UPSC SYLLABUS (COMPLETE – PRELIMS + MAINS + OPTIONAL)
# =====================================================
if mode == "📚 UPSC Syllabus":

    st.header("📚 UPSC Civil Services Examination – Complete Syllabus")

    syllabus_type = st.radio(
        "Select Syllabus Section",
        [
            "Prelims – Paper I & Paper II (CSAT)",
            "Mains – GS Paper 1",
            "Mains – GS Paper 2",
            "Mains – GS Paper 3",
            "Mains – GS Paper 4 (Ethics)",
            "Essay Paper",
            "Optional Subject (Overview)"
        ]
    )

    # ================= PRELIMS =================
    if syllabus_type == "Prelims – Paper I & Paper II (CSAT)":
        st.markdown("""
## 🧪 PRELIMINARY EXAMINATION  
**Total Papers:** 2  
**Total Marks:** 400  

---

### 📘 Paper I – General Studies  
**Marks:** 200  
**Nature:** Objective  

- **Current Events**
  - National & International importance

- **History of India**
  - Ancient
  - Medieval
  - Modern
  - Indian National Movement

- **Indian & World Geography**
  - Physical Geography
  - Human Geography
  - Economic Geography
  - Geography of India

- **Indian Polity & Governance**
  - Constitution
  - Political System
  - Panchayati Raj
  - Public Policy
  - Rights Issues

- **Economic & Social Development**
  - Sustainable Development
  - Poverty
  - Inclusion
  - Demographics
  - Social Sector Initiatives

- **Environment & Ecology**
  - Biodiversity
  - Climate Change
  - Environmental Ecology

- **General Science**

---

### 📗 Paper II – CSAT (Qualifying)  
**Marks:** 200  
**Qualifying Marks:** 33%  
**Nature:** Objective  

- **Comprehension**
- **Interpersonal Skills**
- **Logical Reasoning & Analytical Ability**
- **Decision Making & Problem Solving**
  - No negative marking
- **General Mental Ability**
- **Basic Numeracy (Class X level)**
  - Numbers
  - Percentages
  - Ratio & Proportion
  - Time & Work
  - Time & Distance
- **Data Interpretation**
  - Charts
  - Tables
  - Graphs
""")

    # ================= GS PAPER 1 =================
    elif syllabus_type == "Mains – GS Paper 1":
        st.markdown("""
## 📘 MAINS – GENERAL STUDIES PAPER I  
**Marks:** 250  
**Nature:** Descriptive  

- Indian Culture (Art Forms, Literature, Architecture)
- Modern Indian History (1750–1947)
- World History (18th century onwards)
- Indian Society
  - Diversity
  - Role of Women
  - Population & Urbanization
- Physical Geography
- Geography of India
- Distribution of Natural Resources
""")

    # ================= GS PAPER 2 =================
    elif syllabus_type == "Mains – GS Paper 2":
        st.markdown("""
## 📘 MAINS – GENERAL STUDIES PAPER II  
**Marks:** 250  
**Nature:** Descriptive  

- Indian Constitution
- Parliament & State Legislatures
- Executive & Judiciary
- Governance
- Transparency & Accountability
- E-Governance
- Social Justice
  - Health
  - Education
  - Human Resources
- International Relations
""")

    # ================= GS PAPER 3 =================
    elif syllabus_type == "Mains – GS Paper 3":
        st.markdown("""
## 📘 MAINS – GENERAL STUDIES PAPER III  
**Marks:** 250  
**Nature:** Descriptive  

- Indian Economy
- Agriculture
- Science & Technology
- Environment
- Disaster Management
- Internal Security
  - Terrorism
  - Cyber Security
  - Border Management
""")

    # ================= GS PAPER 4 =================
    elif syllabus_type == "Mains – GS Paper 4 (Ethics)":
        st.markdown("""
## 📘 MAINS – GENERAL STUDIES PAPER IV (ETHICS)  
**Marks:** 250  
**Nature:** Descriptive + Case Studies  

- Ethics & Human Interface
- Attitude
- Aptitude & Foundational Values
- Emotional Intelligence
- Moral Thinkers
- Public/Civil Service Values
- Probity in Governance
- Case Studies on Ethical Dilemmas
""")

    # ================= ESSAY =================
    elif syllabus_type == "Essay Paper":
        st.markdown("""
## ✍️ ESSAY PAPER  
**Marks:** 250  
**Nature:** Descriptive  

- Two essays to be written
- Topics may be:
  - Philosophical
  - Social
  - Political
  - Economic
  - Ethical
- Emphasis on:
  - Coherence
  - Relevance
  - Structure
  - Originality
""")

    # ================= OPTIONAL =================
    elif syllabus_type == "Optional Subject (Overview)":
        st.markdown("""
## 📖 OPTIONAL SUBJECT  
**Papers:** Paper I & Paper II  
**Marks:** 500  

- One optional subject to be chosen
- Two descriptive papers
- Detailed syllabus as per UPSC notification
""")


# # =====================================================
# # 💳 UPGRADE TO PREMIUM
# # =====================================================
# if mode == "💳 Upgrade to Premium":

#     st.header("🌟 Upgrade to PREMIUM")

#     st.markdown("""
# ## Premium Benefits:
# ✅ Unlimited Prelims Tests  
# ✅ CSAT Full Papers  
# ✅ GS Full-Length Mocks  
# ✅ GS-4 Ethics Case Studies  
# ✅ PYQ Practice + Evaluation  
# ✅ Advanced Dashboard Analytics  
# # """)

#     st.markdown("### 💰 Price: ₹999 / year")

#     if st.button("Upgrade Now"):
#         save_user_plan(st.session_state.user, "PREMIUM")
#         st.session_state.plan = "PREMIUM"
#         st.success("🎉 You are now a PREMIUM user!")
#         st.balloons()
#         st.rerun()



