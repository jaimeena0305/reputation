from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class BusinessProfile(BaseModel):
    id: str
    name: str
    category: str
    city: str
    address: str
    phone: str
    website: Optional[str] = ""
    google_place_id: Optional[str] = ""
    yelp_biz_id: Optional[str] = ""
    target_keywords: List[str] = Field(default_factory=list)
    brand_tone: str = "Warm, professional, appreciative, and SEO-optimized"
    notification_email: str = "owner@business.com"
    weekly_report_day: str = "Monday"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Review(BaseModel):
    id: str
    business_id: str
    platform: str = "google" # "google", "yelp"
    author_name: str
    rating: int = 5
    text: str
    review_date: str
    sentiment: str = "positive" # "positive", "neutral", "negative"
    sentiment_score: float = 0.8 # -1.0 to 1.0
    themes: List[str] = Field(default_factory=list)
    urgency: str = "low" # "low", "medium", "high"
    draft_response: Optional[str] = None
    response_status: str = "pending" # "pending", "approved", "posted"
    posted_response: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class KeywordRank(BaseModel):
    id: str
    business_id: str
    keyword: str
    current_rank: int
    previous_rank: int
    search_volume: int = 450
    in_local_pack: bool = True
    checked_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class WeeklyReport(BaseModel):
    id: str
    business_id: str
    period_start: str
    period_end: str
    total_reviews_period: int
    avg_rating_period: float
    positive_count: int
    neutral_count: int
    negative_count: int
    response_rate_percent: float
    net_sentiment_score: float
    top_keywords_ranked: List[Dict[str, Any]] = Field(default_factory=list)
    key_highlights: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    email_sent: bool = False
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AuditRequest(BaseModel):
    business_name: str
    category: str
    city: str
    current_rating: float = 4.1
    review_count: int = 38
    unreplied_count: int = 14
    competitor_top_rating: float = 4.8
    monthly_customer_value: float = 250.0

class AuditReport(BaseModel):
    business_name: str
    category: str
    city: str
    overall_health_score: int # 0 to 100
    current_rating: float
    review_count: int
    unreplied_count: int
    missed_annual_revenue: float
    local_seo_grade: str # A, B, C, D, F
    reputation_grade: str
    critical_vulnerabilities: List[str]
    quick_wins: List[str]
    cold_email_subject: str
    cold_email_body: str
    loom_video_script: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
