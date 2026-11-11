import io, os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader
import db, ai

app = FastAPI(title="Contract Audit System")

class ChatIn(BaseModel):                    # shape of the chat request body
    audit_id: int
    question: str

class AssistIn(BaseModel):              # shape of an assistant request
    message: str
    history: list[dict] = []            # [{"role": "user"|"assistant", "text": "..."}]

def extract_text(filename, data):
    # PDF -> read each page; otherwise treat as plain text
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    return data.decode("utf-8", errors="ignore")

@app.post("/api/audit")
async def audit(file: UploadFile = File(...)):
    text = extract_text(file.filename, await file.read())
    if len(text.strip()) < 50:
        raise HTTPException(400, "Could not read text from this file (scanned PDF?).")
    try:
        result = ai.audit_contract(text)    # Claude returns structured JSON
    except Exception as e:
        raise HTTPException(500, f"AI audit failed: {e}")
    try:
        audit_id = db.save_audit(file.filename, result, text)   # persist to MySQL
    except Exception as e:
        raise HTTPException(500, f"Database save failed: {e}")
    return {"audit_id": audit_id, **result}

@app.post("/api/chat")
def chat(body: ChatIn):
    text = db.get_text(body.audit_id)
    if text is None:
        raise HTTPException(404, "Audit not found")
    return ai.answer_question(text, body.question)

@app.get("/api/audits")
def audits(risk: str | None = None):        # e.g. /api/audits?risk=Medium
    return db.list_audits(risk)             # powers the dashboard table + filter

@app.get("/api/overview")
def overview():
    return db.overview()                    # what data is stored + starter suggestions

@app.post("/api/assistant")
def assistant(body: AssistIn):
    msg = body.message.strip()[:2000]
    if not msg:
        raise HTTPException(400, "Please type a question.")
    try:
        return ai.assistant_reply(msg, body.history[-6:], db.list_audits(), db.get_all_texts())
    except Exception as e:
        raise HTTPException(500, f"Assistant failed: {e}")

# Serve the frontend at http://localhost:8000/ (must be mounted last)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "frontend"),
                           html=True), name="frontend")