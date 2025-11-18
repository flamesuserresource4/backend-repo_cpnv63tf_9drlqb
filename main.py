import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

from database import create_document
from schemas import Lead, ChatLog

app = FastAPI(title="Aurum Vision API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Aurum Vision Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the Aurum Vision API"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------- Lead Generation ----------

@app.post("/api/leads")
async def create_lead(lead: Lead):
    try:
        lead_id = create_document("lead", lead)
        return {"status": "success", "id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Simple AI Assistant (Rule-based) ----------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    session_id: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: Optional[List[str]] = None


FAQ_KB: Dict[str, Dict[str, Any]] = {
    "purity": {
        "q": ["purity", "999", "lbma", "certified"],
        "a": "Aurum Vision provides only LBMA-certified 999.9 purity investment-grade gold. Each purchase is traceable and auditable.",
    },
    "storage": {
        "q": ["storage", "vault", "insured", "security"],
        "a": "Your gold is stored in institutional-grade, fully insured partner vaults with multi-layer security. You can also request home delivery when desired.",
    },
    "fees": {
        "q": ["fee", "pricing", "cost", "hidden"],
        "a": "Pricing is transparent with no hidden fees. You pay the live market rate plus a small service fee that covers custody, insurance, and reporting.",
    },
    "liquidity": {
        "q": ["sell", "liquid", "liquidity", "exit"],
        "a": "You can sell or convert your holdings anytime. We offer a streamlined liquidation process at competitive market rates.",
    },
    "plan": {
        "q": ["plan", "monthly", "accumulation", "custom"],
        "a": "Start with a low monthly contribution or build a custom plan. We assess your goals and risk profile to recommend the ideal schedule.",
    },
    "paper": {
        "q": ["paper", "etf", "derivative"],
        "a": "Physical gold is a tangible asset held outside the financial system, unlike paper gold (ETFs/derivatives) which carry counterparty and tracking-error risks.",
    },
}


def generate_answer(question: str) -> str:
    q = question.lower()
    for _, entry in FAQ_KB.items():
        if any(keyword in q for keyword in entry["q"]):
            return entry["a"]
    # Default response
    return (
        "Aurum Vision helps you accumulate LBMA-certified 999.9 physical gold through simple monthly or custom plans with insured vault storage. "
        "Ask me about purity, storage, fees, liquidity, or how the plans work."
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    try:
        answer = generate_answer(req.question)
        # Best-effort log (ignore errors if DB unavailable)
        try:
            log = ChatLog(role="user", message=req.question, session_id=req.session_id)
            create_document("chatlog", log)
            log = ChatLog(role="assistant", message=answer, session_id=req.session_id)
            create_document("chatlog", log)
        except Exception:
            pass
        return AskResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
