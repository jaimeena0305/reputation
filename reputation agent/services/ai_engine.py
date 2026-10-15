import requests
import json
import re
from typing import Dict, Any, List, Optional
from config import settings

class AIEngine:
    """
    Unified AI engine supporting Gemini, Groq, OpenAI, and a robust Heuristic fallback.
    No heavy SDK dependencies needed; works cleanly in pure Python.
    """
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        
    def _call_gemini(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        if not self.gemini_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"Gemini API error: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Gemini call failed: {e}")
        return None

    def _call_groq(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        if not self.groq_key:
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt or "You are an expert local business reputation and SEO assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Groq call failed: {e}")
        return None

    def _call_openai(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        if not self.openai_key:
            return None
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt or "You are an expert local business reputation and SEO assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenAI call failed: {e}")
        return None

    def _generate_llm(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        # Try configured provider first, then fallback to others if keys are present
        if self.provider == "gemini" and self.gemini_key:
            res = self._call_gemini(prompt, system_prompt)
            if res: return res
        elif self.provider == "groq" and self.groq_key:
            res = self._call_groq(prompt, system_prompt)
            if res: return res
        elif self.provider == "openai" and self.openai_key:
            res = self._call_openai(prompt, system_prompt)
            if res: return res
            
        # Try any available key
        if self.gemini_key:
            res = self._call_gemini(prompt, system_prompt)
            if res: return res
        if self.groq_key:
            res = self._call_groq(prompt, system_prompt)
            if res: return res
        if self.openai_key:
            res = self._call_openai(prompt, system_prompt)
            if res: return res
            
        return None

    # ==========================================
    # 1. Sentiment & Theme Extraction
    # ==========================================
    def analyze_review(self, review_text: str, rating: int) -> Dict[str, Any]:
        """
        Analyzes review text and rating to extract sentiment, score (-1 to 1),
        urgency, and key themes/issues.
        """
        prompt = f"""Analyze this customer review for a local business:
Rating: {rating} stars out of 5
Review Text: "{review_text}"

Return ONLY a valid JSON object matching this schema:
{{
  "sentiment": "positive" | "neutral" | "negative",
  "sentiment_score": float between -1.0 and 1.0,
  "urgency": "low" | "medium" | "high",
  "themes": ["theme1", "theme2", "theme3"]
}}
Do not include markdown backticks or commentary."""

        llm_response = self._generate_llm(prompt, "You are a local business customer sentiment analyzer.")
        if llm_response:
            try:
                # Strip any backticks if LLM returns ```json ... ```
                clean_json = re.sub(r"^```[a-z]*\s*", "", llm_response.strip(), flags=re.MULTILINE)
                clean_json = re.sub(r"```$", "", clean_json.strip())
                parsed = json.loads(clean_json)
                return {
                    "sentiment": parsed.get("sentiment", "positive" if rating >= 4 else "negative"),
                    "sentiment_score": float(parsed.get("sentiment_score", 0.8 if rating >= 4 else -0.7)),
                    "urgency": parsed.get("urgency", "high" if rating <= 2 else "low"),
                    "themes": parsed.get("themes", ["general service"])
                }
            except Exception as e:
                print(f"Error parsing LLM sentiment JSON: {e}")

        # Intelligent Heuristic Fallback
        return self._heuristic_analyze_review(review_text, rating)

    def _heuristic_analyze_review(self, text: str, rating: int) -> Dict[str, Any]:
        lower = text.lower()
        themes = []
        
        # Check common themes
        if any(w in lower for w in ["wait", "delay", "time", "late", "hour", "minutes"]):
            themes.append("wait time & scheduling")
        if any(w in lower for w in ["rude", "attitude", "unfriendly", "dismissive", "polite", "friendly", "kind", "helpful"]):
            themes.append("customer service & staff demeanor")
        if any(w in lower for w in ["price", "cost", "expensive", "bill", "insurance", "charge", "overpriced"]):
            themes.append("pricing & billing transparency")
        if any(w in lower for w in ["clean", "dirty", "hygiene", "tidy", "atmosphere", "vibe"]):
            themes.append("cleanliness & atmosphere")
        if any(w in lower for w in ["quality", "food", "pain", "teeth", "clean", "repair", "fix", "coffee", "roast"]):
            themes.append("service & product quality")
            
        if not themes:
            themes.append("overall experience")

        if rating >= 4:
            sentiment = "positive"
            score = 0.75 + (0.2 * (rating - 4))
            urgency = "low"
        elif rating == 3:
            sentiment = "neutral"
            score = 0.05
            urgency = "medium"
        else:
            sentiment = "negative"
            score = -0.5 - (0.25 * (3 - rating))
            urgency = "high"
            
        return {
            "sentiment": sentiment,
            "sentiment_score": round(score, 2),
            "urgency": urgency,
            "themes": themes
        }

    # ==========================================
    # 2. AI Review Response Generator
    # ==========================================
    def generate_review_response(
        self,
        business_name: str,
        category: str,
        city: str,
        author_name: str,
        rating: int,
        review_text: str,
        target_keywords: List[str],
        brand_tone: str,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Drafts a personalized, empathetic, SEO-optimized response that:
        - Mentions the author by first name
        - Echoes specifics of the review
        - Naturally integrates 1-2 local SEO keywords without keyword stuffing
        - For negative reviews: de-escalates, offers direct owner offline phone/email, never argues
        - For positive reviews: expresses gratitude and invites them back
        """
        kw_str = ", ".join(target_keywords[:3]) if target_keywords else f"{category} in {city}"
        
        system_prompt = f"""You are the reputation manager for '{business_name}', a premier {category} located in {city}.
Brand Tone: {brand_tone}
Primary Local SEO Keywords to naturally weave into positive replies: {kw_str}

Rules:
1. Greet the customer by name (e.g. 'Hi {author_name.split()[0]}').
2. Keep it concise, genuine, and under 90 words.
3. For positive reviews (4-5 stars): Thank them warmly, reference specific details they praised, and weave in the business specialty naturally.
4. For negative reviews (1-2 stars): Empathize sincerely, take ownership without being overly defensive, do NOT stuff SEO keywords into complaints, and provide a direct offline resolution path (phone or owner email).
5. Output ONLY the response text."""

        user_prompt = f"""Customer: {author_name}
Rating: {rating}/5 Stars
Review: "{review_text}"
{f'Extra instruction: {custom_instructions}' if custom_instructions else ''}

Draft the reply:"""

        llm_response = self._generate_llm(user_prompt, system_prompt)
        if llm_response:
            return llm_response.strip().strip('"')

        # Heuristic Response Generator
        return self._heuristic_generate_response(
            business_name, category, city, author_name, rating, review_text, target_keywords, brand_tone
        )

    def _heuristic_generate_response(
        self,
        business_name: str,
        category: str,
        city: str,
        author_name: str,
        rating: int,
        review_text: str,
        target_keywords: List[str],
        brand_tone: str
    ) -> str:
        first_name = author_name.split()[0] if author_name else "there"
        kw = target_keywords[0] if target_keywords else f"{category} in {city}"
        
        if rating >= 4:
            return (
                f"Hi {first_name}! Thank you so much for taking the time to share your 5-star experience with {business_name}. "
                f"Our team takes great pride in delivering the highest quality {kw}, and knowing you had such a seamless visit means "
                f"the world to us. We look forward to welcoming you back soon!"
            )
        elif rating == 3:
            return (
                f"Hello {first_name}, thank you for your feedback regarding your recent visit to {business_name}. "
                f"While we are glad certain parts of your visit went smoothly, we always aim for 5-star satisfaction and take your notes "
                f"to heart so we can continue improving our {category} service. Please feel free to reach out to us directly so we can ensure "
                f"your next visit exceeds expectations."
            )
        else: # 1 or 2 stars
            return (
                f"Dear {first_name}, thank you for bringing this to our attention. We sincerely apologize that your experience did not "
                f"meet the high standard we hold ourselves to at {business_name}. We take feedback like yours very seriously to ensure our "
                f"team addresses these concerns immediately. We would value the opportunity to speak with you directly and make this right. "
                f"Please contact our management team directly so we can assist you personally."
            )

    # ==========================================
    # 3. Phase 4 Acquisition Engine: GBP Audit & Cold Pitch
    # ==========================================
    def generate_audit_and_pitch(
        self,
        business_name: str,
        category: str,
        city: str,
        current_rating: float,
        review_count: int,
        unreplied_count: int,
        monthly_customer_value: float = 250.0
    ) -> Dict[str, Any]:
        """
        Produces the Phase 4 Client Acquisition weapon:
        - Health score & SEO grade
        - Calculated missed revenue
        - High-converting cold outreach email
        - 60-second Loom screen recording script
        """
        # Calculate scores
        # Rating penalty: 4.8 is gold standard. Drops below 4.5 hurt conversions by 30%. Below 4.0 drops conversions by 70%.
        rating_score = max(0, min(100, int((current_rating / 5.0) * 100)))
        unreplied_penalty = min(35, int((unreplied_count / max(1, review_count)) * 40))
        health_score = max(18, min(95, rating_score - unreplied_penalty))
        
        if health_score >= 85:
            grade = "B+"
            reputation_grade = "Strong"
        elif health_score >= 70:
            grade = "C+"
            reputation_grade = "Vulnerable to Local Competitors"
        elif health_score >= 50:
            grade = "D"
            reputation_grade = "Critical Attention Needed"
        else:
            grade = "F"
            reputation_grade = "Severe Local Search Leakage"

        # Conversion drop calculation:
        # Every 0.1 drop below 4.7 costs ~3-5% of potential inbound search leads
        estimated_lost_leads_per_month = max(2, int((4.8 - min(4.8, current_rating)) * 12) + int(unreplied_count * 0.3))
        missed_annual_revenue = estimated_lost_leads_per_month * monthly_customer_value * 12

        cold_email_subject = f"Quick question about {business_name}'s Google Business listing in {city}"
        
        cold_email_body = f"""Hi {business_name} Team,

I was looking at local {category.lower()} options in {city} and noticed your Google Business profile has {review_count} reviews with an average {current_rating} rating.

However, I noticed {unreplied_count} recent customer reviews (including critical feedback) haven't received a response yet. 

Google's local search algorithm directly rewards businesses that respond to reviews within 24 hours with higher placement in the top 3 Google Maps pack. Because of these unaddressed reviews, you're likely losing around {estimated_lost_leads_per_month} high-intent customers each month to local competitors who rank slightly higher.

At ~${int(monthly_customer_value)} per customer, that's roughly ${int(missed_annual_revenue):,} in potential revenue slipping away each year.

I recorded a quick 60-second video showing:
1. Exactly which keywords your competitors are outranking you for right now.
2. How you can automatically monitor Google + Yelp and draft professional, SEO-optimized responses in 10 seconds without lifting a finger.

Would it be okay if I sent over that 60-second walkthrough video? 

Best regards,
Local SEO & Reputation Specialist"""

        loom_script = f"""[0:00 - 0:10] HOOK:
"Hey {business_name} team! I'm on Google Maps looking at {category.lower()} searches here in {city}, and I wanted to point out a huge, easy win for your business this month."

[0:10 - 0:25] THE AUDIT & THE PROBLEM:
"Right now, your profile is at a {current_rating}-star average with {review_count} reviews. But here's the issue: there are {unreplied_count} reviews sitting unanswered. When Google sees unanswered reviews—especially negative ones—it pushes your listing out of the top 3 'Map Pack', handing those calls directly to your top competitors."

[0:25 - 0:45] THE SOLUTION & LIVE DEMO:
"We built an AI-powered reputation agent specifically for local {category.lower()} businesses. Every time a new review comes in on Google or Yelp, it automatically analyzes sentiment, alerts you, and drafts a warm, professional, SEO-keyword-optimized reply ready for your 1-click approval."

[0:45 - 1:00] THE CALL TO ACTION:
"I set up a preview dashboard for {business_name}. If you'd like to test it out completely free for 14 days and recover those lost rankings, reply back or click the link below to pick a 10-minute time. Have a great week!"
"""

        return {
            "business_name": business_name,
            "category": category,
            "city": city,
            "overall_health_score": health_score,
            "current_rating": current_rating,
            "review_count": review_count,
            "unreplied_count": unreplied_count,
            "estimated_lost_leads_per_month": estimated_lost_leads_per_month,
            "missed_annual_revenue": missed_annual_revenue,
            "local_seo_grade": grade,
            "reputation_grade": reputation_grade,
            "critical_vulnerabilities": [
                f"{unreplied_count} unanswered customer reviews signaling poor engagement to Google Maps",
                f"Rating of {current_rating} vs top local competitors averaging 4.8+",
                "Missed local SEO keywords in historical review responses",
                f"Estimated ~{estimated_lost_leads_per_month} lost local inquiries/month worth approx ${int(missed_annual_revenue):,}/year"
            ],
            "quick_wins": [
                "Respond to all pending reviews with personalized, empathetic replies within 48 hours",
                "Inject primary neighborhood keywords (e.g. South Congress, Capitol Hill) into positive reply templates",
                "Automate weekly sentiment and ranking tracking to catch negative reviews before they harm conversions"
            ],
            "cold_email_subject": cold_email_subject,
            "cold_email_body": cold_email_body,
            "loom_video_script": loom_script
        }

ai_engine = AIEngine()
