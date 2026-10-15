import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from config import settings
from database import (
    init_db,
    get_all_businesses,
    get_business_by_id,
    get_reviews_for_business,
    get_review_by_id,
    update_review_response,
    get_keywords_for_business,
    get_weekly_reports_for_business
)
from services.ai_engine import ai_engine
from services.review_collector import review_collector
from services.seo_tracker import seo_tracker
from services.report_generator import report_generator
from models import AuditRequest

app = FastAPI(
    title="ApexRepute AI — Local Business Reputation & SEO Agent",
    description="Automated review monitoring, AI response drafting, local keyword rank tracking, and weekly client reporting.",
    version="1.0.0"
)

# Static files and Templates
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Startup event to ensure SQLite tables and seeds are ready
@app.on_event("startup")
def on_startup():
    init_db()
    print("ApexRepute AI database initialized & seeded.")

# HTML Dashboard Route
@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

# ========================================================
# Business Profiles API
# ========================================================

@app.get("/api/businesses")
def list_businesses():
    return get_all_businesses()

@app.get("/api/businesses/{business_id}")
def get_business(business_id: str):
    biz = get_business_by_id(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return biz

# ========================================================
# Reviews & AI Response Engine API
# ========================================================

@app.get("/api/businesses/{business_id}/reviews")
def get_reviews(business_id: str, status: Optional[str] = Query(None)):
    return get_reviews_for_business(business_id, status)

@app.post("/api/businesses/{business_id}/sync-reviews")
def sync_reviews(business_id: str):
    result = review_collector.sync_reviews_for_business(business_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

class UpdateResponsePayload(BaseModel):
    response_text: str
    status: str = "approved"

@app.post("/api/reviews/{review_id}/response")
def update_response(review_id: str, payload: UpdateResponsePayload):
    success = update_review_response(review_id, payload.response_text, payload.status)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found or not updated")
    return {"success": True, "review_id": review_id, "status": payload.status}

class RegeneratePayload(BaseModel):
    tone_instruction: Optional[str] = "Warm & Professional"

@app.post("/api/reviews/{review_id}/regenerate")
def regenerate_response(review_id: str, payload: RegeneratePayload):
    rev = get_review_by_id(review_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found")
    biz = get_business_by_id(rev["business_id"])
    if not biz:
        raise HTTPException(status_code=404, detail="Associated business not found")

    new_draft = ai_engine.generate_review_response(
        business_name=biz["name"],
        category=biz["category"],
        city=biz["city"],
        author_name=rev["author_name"],
        rating=rev["rating"],
        review_text=rev["text"],
        target_keywords=biz.get("target_keywords", []),
        brand_tone=biz.get("brand_tone", "Warm and professional"),
        custom_instructions=payload.tone_instruction
    )
    
    update_review_response(review_id, new_draft, "pending")
    return {"review_id": review_id, "draft_response": new_draft}

# ========================================================
# Local SEO & Keyword Tracking API
# ========================================================

@app.get("/api/businesses/{business_id}/keywords")
def get_keywords(business_id: str):
    return seo_tracker.get_rankings(business_id)

class AddKeywordPayload(BaseModel):
    keyword: str
    search_volume: Optional[int] = 500

@app.post("/api/businesses/{business_id}/keywords")
def add_keyword(business_id: str, payload: AddKeywordPayload):
    return seo_tracker.add_keyword(business_id, payload.keyword, payload.search_volume or 500)

@app.post("/api/businesses/{business_id}/keywords/refresh")
def refresh_keywords(business_id: str):
    return seo_tracker.refresh_keyword_ranks(business_id)

# ========================================================
# Weekly Impact Reports & Email API
# ========================================================

@app.post("/api/businesses/{business_id}/generate-report")
def generate_report(business_id: str, send_email: bool = False):
    report = report_generator.generate_weekly_report(business_id, send_email=send_email)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report

@app.get("/api/businesses/{business_id}/reports")
def list_reports(business_id: str):
    return get_weekly_reports_for_business(business_id)

@app.get("/api/reports/{report_id}/html", response_class=HTMLResponse)
def get_report_html(report_id: str):
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weekly_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
        
    rep_dict = dict(row)
    biz = get_business_by_id(rep_dict["business_id"])
    rep_dict["business_name"] = biz["name"] if biz else "Local Business"
    rep_dict["top_keywords_ranked"] = get_keywords_for_business(rep_dict["business_id"])
    rep_dict["key_highlights"] = [
        f"Maintained {rep_dict['response_rate_percent']}% review response rate.",
        f"Current Google/Yelp composite rating: {rep_dict['avg_rating_period']} ★."
    ]
    rep_dict["actionable_recommendations"] = [
        "Prompt customers for reviews on Google Maps directly following completed appointments.",
        "Ensure negative reviews receive personalized responses within 24 hours."
    ]
    
    from services.report_generator import EMAIL_HTML_TEMPLATE
    from jinja2 import Template
    return Template(EMAIL_HTML_TEMPLATE).render(**rep_dict)

# ========================================================
# Phase 4 Acquisition Engine: Audit & Cold Pitch API
# ========================================================

@app.post("/api/audit")
def run_business_audit(payload: AuditRequest):
    return ai_engine.generate_audit_and_pitch(
        business_name=payload.business_name,
        category=payload.category,
        city=payload.city,
        current_rating=payload.current_rating,
        review_count=payload.review_count,
        unreplied_count=payload.unreplied_count,
        monthly_customer_value=payload.monthly_customer_value
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
