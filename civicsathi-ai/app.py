import json
import os
import streamlit as st
from dotenv import load_dotenv
from app.agent_harness import CivicRequestHarness
from app.model_adapter import OllamaModelAdapter, ModelUnavailable
from app.schemas import CivicRequest
from app.duplicate_detection import find_possible_duplicates
from app.audit_log import AuditLog

load_dotenv()
st.set_page_config(page_title="CivicSathi AI", page_icon="🏙️", layout="wide")
st.title("🏙️ CivicSathi AI")
st.caption("AI-assisted civic service discovery and complaint drafting · Chandigarh")
st.info("Prototype only. Not an official Chandigarh government service. No live complaint is submitted. Please do not enter sensitive personal information.")

with st.sidebar:
    st.header("Model settings")
    st.write("Inference runs through a locally hosted Ollama model.")
    base_url = st.text_input("Ollama URL", value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model_name = st.text_input("Model name", value=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
    st.caption("Start Ollama and pull the selected model before using AI analysis.")

services_path = os.path.join("data", "services.json")
complaints_path = os.path.join("data", "sample_complaints.json")
with open(services_path, encoding="utf-8") as f:
    services = json.load(f)
with open(complaints_path, encoding="utf-8") as f:
    samples = json.load(f)

st.subheader("Describe your civic issue")
request_text = st.text_area("What do you need help with?", height=130, placeholder="Example: Garbage has been piling up near the park in Sector 22 for three days.")
language = st.selectbox("Preferred language", ["English", "Hindi", "Punjabi"])
location = st.text_input("Location or sector (optional)", placeholder="e.g., Sector 22, Chandigarh")

if st.button("Analyze request with AI", type="primary", disabled=not request_text.strip()):
    try:
        adapter = OllamaModelAdapter(base_url=base_url, model=model_name)
        harness = CivicRequestHarness(adapter, services=services)
        result = harness.intake(request_text=request_text, language=language, location=location)
        st.session_state["result"] = result.model_dump()
        st.session_state["last_request"] = request_text
        AuditLog().record("request_analyzed", {"category": result.category, "needs_human_review": result.needs_human_review})
    except ModelUnavailable as exc:
        st.error(f"Open-weight model unavailable: {exc}")
        st.info("To enable AI: start Ollama, run `ollama pull qwen2.5:3b`, and try again. No AI result was fabricated.")
    except Exception as exc:
        st.error(f"The request could not be analyzed safely: {exc}")

if "result" in st.session_state:
    data = st.session_state["result"]
    st.divider()
    st.subheader("AI-generated draft — review before use")
    st.write(f"**Suggested category:** {data['category']}")
    st.write(f"**Suggested service:** {data['suggested_service']}")
    st.write(f"**Summary:** {data['summary']}")
    st.write(f"**Location:** {data.get('location') or 'Not provided'}")
    st.write(f"**Confidence:** {data['confidence']:.2f} (model estimate; not a validated accuracy score)")
    missing = data.get("missing_information", [])
    st.write("**Missing information:** " + (", ".join(missing) if missing else "None identified by the model"))
    if data.get("needs_human_review"):
        st.warning("Human review recommended. Please verify this classification and all extracted details.")
    dups = find_possible_duplicates(st.session_state.get("last_request", ""), samples)
    if dups:
        st.subheader("Potentially similar sample reports")
        st.caption("Similarity hints only. They do not prove duplication and never reject a report.")
        for item in dups:
            st.write(f"- {item['id']}: {item['summary']} (similarity: {item['score']:.2f})")
    st.subheader("Resident review")
    edited_summary = st.text_area("Edit summary", value=data["summary"])
    st.write("This prototype prepares a draft only. It does not submit a real municipal complaint.")
    st.download_button("Download draft JSON", data=json.dumps({**data, "summary": edited_summary}, ensure_ascii=False, indent=2), file_name="civicsathi-request-draft.json", mime="application/json")

st.divider()
st.caption("Designed for future authorized integration. Municipal APIs, official case status and complaint submission are not connected.")
