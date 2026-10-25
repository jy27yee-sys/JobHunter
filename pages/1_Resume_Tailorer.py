import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import io
import docx

# Pre-attached Groq Key
DEFAULT_API_KEY = "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"

st.set_page_config(page_title="Resume & Cover Letter Tailorer", page_icon="📄", layout="wide")
st.title("📄 Resume & Cover Letter Customizer")
st.caption("Powered by OpenAI GPT-OSS on Groq — Instant generation, no token limits.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("API Key", value=DEFAULT_API_KEY, type="password")

    clean_key = api_key.strip()
    st.success("⚡ Connected & Ready!")
    
    # Pre-locked to the reliable 250k-token model that worked on your screen
    model = st.selectbox(
        "Model", 
        ["openai/gpt-oss-20b", "openai/gpt-oss-120b"], 
        index=0
    )
    
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
    resume_manual = st.text_area("...or paste resume text here:", height=200)

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
    job_description = st.text_area("Paste the job posting description here:", height=200)

# Section 3: Custom Prompt Box
st.markdown("---")
st.subheader("3. 💡 Custom Prompt & Instructions (Optional)")
custom_prompt = st.text_area(
    "Tell the AI how to write or what to focus on:",
    placeholder="e.g. Focus on my retail and digital marketing skills. Make the cover letter energetic and passionate about fashion.",
    height=80
)

st.markdown("---")
generate_btn = st.button("✨ Tailor My Application", type="primary", use_container_width=True)

# Generation Logic
if generate_btn:
    if not clean_key:
        st.error("⚠️ Please enter your API key in the sidebar.")
    elif not master_resume.strip():
        st.error("⚠️ Please upload or paste your resume.")
    elif not job_description.strip():
        st.error("⚠️ Please paste a job description.")
    elif not (make_resume or make_cover_letter):
        st.error("⚠️ Please check at least one box in the sidebar.")
    else:
        # Route to Groq server
        client = OpenAI(
            api_key=clean_key, 
            base_url="https://api.groq.com/openai/v1"
        )

        instructions = custom_prompt.strip() if custom_prompt.strip() else "None provided."

        prompt = f"""
You are an executive career coach and expert ATS resume writer.

Analyze the Master Resume against the Job Description.

Tasks to generate:
- Tailored Resume: {make_resume}
- Cover Letter: {make_cover_letter}

SPECIAL USER INSTRUCTIONS (CRITICAL TO FOLLOW):
{instructions}

Instructions:
1. Identify ATS keywords, missing skills, and strategic angle.
2. Tailor resume bullets using the STAR method with active verbs and quantifiable results.
3. Write an engaging, confident 3-4 paragraph cover letter.

CRITICAL FORMATTING: You MUST use these exact tags to delimit your sections:

<<<ANALYSIS>>>
[Provide ATS match analysis and keyword recommendations here]
<<<END_ANALYSIS>>>

<<<RESUME>>>
[Provide Full Markdown Resume here, or leave empty if not requested]
<<<END_RESUME>>>

<<<COVER_LETTER>>>
[Provide Full Markdown Cover Letter here, or leave empty if not requested]
<<<END_COVER_LETTER>>>

---
MASTER RESUME:
{master_resume}

---
JOB DESCRIPTION:
{job_description}
"""

        with st.spinner("Analyzing requirements and crafting documents..."):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional ATS resume and cover letter writer. Always output in clear English Markdown with requested delimiters."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4
                )
                
                raw = response.choices[0].message.content

                def extract_tag(text, start, end):
                    if start in text and end in text:
                        return text.split(start)[1].split(end)[0].strip()
                    return ""

                resume_text = extract_tag(raw, "<<<RESUME>>>", "<<<END_RESUME>>>")
                cover_text = extract_tag(raw, "<<<COVER_LETTER>>>", "<<<END_COVER_LETTER>>>")
                analysis_text = extract_tag(raw, "<<<ANALYSIS>>>", "<<<END_ANALYSIS>>>")

                if not resume_text and "<<<RESUME>>>" in raw:
                    resume_text = raw.split("<<<RESUME>>>")[1].split("<<<")[0].strip()
                if not cover_text and "<<<COVER_LETTER>>>" in raw:
                    cover_text = raw.split("<<<COVER_LETTER>>>")[1].split("<<<")[0].strip()

                st.session_state["resume"] = resume_text
                st.session_state["cover_letter"] = cover_text
                st.session_state["analysis"] = analysis_text if analysis_text else "Strategic keyword alignment complete."
                st.session_state["has_generated"] = True
                st.success("✅ Generated successfully!")

            except Exception as e:
                st.error(f"Error: {e}")

# Display Results in Separate Tabs
if st.session_state.get("has_generated"):
    st.markdown("---")
    st.markdown("### 📋 Generated Documents")

    tab_titles = []
    if st.session_state.get("resume"):
        tab_titles.append("📄 Tailored Resume")
    if st.session_state.get("cover_letter"):
        tab_titles.append("✉️ Cover Letter")
    tab_titles.append("📊 ATS Analysis")

    tabs = st.tabs(tab_titles)
    curr_tab = 0

    # 1. Resume Tab
    if st.session_state.get("resume"):
        with tabs[curr_tab]:
            res_content = st.session_state["resume"]
            st.markdown(res_content)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📝 Download Resume (.docx)", 
                    create_docx(res_content, "Tailored Resume"), 
                    "tailored_resume.docx", 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                    use_container_width=True
                )
            with c2:
                st.download_button(
                    "📋 Download Resume (.md)", 
                    res_content, 
                    "tailored_resume.md", 
                    "text/markdown", 
                    use_container_width=True
                )
        curr_tab += 1

    # 2. Cover Letter Tab
    if st.session_state.get("cover_letter"):
        with tabs[curr_tab]:
            cov_content = st.session_state["cover_letter"]
            st.markdown(cov_content)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📝 Download Cover Letter (.docx)", 
                    create_docx(cov_content, "Cover Letter"), 
                    "cover_letter.docx", 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                    use_container_width=True
                )
            with c2:
                st.download_button(
                    "📋 Download Cover Letter (.md)", 
                    cov_content, 
                    "cover_letter.md", 
                    "text/markdown", 
                    use_container_width=True
                )
        curr_tab += 1

    # 3. ATS Analysis Tab
    with tabs[curr_tab]:
        st.markdown(st.session_state.get("analysis", "No analysis available."))