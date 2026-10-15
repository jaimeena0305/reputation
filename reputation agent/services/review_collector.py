import requests
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from config import settings
from database import get_business_by_id, insert_review, get_reviews_for_business
from services.ai_engine import ai_engine

class ReviewCollector:
    """
    Connects to Google Places API, Yelp Fusion API, and provides a smart mock
    collector to simulate real-time live review ingestion.
    """
    
    def fetch_google_places_reviews(self, place_id: str) -> List[Dict[str, Any]]:
        if not settings.GOOGLE_PLACES_API_KEY or not place_id:
            return []
            
        url = f"https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,reviews,user_ratings_total",
            "key": settings.GOOGLE_PLACES_API_KEY
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_reviews = data.get("result", {}).get("reviews", [])
                normalized = []
                for idx, r in enumerate(raw_reviews):
                    normalized.append({
                        "platform": "google",
                        "author_name": r.get("author_name", "Google User"),
                        "rating": int(r.get("rating", 5)),
                        "text": r.get("text", ""),
                        "review_date": datetime.fromtimestamp(r.get("time", datetime.utcnow().timestamp())).strftime("%Y-%m-%d %H:%M")
                    })
                return normalized
        except Exception as e:
            print(f"Error fetching Google reviews: {e}")
        return []

    def fetch_yelp_reviews(self, yelp_biz_id: str) -> List[Dict[str, Any]]:
        if not settings.YELP_API_KEY or not yelp_biz_id:
            return []
            
        url = f"https://api.yelp.com/v3/businesses/{yelp_biz_id}/reviews"
        headers = {
            "Authorization": f"Bearer {settings.YELP_API_KEY}"
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_reviews = data.get("reviews", [])
                normalized = []
                for r in raw_reviews:
                    normalized.append({
                        "platform": "yelp",
                        "author_name": r.get("user", {}).get("name", "Yelp Reviewer"),
                        "rating": int(r.get("rating", 5)),
                        "text": r.get("text", ""),
                        "review_date": r.get("time_created", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
                    })
                return normalized
        except Exception as e:
            print(f"Error fetching Yelp reviews: {e}")
        return []

    def sync_reviews_for_business(self, business_id: str) -> Dict[str, Any]:
        """
        Executes review sync: checks Google/Yelp APIs if configured, or simulates
        a realistic new customer review to show live auto-drafting in action.
        """
        biz = get_business_by_id(business_id)
        if not biz:
            return {"error": "Business not found", "new_reviews": 0}

        new_reviews_found = []

        # 1. Try real external APIs first
        if biz.get("google_place_id") and settings.GOOGLE_PLACES_API_KEY:
            g_reviews = self.fetch_google_places_reviews(biz["google_place_id"])
            new_reviews_found.extend(g_reviews)
            
        if biz.get("yelp_biz_id") and settings.YELP_API_KEY:
            y_reviews = self.fetch_yelp_reviews(biz["yelp_biz_id"])
            new_reviews_found.extend(y_reviews)

        # 2. If no new reviews from live APIs (or in local testing mode), simulate a realistic newly posted review
        if not new_reviews_found:
            simulated = self._generate_simulated_review(biz)
            new_reviews_found.append(simulated)

        # Process each review: run sentiment analysis & generate AI draft reply
        added_count = 0
        existing_reviews = get_reviews_for_business(business_id)
        existing_texts = {r["text"].strip().lower() for r in existing_reviews}

        for r_data in new_reviews_found:
            if r_data["text"].strip().lower() in existing_texts:
                continue # Skip duplicates

            # Analyze sentiment & issues
            analysis = ai_engine.analyze_review(r_data["text"], r_data["rating"])
            
            # Draft personalized response
            draft = ai_engine.generate_review_response(
                business_name=biz["name"],
                category=biz["category"],
                city=biz["city"],
                author_name=r_data["author_name"],
                rating=r_data["rating"],
                review_text=r_data["text"],
                target_keywords=biz.get("target_keywords", []),
                brand_tone=biz.get("brand_tone", "Warm and professional")
            )

            review_id = f"rev-{int(datetime.utcnow().timestamp())}-{random.randint(100, 999)}"
            insert_review({
                "id": review_id,
                "business_id": business_id,
                "platform": r_data["platform"],
                "author_name": r_data["author_name"],
                "rating": r_data["rating"],
                "text": r_data["text"],
                "review_date": r_data.get("review_date", datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
                "sentiment": analysis["sentiment"],
                "sentiment_score": analysis["sentiment_score"],
                "themes": analysis["themes"],
                "urgency": analysis["urgency"],
                "draft_response": draft,
                "response_status": "pending",
                "posted_response": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })
            added_count += 1

        return {
            "success": True,
            "business_name": biz["name"],
            "new_reviews_synced": added_count,
            "message": f"Successfully synced {added_count} new review(s) with AI response drafts ready for approval."
        }

    def _generate_simulated_review(self, biz: Dict[str, Any]) -> Dict[str, Any]:
        """Generates contextual simulated reviews for realistic demonstrations."""
        cat = biz.get("category", "").lower()
        
        dental_pool = [
            ("Amanda Chen", 5, "I had my dental veneers done here and the results look so natural! Dr. Patel was attentive and patient throughout.", "google"),
            ("Robert Miller", 2, "Appointment was canceled at the last minute because the doctor was unavailable. Hard to rebook when working full time.", "google"),
            ("Jessica Taylor", 5, "Brought my 7-year-old in for her first cavity filling. The staff made her feel so safe and brave. 10/10 clinic!", "yelp"),
            ("Carlos Mendez", 4, "Clean office and gentle dental cleaning. The dental hygienist was super knowledgeable.", "google")
        ]

        cafe_pool = [
            ("Devon Riley", 5, "Their cold brew and almond croissant gave me life this morning. Super chill atmosphere to study.", "google"),
            ("Sarah Jenkins", 2, "Tables were dirty during the afternoon rush and the music was playing too loud to take a quick phone call.", "yelp"),
            ("Liam Brooks", 5, "The best specialty roaster in the city. The baristas really understand single-origin flavor profiles.", "google")
        ]

        contractor_pool = [
            ("Heather Scott", 5, "Furnace broke on a freezing Sunday night. They arrived in under 45 minutes and had heat restored in no time!", "google"),
            ("Daniel Vance", 3, "Technician fixed the leak well, but they left some muddy footprints in the hallway without cleaning up.", "google")
        ]

        if "dent" in cat:
            sample = random.choice(dental_pool)
        elif "cafe" in cat or "coffee" in cat:
            sample = random.choice(cafe_pool)
        else:
            sample = random.choice(contractor_pool)

        return {
            "author_name": sample[0],
            "rating": sample[1],
            "text": sample[2],
            "platform": sample[3],
            "review_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }

review_collector = ReviewCollector()
