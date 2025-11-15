"""
FastAPI application for a simple exam simulation coach.

This API exposes three endpoints:

* **GET /** – serves the single‑page web application from the `static/index.html` file.
* **POST /generate** – returns a dummy exam paper with a small mix of
  multiple‑choice, short‑answer and calculation questions.  In a real
  implementation you would connect this to an LLM or question bank.
* **POST /mark_bundle** – accepts the paper and a dictionary of answers
  and returns marking information with per‑question feedback and
  total marks awarded.

The dummy implementation here is deliberately straightforward so that
you can deploy it quickly on a hosting platform such as Railway,
Render or Fly.io.  The core logic lives entirely within this file.

To run locally:

```bash
pip install fastapi uvicorn pydantic
uvicorn server:app --reload
```

Then open http://127.0.0.1:8000/ in your browser.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import re


app = FastAPI(title="Exam Simulation Coach")

# --- Data models -----------------------------------------------------------

class Question(BaseModel):
    """Represents a single exam question."""

    type: str  # 'mcq', 'short' or 'calc'
    stem: str  # question text
    marks: int  # number of marks available
    # MCQ specific
    options: Optional[List[str]] = None
    answer_key: Optional[str] = None
    # Short answer specific
    expected_keywords: Optional[List[str]] = None
    model_answer: Optional[str] = None
    # Calculation specific
    steps_keywords: Optional[List[str]] = None
    final_answer: Optional[str] = None
    model_method: Optional[List[str]] = None


class PaperRequest(BaseModel):
    """Payload used when asking the server to generate a paper."""

    board: str
    level: str
    subject: str
    topics: Optional[List[str]] = None


class MarkBundle(BaseModel):
    """Bundle of paper and answers sent for marking."""

    paper: List[Question]
    answers: Dict[int, str]


# --- Dummy exam generation -------------------------------------------------

def generate_dummy_exam(board: str, level: str, subject: str, topics: Optional[List[str]]) -> List[Dict]:
    """
    Return a list of question dicts.  In a production system this
    function would talk to a language model or consult a database of
    past papers.  For now we return a fixed set of questions to
    demonstrate the flow.

    Args:
        board: The examination board (unused here).
        level: Qualification level such as GCSE or A‑level (unused).
        subject: Exam subject (unused).
        topics: A list of topics to cover (unused).

    Returns:
        A list of dictionaries, each representing a question.
    """
    return [
        {
            "type": "mcq",
            "stem": "Which process converts light energy into chemical energy in plants?",
            "marks": 1,
            "options": [
                "A. Photosynthesis",
                "B. Respiration",
                "C. Osmosis",
                "D. Fermentation",
            ],
            "answer_key": "A",
        },
        {
            "type": "short",
            "stem": "Define osmosis.",
            "marks": 3,
            "expected_keywords": ["diffusion", "water", "partially permeable membrane"],
            "model_answer": "Diffusion of water through a partially permeable membrane.",
        },
        {
            "type": "calc",
            "stem": "A 2 kg mass is lifted 1.5 m in a gravitational field where g = 9.8 m/s². Calculate the increase in gravitational potential energy (GPE).",
            "marks": 6,
            "steps_keywords": ["GPE = mgh", "2×9.8×1.5", "= 29.4"],
            "final_answer": "29.4 J",
            "model_method": ["Use GPE = mgh", "m = 2 kg", "g = 9.8 m/s²", "h = 1.5 m", "GPE = 2×9.8×1.5 = 29.4 J"],
        },
    ]


# --- Marking helpers -------------------------------------------------------

def _has_kw(text: str, kw: str) -> bool:
    """Return True if the keyword appears in the text, case‑insensitive."""
    return kw.lower() in (text or "").lower()


def mark_paper(questions: List[Dict], answers: Dict[int, str]) -> Dict:
    """
    Given a list of question dictionaries and a mapping of question
    indices to answers, compute the marks awarded and feedback.

    Args:
        questions: A list of question dictionaries (see generate_dummy_exam).
        answers: A mapping from question index (int) to the candidate's answer.

    Returns:
        A dictionary with per‑question results and totals.
    """
    results = []
    total_awarded = 0
    total_max = 0
    for i, q in enumerate(questions):
        resp = answers.get(i) or answers.get(str(i)) or ""
        awarded = 0
        feedback_parts = []
        if q["type"] == "mcq":
            if (resp.strip().upper() == (q.get("answer_key") or "").upper()):
                awarded = q["marks"]
                feedback_parts.append("Correct choice.")
            else:
                feedback_parts.append(f"Correct answer: {q.get('answer_key')}.")
        elif q["type"] == "short":
            # Count matching keywords for partial credit
            expected = q.get("expected_keywords", [])
            found = sum(1 for kw in expected if _has_kw(resp, kw))
            awarded = min(found, q["marks"])
            missing = [kw for kw in expected if not _has_kw(resp, kw)]
            if missing:
                feedback_parts.append(
                    "Missing keywords: "
                    + ", ".join(missing[:3])
                    + ("..." if len(missing) > 3 else "")
                )
            if q.get("model_answer"):
                feedback_parts.append("Model answer: " + q["model_answer"])
        elif q["type"] == "calc":
            # Award a mark for each step keyword and a mark for the final answer
            steps = q.get("steps_keywords", [])
            method_found = sum(1 for kw in steps if _has_kw(resp, kw))
            fa = (q.get("final_answer") or "").lower().replace(" ", "")
            rr = (resp or "").lower().replace(" ", "")
            final_ok = bool(fa) and fa in rr
            awarded = min(method_found + (1 if final_ok else 0), q["marks"])
            if not final_ok and q.get("final_answer"):
                feedback_parts.append(f"Expected final answer: {q['final_answer']}")
            if q.get("model_method"):
                feedback_parts.append("Method: " + " | ".join(q["model_method"]))
        else:
            feedback_parts.append("Unknown question type; awarded 0 marks.")
        results.append(
            {
                "q_index": i,
                "awarded": awarded,
                "max_marks": q["marks"],
                "feedback": " ".join(feedback_parts),
            }
        )
        total_awarded += awarded
        total_max += q["marks"]
    return {
        "results": results,
        "total_awarded": total_awarded,
        "total_max": total_max,
    }


# --- Route handlers --------------------------------------------------------

# Serve static assets from /static (e.g. index.html, JS, CSS)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def get_index() -> FileResponse:
    """Serve the main HTML page."""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.post("/generate")
def generate_paper(request: PaperRequest) -> Dict:
    """Generate a dummy paper for the given request parameters."""
    questions = generate_dummy_exam(
        request.board, request.level, request.subject, request.topics
    )
    return {"questions": questions}


@app.post("/mark_bundle")
def mark_bundle(bundle: MarkBundle) -> Dict:
    """Mark a submitted paper and return the results."""
    try:
        questions = [q.model_dump() for q in bundle.paper]
        return mark_paper(questions, bundle.answers)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
