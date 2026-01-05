import streamlit as st
import os
from datetime import date
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI UPSC Mentor", layout="wide")
st.title("🏛️ AI UPSC Mentor (FREE – LIVE WEB)")

# ---------------- SECURITY CHECK ----------------
if not os.getenv("GROQ_API_KEY") or not os.getenv("TAVILY_API_KEY"):
    st.error("❌ Server configuration error. Please contact admin.")
    st.stop()

# ---------------- CLIENTS ----------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "email" not in st.session_state:
    st.session_state.email = ""

if "questions_today" not in st.session_state:
    st.session_state.questions_today = 0

if "last_date" not in st.session_state:
    st.session_state.last_date = str(date.today())

# ---------------- LOGIN SCREEN ----------------
if not st.session_state.logged_in:
    st.subheader("🔐 Login to continue")

    name = st.text_input("Your Name")
    email = st.text_input("Email ID")

    if st.button("Login"):
        if name and email:
            st.session_state.logged_in = True
            st.session_state.username = name
            st.session_state.email = email
            st.success(f"Welcome {name} 👋")
            st.rerun()
        else:
            st.warning("Please enter both name and email")

    st.stop()

# ---------------- DAILY LIMIT RESET ----------------
today = str(date.today())
if st.session_state.last_date != today:
    st.session_state.questions_today = 0
    st.session_state.last_date = today

DAILY_LIMIT = 5

st.info(
    f"👤 {st.session_state.username} | "
    f"Questions today: {st.session_state.questions_today}/{DAILY_LIMIT}"
)

# ---------------- LANGUAGE SELECTOR ----------------
language = st.radio(
    "🌐 Select Language",
    ["English", "हिंदी"],
    horizontal=True
)

if language == "English":
    lang_instruction = "Answer strictly in formal UPSC-level English."
else:
    lang_instruction = "उत्तर सरल, स्पष्ट और UPSC-उपयुक्त हिंदी में दीजिए।"

# ---------------- MODE SELECTOR ----------------
mode = st.radio(
    "📘 Select Mode",
    ["GS (Mains/Prelims)", "Current Affairs", "Interview (Personality Test)"],
    horizontal=True
)

# ---------------- PROMPTS ----------------
GS_PROMPT = f"""
You are a senior UPSC General Studies mentor.

Rules:
- Stick strictly to UPSC syllabus
- Answer in Introduction, Body, Conclusion format
- Use Constitution articles, committees, examples
- Avoid unnecessary theory
- Write like a topper answer
{lang_instruction}
"""

CA_PROMPT = f"""
You are a UPSC current affairs expert.

Rules:
- Explain issue with background
- Link to GS paper (GS2/GS3/GS1)
- Include recent developments
- Use bullet points
- End with way forward
{lang_instruction}
"""

INTERVIEW_PROMPT = f"""
You are a UPSC interview board member.

Rules:
- Ask 3–5 interview questions
- Include follow-up questions
- Test ethics, opinion, clarity
- Keep tone polite but probing
{lang_instruction}
"""

# ---------------- QUESTION UI ----------------
question = st.text_input("Ask your question")

if st.button("Ask") and question:
    if st.session_state.questions_today >= DAILY_LIMIT:
        st.error("❌ Daily limit reached. Please come back tomorrow.")
        st.stop()

    st.session_state.questions_today += 1

    with st.spinner("Analyzing and preparing UPSC-level response..."):

        # Web search only for GS & Current Affairs
        web_content = ""
        if mode != "Interview (Personality Test)":
            search_results = tavily_client.search(
                query=question,
                search_depth="advanced",
                include_domains=[
                    "pib.gov.in",
                    "prsindia.org",
                    "gov.in",
                    "niti.gov.in",
                    "un.org",
                    "worldbank.org",
                    "wikipedia.org"
                ],
                max_results=5
            )

            web_content = "\n".join(
                item["content"] for item in search_results.get("results", [])
            )

        # Select prompt
        if mode == "GS (Mains/Prelims)":
            system_prompt = GS_PROMPT
        elif mode == "Current Affairs":
            system_prompt = CA_PROMPT
        else:
            system_prompt = INTERVIEW_PROMPT

        final_prompt = f"""
{system_prompt}

Question:
{question}

Relevant public information:
{web_content}

Response:
"""

        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.3
        )

        answer = completion.choices[0].message.content

        st.success("Answer")
        st.write(answer)
