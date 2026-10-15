import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config import settings

DB_FILE = settings.BASE_DIR / "reputation_agent.db"

def get_connection():
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Businesses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS businesses (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        city TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        website TEXT,
        google_place_id TEXT,
        yelp_biz_id TEXT,
        target_keywords TEXT, -- JSON array
        brand_tone TEXT,
        notification_email TEXT,
        weekly_report_day TEXT,
        created_at TEXT
    )
    """)
    
    # 2. Reviews table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id TEXT PRIMARY KEY,
        business_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        author_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        review_date TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        sentiment_score REAL NOT NULL,
        themes TEXT, -- JSON array
        urgency TEXT NOT NULL,
        draft_response TEXT,
        response_status TEXT NOT NULL, -- pending, approved, posted
        posted_response TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (business_id) REFERENCES businesses (id)
    )
    """)
    
    # 3. Keyword Ranks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keyword_ranks (
        id TEXT PRIMARY KEY,
        business_id TEXT NOT NULL,
        keyword TEXT NOT NULL,
        current_rank INTEGER NOT NULL,
        previous_rank INTEGER NOT NULL,
        search_volume INTEGER NOT NULL,
        in_local_pack INTEGER NOT NULL,
        checked_at TEXT,
        FOREIGN KEY (business_id) REFERENCES businesses (id)
    )
    """)
    
    # 4. Weekly Reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id TEXT PRIMARY KEY,
        business_id TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        total_reviews_period INTEGER NOT NULL,
        avg_rating_period REAL NOT NULL,
        positive_count INTEGER NOT NULL,
        neutral_count INTEGER NOT NULL,
        negative_count INTEGER NOT NULL,
        response_rate_percent REAL NOT NULL,
        net_sentiment_score REAL NOT NULL,
        top_keywords_ranked TEXT, -- JSON array
        key_highlights TEXT, -- JSON array
        actionable_recommendations TEXT, -- JSON array
        email_sent INTEGER NOT NULL,
        generated_at TEXT,
        FOREIGN KEY (business_id) REFERENCES businesses (id)
    )
    """)

    # 5. Prospects & Acquisition Deals Pipeline table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prospects (
        id TEXT PRIMARY KEY,
        business_name TEXT NOT NULL,
        category TEXT NOT NULL,
        city TEXT NOT NULL,
        current_rating REAL NOT NULL,
        review_count INTEGER NOT NULL,
        unreplied_count INTEGER NOT NULL,
        health_score INTEGER NOT NULL,
        annual_revenue_leak REAL NOT NULL,
        status TEXT NOT NULL, -- Audited, Cold Email Sent, Loom Sent, Call Booked, Won Client ($149/mo), Lost
        notes TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM businesses")
    if cursor.fetchone()[0] > 0:
        return # Already seeded
        
    print("Initializing demo local business clients...")
    
    # Client 1: Dr. Smile Family Dental (Austin, TX)
    biz1 = {
        "id": "biz-dentist-01",
        "name": "Dr. Smile Family & Cosmetic Dentistry",
        "category": "Dentist & Orthodontics",
        "city": "Austin, TX",
        "address": "4502 S Congress Ave, Austin, TX 78745",
        "phone": "(512) 555-0198",
        "website": "https://drsmileaustin.example.com",
        "google_place_id": "ChIJ_demo_place_dentist_austin",
        "yelp_biz_id": "dr-smile-family-dentistry-austin",
        "target_keywords": json.dumps([
            "best family dentist austin",
            "emergency dental care austin",
            "teeth whitening near me",
            "painless tooth extraction south congress",
            "invisalign clear aligners austin"
        ]),
        "brand_tone": "Warm, reassuring, gentle, clinically authoritative, inviting patients back for preventative checkups",
        "notification_email": "dr.patel@drsmileaustin.example.com",
        "weekly_report_day": "Monday",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Client 2: Bean & Bloom Artisan Cafe (Seattle, WA)
    biz2 = {
        "id": "biz-cafe-02",
        "name": "Bean & Bloom Artisan Coffee Roasters",
        "category": "Cafe & Roastery",
        "city": "Seattle, WA",
        "address": "1208 Pine St, Seattle, WA 98101",
        "phone": "(206) 555-0142",
        "website": "https://beanandbloomcafe.example.com",
        "google_place_id": "ChIJ_demo_place_cafe_seattle",
        "yelp_biz_id": "bean-and-bloom-seattle",
        "target_keywords": [
            "specialty coffee capitol hill seattle",
            "best oat milk latte seattle",
            "study cafe with fast wifi seattle",
            "artisan bakery and coffee pine st"
        ],
        "brand_tone": "Trendy, community-driven, warm, passionate about specialty craft roasts",
        "notification_email": "hello@beanandbloomcafe.example.com",
        "weekly_report_day": "Monday",
        "created_at": datetime.utcnow().isoformat()
    }
    biz2["target_keywords"] = json.dumps(biz2["target_keywords"])
    
    # Client 3: Apex HVAC & Plumbing (Denver, CO)
    biz3 = {
        "id": "biz-contractor-03",
        "name": "Apex HVAC & Emergency Plumbing",
        "category": "HVAC Contractor & Plumber",
        "city": "Denver, CO",
        "address": "3401 Walnut St, Denver, CO 80205",
        "phone": "(303) 555-0177",
        "website": "https://apexhvacdenver.example.com",
        "google_place_id": "ChIJ_demo_place_hvac_denver",
        "yelp_biz_id": "apex-hvac-plumbing-denver",
        "target_keywords": json.dumps([
            "emergency furnace repair denver",
            "24 hour plumber near me",
            "commercial hvac installation denver",
            "water heater replacement lakewood co"
        ]),
        "brand_tone": "Prompt, reliable, transparent pricing, licensed & insured expertise",
        "notification_email": "dispatch@apexhvacdenver.example.com",
        "weekly_report_day": "Monday",
        "created_at": datetime.utcnow().isoformat()
    }

    for b in [biz1, biz2, biz3]:
        cursor.execute("""
        INSERT INTO businesses VALUES (
            :id, :name, :category, :city, :address, :phone, :website,
            :google_place_id, :yelp_biz_id, :target_keywords, :brand_tone,
            :notification_email, :weekly_report_day, :created_at
        )
        """, b)
        
    # Seed Reviews for Dr. Smile Dental
    dental_reviews = [
        {
            "id": "rev-101",
            "business_id": "biz-dentist-01",
            "platform": "google",
            "author_name": "Marcus Sterling",
            "rating": 5,
            "text": "I had terrible dental anxiety for years, but Dr. Patel and the hygienist Sarah were incredible. The procedure was completely painless and the front desk explained my insurance coverage clearly. Best family dentist in Austin by far!",
            "review_date": (datetime.utcnow() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "positive",
            "sentiment_score": 0.95,
            "themes": json.dumps(["painless dentistry", "anxiety-friendly", "clear insurance billing", "friendly staff"]),
            "urgency": "low",
            "draft_response": "Hi Marcus! Thank you so much for your kind words. We completely understand how daunting dental visits can feel, and our goal is always to make every treatment gentle, compassionate, and stress-free. Sarah and the entire Dr. Smile Family Dentistry team in South Congress look forward to seeing you at your next regular checkup!",
            "response_status": "pending",
            "posted_response": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": "rev-102",
            "business_id": "biz-dentist-01",
            "platform": "google",
            "author_name": "Elena Rostova",
            "rating": 2,
            "text": "The dental cleaning itself was fine, but I had to sit in the waiting room for 45 minutes past my scheduled appointment time without anyone telling me what was happening. As a working professional my time is valuable.",
            "review_date": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "negative",
            "sentiment_score": -0.65,
            "themes": json.dumps(["long wait time", "front desk communication", "scheduling"]),
            "urgency": "high",
            "draft_response": "Dear Elena, we deeply apologize for the 45-minute delay during your recent visit. We truly respect your time as a busy professional, and our team fell short by not proactively keeping you informed when an urgent dental emergency ran into the schedule. We are refining our check-in protocols right now. Please reach out directly to our clinic manager at (512) 555-0198 so we can ensure your next visit is completely prompt and seamless.",
            "response_status": "pending",
            "posted_response": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": "rev-103",
            "business_id": "biz-dentist-01",
            "platform": "yelp",
            "author_name": "David K.",
            "rating": 5,
            "text": "Had an emergency cracked molar on a Saturday morning. They squeezed me into the schedule within 2 hours and took care of the pain immediately. Truly lifesavers in South Austin!",
            "review_date": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "positive",
            "sentiment_score": 0.92,
            "themes": json.dumps(["emergency dental care", "fast response", "pain relief"]),
            "urgency": "low",
            "draft_response": "Thank you David! Providing rapid relief for emergency dental situations in South Austin is a top priority for our practice. We are thrilled that Dr. Patel was able to get you comfortable and back to your weekend without pain. Take care!",
            "response_status": "approved",
            "posted_response": "Thank you David! Providing rapid relief for emergency dental situations in South Austin is a top priority for our practice. We are thrilled that Dr. Patel was able to get you comfortable and back to your weekend without pain. Take care!",
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": "rev-104",
            "business_id": "biz-dentist-01",
            "platform": "google",
            "author_name": "Samantha Liu",
            "rating": 4,
            "text": "Great teeth whitening results. Took about an hour and my teeth are noticeably brighter. A bit pricey compared to at-home kits, but the professional in-office result was worth it.",
            "review_date": (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "positive",
            "sentiment_score": 0.60,
            "themes": json.dumps(["cosmetic teeth whitening", "pricing", "high quality results"]),
            "urgency": "low",
            "draft_response": "Hi Samantha, thank you for sharing your experience! We are delighted that you love your brighter smile after your professional teeth whitening session. We pride ourselves on using clinical-grade formulas for safer, longer-lasting radiance. Keep smiling!",
            "response_status": "posted",
            "posted_response": "Hi Samantha, thank you for sharing your experience! We are delighted that you love your brighter smile after your professional teeth whitening session. We pride ourselves on using clinical-grade formulas for safer, longer-lasting radiance. Keep smiling!",
            "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ]

    # Seed Reviews for Bean & Bloom Cafe
    cafe_reviews = [
        {
            "id": "rev-201",
            "business_id": "biz-cafe-02",
            "platform": "google",
            "author_name": "Chloe Vance",
            "rating": 5,
            "text": "Best oat milk vanilla latte in Seattle! The espresso has rich chocolate undertones and their cardamom buns are freshly baked each morning. Incredible vibe to get remote work done.",
            "review_date": (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "positive",
            "sentiment_score": 0.98,
            "themes": json.dumps(["specialty latte", "fresh pastries", "laptop-friendly vibe", "fast wifi"]),
            "urgency": "low",
            "draft_response": "Thanks so much Chloe! We take our artisan roasts and small-batch morning cardamom buns seriously, and our team loves having remote creatives hang out at our Pine St roastery. See you tomorrow for your morning brew!",
            "response_status": "pending",
            "posted_response": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "id": "rev-202",
            "business_id": "biz-cafe-02",
            "platform": "yelp",
            "author_name": "Brian O'Connor",
            "rating": 1,
            "text": "Waited 20 minutes for a drip coffee during morning rush. When I asked the barista, they had lost my ticket and were unapologetic. Coffee is good, service today was frustrating.",
            "review_date": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": "negative",
            "sentiment_score": -0.80,
            "themes": json.dumps(["lost order ticket", "slow service", "barista attitude"]),
            "urgency": "high",
            "draft_response": "Brian, we sincerely apologize for the lost ticket and the dismissive attitude you encountered during the morning rush. That does not reflect our standards for hospitality. We'd love to make this right—please stop by or email hello@beanandbloomcafe.example.com and your next breakfast is on us.",
            "response_status": "pending",
            "posted_response": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    ]

    for rev in dental_reviews + cafe_reviews:
        cursor.execute("""
        INSERT INTO reviews VALUES (
            :id, :business_id, :platform, :author_name, :rating, :text,
            :review_date, :sentiment, :sentiment_score, :themes, :urgency,
            :draft_response, :response_status, :posted_response, :created_at, :updated_at
        )
        """, rev)

    # Seed SEO Keywords for Dr. Smile Dental
    keywords = [
        ("kw-101", "biz-dentist-01", "best family dentist austin", 2, 4, 1300, 1),
        ("kw-102", "biz-dentist-01", "emergency dental care austin", 1, 1, 880, 1),
        ("kw-103", "biz-dentist-01", "teeth whitening near me", 4, 6, 2400, 0),
        ("kw-104", "biz-dentist-01", "painless tooth extraction south congress", 1, 2, 320, 1),
        ("kw-105", "biz-dentist-01", "invisalign clear aligners austin", 5, 8, 1100, 0),
        
        ("kw-201", "biz-cafe-02", "specialty coffee capitol hill seattle", 1, 2, 1600, 1),
        ("kw-202", "biz-cafe-02", "best oat milk latte seattle", 3, 3, 920, 1),
        ("kw-203", "biz-cafe-02", "study cafe with fast wifi seattle", 2, 5, 1450, 1)
    ]
    
    for kw in keywords:
        cursor.execute("""
        INSERT INTO keyword_ranks VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (kw[0], kw[1], kw[2], kw[3], kw[4], kw[5], kw[6], datetime.utcnow().isoformat()))
        
    conn.commit()

# Accessor methods
def get_all_businesses() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses ORDER BY created_at ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for r in rows:
        r["target_keywords"] = json.loads(r["target_keywords"]) if r.get("target_keywords") else []
    return rows

def get_business_by_id(business_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses WHERE id = ?", (business_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["target_keywords"] = json.loads(data["target_keywords"]) if data.get("target_keywords") else []
    return data

def get_reviews_for_business(business_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if status and status != "all":
        cursor.execute(
            "SELECT * FROM reviews WHERE business_id = ? AND response_status = ? ORDER BY review_date DESC",
            (business_id, status)
        )
    else:
        cursor.execute(
            "SELECT * FROM reviews WHERE business_id = ? ORDER BY review_date DESC",
            (business_id,)
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for r in rows:
        r["themes"] = json.loads(r["themes"]) if r.get("themes") else []
    return rows

def get_review_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["themes"] = json.loads(data["themes"]) if data.get("themes") else []
    return data

def insert_review(review_dict: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    themes_str = json.dumps(review_dict.get("themes", []))
    cursor.execute("""
    INSERT INTO reviews (
        id, business_id, platform, author_name, rating, text, review_date,
        sentiment, sentiment_score, themes, urgency, draft_response,
        response_status, posted_response, created_at, updated_at
    ) VALUES (
        :id, :business_id, :platform, :author_name, :rating, :text, :review_date,
        :sentiment, :sentiment_score, :themes, :urgency, :draft_response,
        :response_status, :posted_response, :created_at, :updated_at
    )
    """, {**review_dict, "themes": themes_str})
    conn.commit()
    conn.close()
    return review_dict["id"]

def update_review_response(review_id: str, response_text: str, status: str = "approved") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    posted_text = response_text if status == "posted" else None
    cursor.execute("""
    UPDATE reviews
    SET draft_response = ?,
        response_status = ?,
        posted_response = COALESCE(?, posted_response),
        updated_at = ?
    WHERE id = ?
    """, (response_text, status, posted_text, datetime.utcnow().isoformat(), review_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_keywords_for_business(business_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM keyword_ranks WHERE business_id = ? ORDER BY current_rank ASC", (business_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def save_weekly_report(report_dict: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO weekly_reports VALUES (
        :id, :business_id, :period_start, :period_end, :total_reviews_period,
        :avg_rating_period, :positive_count, :neutral_count, :negative_count,
        :response_rate_percent, :net_sentiment_score, :top_keywords_ranked,
        :key_highlights, :actionable_recommendations, :email_sent, :generated_at
    )
    """, {
        **report_dict,
        "top_keywords_ranked": json.dumps(report_dict.get("top_keywords_ranked", [])),
        "key_highlights": json.dumps(report_dict.get("key_highlights", [])),
        "actionable_recommendations": json.dumps(report_dict.get("actionable_recommendations", [])),
        "email_sent": 1 if report_dict.get("email_sent") else 0
    })
    conn.commit()
    conn.close()
    return report_dict["id"]

def get_weekly_reports_for_business(business_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weekly_reports WHERE business_id = ? ORDER BY generated_at DESC", (business_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for r in rows:
        r["top_keywords_ranked"] = json.loads(r["top_keywords_ranked"]) if r.get("top_keywords_ranked") else []
        r["key_highlights"] = json.loads(r["key_highlights"]) if r.get("key_highlights") else []
        r["actionable_recommendations"] = json.loads(r["actionable_recommendations"]) if r.get("actionable_recommendations") else []
    return rows
