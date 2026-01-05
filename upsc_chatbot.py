import streamlit as st
import os, json, time
# from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

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
# 📰 DAILY NEWS (WITH NEWSPAPER SELECTION)
# =====================================================
if mode == "📰 Daily News":

    st.subheader("📰 Daily UPSC News & Editorial Analysis")

    newspaper = st.selectbox(
        "Select Newspaper / Source",
        ["The Hindu", "Indian Express", "PIB", "All"]
    )

    if newspaper == "The Hindu":
        query = "site:thehindu.com UPSC relevant editorials India"
    elif newspaper == "Indian Express":
        query = "site:indianexpress.com UPSC relevant editorials India"
    elif newspaper == "PIB":
        query = "site:pib.gov.in important government releases UPSC"
    else:
        query = "Important UPSC current affairs India editorials"

    web = ""
    if TAVILY_ENABLED:
        try:
            r = tavily.search(query=query, max_results=5)
            web = "\n".join(i["content"] for i in r["results"])
        except:
            web = ""

    prompt = f"""
You are a UPSC mentor.

Provide DAILY UPSC-RELEVANT NEWS & EDITORIAL ANALYSIS
based on the source: {newspaper}.

Include:
- Background
- Why in news
- GS paper linkage
- Key data / facts
- Way forward

Write like a topper’s notes.

Content:
{web}
"""

    res = groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    st.write(res.choices[0].message.content)


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
if st.session_state.plan == "PREMIUM":
    st.subheader("📈 Advanced Analytics (Premium)")
    st.write("• Accuracy trends\n• Weak topic analysis\n• Improvement tracking")
else:
    st.info("Upgrade to Premium to unlock advanced analytics")

if mode == "📊 Dashboard":
    # if st.session_state.plan != "PREMIUM":
    #     st.warning("🔒 PYQ Practice with evaluation is a Premium feature.")
    #     st.stop()


    st.subheader("📊 My UPSC Practice Dashboard")

    # Load history
    with open(HISTORY_FILE) as f:
        data = json.load(f)

    user_data = data.get(st.session_state.user, [])

    if not user_data:
        st.info("No practice data available yet.")
        st.stop()

    # ---------- SUMMARY ----------
    total_attempts = len(user_data)
    prelims_attempts = [d for d in user_data if d.get("type") == "prelims"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Practice Sessions", total_attempts)
    with col2:
        st.metric("Prelims Tests Taken", len(prelims_attempts))

    st.markdown("---")

    # ---------- PRELIMS PERFORMANCE ----------
    if prelims_attempts:
        st.subheader("🧪 Prelims Performance")

        scores = [d["score"] for d in prelims_attempts]
        avg_score = round(sum(scores) / len(scores), 2)

        st.metric("Average Prelims Score", avg_score)

        st.markdown("Recent Prelims Attempts:")
        for d in prelims_attempts[-5:][::-1]:
            st.write(f"• **Topic:** {d['topic']} | **Score:** {round(d['score'],2)}")

        st.markdown("---")

    # ---------- TOPIC-WISE ANALYSIS ----------
    st.subheader("📘 Topic-wise Practice")

    topic_map = {}
    for d in user_data:
        topic = d.get("topic")
        if topic:
            topic_map[topic] = topic_map.get(topic, 0) + 1

    for topic, count in sorted(topic_map.items(), key=lambda x: x[1], reverse=True):
        st.write(f"🔹 **{topic}** → {count} session(s)")

    st.markdown("---")

    # ---------- RAW HISTORY (OPTIONAL VIEW) ----------
    with st.expander("📋 View Full Practice History"):
        for i, d in enumerate(user_data, start=1):
            st.write(f"{i}. {d}")

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



