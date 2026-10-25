import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import io
import docx

# Page Configuration
st.set_page_config(page_title="Resume & Cover Letter Tailorer", page_icon="📄", layout="wide")

st.title("📄 Resume & Cover Letter Customizer")
st.caption("Automatically tailor your resume and cover letter to match any job description.")

# Helper to automatically fetch whatever models Groq currently has active
@st.cache_data(show_spinner=False, ttl=300)
def fetch_groq_models(key):
    try:
        temp_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        models = [
            m.id for m in temp_client.models.list().data 
            if not any(skip in m.id for skip in ["whisper", "guard", "tts", "vision"])
        ]
        return models if models else ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    except Exception:
        return ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "API Key (OpenAI or Free Groq)", 
        type="password", 
        help="Paste an OpenAI key (sk-...) or a free Groq key (gsk-...)"
    )

    clean_key = api_key.strip()
    is_groq = clean_key.startswith("gsk_")
    
    if is_groq:
        st.success("⚡ Free Groq Key detected!")
        # Automatically detects the live, working models for your key
        available_models = fetch_groq_models(clean_key)
        model = st.selectbox("Model", available_models, index=0)
    else:
        model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"])
    
    st.markdown("---")
    st.header("🎯 What to Generate")
    make_resume = st.checkbox("Tailored Resume", value=True)
    make_cover_letter = st.checkbox("Matching Cover Letter", value=True)

# Helper: Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# Helper: Create Word document
def create_docx(text, title="Document"):
    doc = docx.Document()
    doc.add_heading(title, level=1)
    for paragraph in text.split("\n"):
        if paragraph.strip():
            doc.add_paragraph(paragraph)
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

# Inputs: 2 Columns
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Your Current Resume")
    resume_file = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
    resume_manual = st.text_area("...or paste resume text here:", height=220)

    master_resume = ""
    if resume_file is not None:
        if resume_file.name.endswith(".pdf"):
            master_resume = extract_text_from_pdf(resume_file)
        else:
            master_resume = resume_file.read().decode("utf-8")
    elif resume_manual.strip():
        master_resume = resume_manual.strip()

with col2:
    st.subheader("2. Target Job Description")
    job_description = st.text_area("Paste the job posting description here:", height=300)

st.markdown("---")
generate_btn = st.button("✨ Tailor My Application", type="primary", use_container_width=True)

# Generation Logic
if generate_btn:
    if not clean_key:
        st.error("⚠️ Please enter an API key in the sidebar.")
    elif not master_resume.strip():
        st.error("⚠️ Please upload or paste your resume.")
    elif not job_description.strip():
        st.error("⚠️ Please paste a job description.")
    elif not (make_resume or make_cover_letter):
        st.error("⚠️ Please check at least one box in the sidebar (Resume or Cover Letter).")
    else:
        # Route to Groq or OpenAI automatically
        if clean_key.startswith("gsk_"):
            client = OpenAI(api_key=clean_key, base_url="https://api.groq.com/openai/v1")
        else:
            client = OpenAI(api_key=clean_key)

        prompt = f"""
You are an executive career coach and expert ATS resume writer.

Analyze the Master Resume against the Job Description.

Tasks to perform:
- Generate Tailored Resume: {make_resume}
- Generate Cover Letter: {make_cover_letter}

Formatting instructions:
1. ATS Analysis: Identify the target job title, company name, and top matching keywords.
2. Tailored Resume (if enabled): 
   - Optimize experience bullet points using STAR format (action verbs + measurable results).
   - Naturally include important ATS keywords from the JD without lying.
3. Cover Letter (if enabled):
   - 3-4 professional, engaging paragraphs highlighting why the applicant is a strong match.

CRITICAL: You MUST use these exact tags to separate your response:
<<<ANALYSIS>>>
[Put ATS Analysis and keyword breakdown here]
<<<END_ANALYSIS>>>

<<<RESUME>>>
[Put the full Markdown Resume here, or leave blank if not requested]
<<<END_RESUME>>>

<<<COVER_LETTER>>>
[Put the full Markdown Cover Letter here, or leave blank if not requested]
<<<END_COVER_LETTER>>>

---
MASTER RESUME:
{master_resume}

---
JOB DESCRIPTION:
{job_description}
"""

        with st.spinner("Analyzing job requirements and crafting documents..."):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional ATS resume and cover letter writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4
                )
                
                raw = response.choices[0].message.content

                def get_section(text, start, end):
                    if start in text and end in text:
                        return text.split(start)[1].split(end)[0].strip()
                    return ""

                st.session_state["analysis"] = get_section(raw, "<<<ANALYSIS>>>", "<<<END_ANALYSIS>>>")
                st.session_state["resume"] = get_section(raw, "<<<RESUME>>>", "<<<END_RESUME>>>")
                st.session_state["cover_letter"] = get_section(raw, "<<<COVER_LETTER>>>", "<<<END_COVER_LETTER>>>")
                st.success("✅ Generated successfully!")

            except Exception as e:
                st.error(f"Error: {e}")

# Display Results
if "analysis" in st.session_state:
    st.markdown("### 📋 Generated Results")

    tabs_to_show = []
    if st.session_state.get("resume"):
        tabs_to_show.append("📄 Tailored Resume")
    if st.session_state.get("cover_letter"):
        tabs_to_show.append("✉️ Cover Letter")
    tabs_to_show.append("📊 ATS Keyword Analysis")

    tabs = st.tabs(tabs_to_show)
    idx = 0

    # Resume Tab
    if st.session_state.get("resume"):
        with tabs[idx]:
            content = st.session_state["resume"]
            st.markdown(content)
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("Download Resume (.md)", content, "tailored_resume.md", "text/markdown", use_container_width=True)
            with c2:
                st.download_button("Download Resume (.docx)", create_docx(content, "Tailored Resume"), "tailored_resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        idx += 1

    # Cover Letter Tab
    if st.session_state.get("cover_letter"):
        with tabs[idx]:
            cl_content = st.session_state["cover_letter"]
            st.markdown(cl_content)
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("Download Cover Letter (.md)", cl_content, "cover_letter.md", "text/markdown", use_container_width=True)
            with c2:
                st.download_button("Download Cover Letter (.docx)", create_docx(cl_content, "Cover Letter"), "cover_letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        idx += 1

    # Analysis Tab
    with tabs[idx]:
        st.markdown(st.session_state.get("analysis", "No analysis available."))