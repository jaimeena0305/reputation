import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from jinja2 import Template
from config import settings
from database import (
    get_business_by_id,
    get_reviews_for_business,
    get_keywords_for_business,
    save_weekly_report,
    get_weekly_reports_for_business
)

EMAIL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }
  .container { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
  .header { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #ffffff; padding: 32px 24px; text-align: center; }
  .header h1 { margin: 0 0 6px 0; font-size: 24px; font-weight: 700; }
  .header p { margin: 0; opacity: 0.9; font-size: 14px; }
  .content { padding: 24px; }
  .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
  .kpi-card { background: #f1f5f9; padding: 14px; border-radius: 8px; text-align: center; }
  .kpi-value { font-size: 22px; font-weight: 700; color: #0f172a; }
  .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-top: 4px; }
  .section-title { font-size: 16px; font-weight: 700; margin: 20px 0 10px 0; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px; }
  .list-item { font-size: 13px; line-height: 1.6; margin-bottom: 8px; color: #334155; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
  .badge-pack { background: #dcfce7; color: #15803d; }
  .badge-rank { background: #e0e7ff; color: #4338ca; }
  .footer { background: #f8fafc; padding: 18px 24px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Weekly Reputation & SEO Impact</h1>
    <p>{{ business_name }} &bull; {{ period_start }} to {{ period_end }}</p>
  </div>
  
  <div class="content">
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-value">{{ avg_rating_period }} ★</div>
        <div class="kpi-label">Avg Rating</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ total_reviews_period }}</div>
        <div class="kpi-label">Total Reviews</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ response_rate_percent }}%</div>
        <div class="kpi-label">Response Rate</div>
      </div>
    </div>

    <div class="section-title">📊 Local SEO & Google Maps Visibility</div>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px;">
      <thead>
        <tr style="text-align: left; color: #64748b; border-bottom: 1px solid #e2e8f0;">
          <th style="padding: 6px 0;">Tracked Keyword</th>
          <th style="padding: 6px 0;">Rank</th>
          <th style="padding: 6px 0;">Map Pack</th>
        </tr>
      </thead>
      <tbody>
        {% for kw in top_keywords_ranked %}
        <tr style="border-bottom: 1px solid #f8fafc;">
          <td style="padding: 8px 0; font-weight: 500;">{{ kw.keyword }}</td>
          <td style="padding: 8px 0;"><span class="badge badge-rank">#{{ kw.current_rank }}</span></td>
          <td style="padding: 8px 0;">
            {% if kw.in_local_pack %}
              <span class="badge badge-pack">Top 3 Map Pack</span>
            {% else %}
              <span style="color: #94a3b8;">Regular Search</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <div class="section-title">✨ Key Weekly Highlights</div>
    <ul>
      {% for item in key_highlights %}
      <li class="list-item">{{ item }}</li>
      {% endfor %}
    </ul>

    <div class="section-title">🎯 Actionable Recommendations for Next Week</div>
    <ul>
      {% for rec in actionable_recommendations %}
      <li class="list-item">{{ rec }}</li>
      {% endfor %}
    </ul>
  </div>

  <div class="footer">
    Delivered automatically by your AI Local Reputation & SEO Agent.<br>
    To modify response approval settings or target keywords, visit your client portal.
  </div>
</div>
</body>
</html>
"""

class ReportGenerator:
    """
    Generates weekly SEO & review impact reports, renders client email templates,
    and sends via Resend API.
    """

    def generate_weekly_report(self, business_id: str, send_email: bool = False) -> Dict[str, Any]:
        biz = get_business_by_id(business_id)
        if not biz:
            return {"error": "Business not found"}

        now = datetime.utcnow()
        start_date = (now - timedelta(days=7)).strftime("%b %d, %Y")
        end_date = now.strftime("%b %d, %Y")

        reviews = get_reviews_for_business(business_id)
        keywords = get_keywords_for_business(business_id)

        total_revs = len(reviews)
        avg_rating = round(sum(r["rating"] for r in reviews) / max(1, total_revs), 1) if reviews else 5.0
        pos_count = sum(1 for r in reviews if r["sentiment"] == "positive")
        neu_count = sum(1 for r in reviews if r["sentiment"] == "neutral")
        neg_count = sum(1 for r in reviews if r["sentiment"] == "negative")

        responded_count = sum(1 for r in reviews if r["response_status"] in ("approved", "posted"))
        response_rate = round((responded_count / max(1, total_revs)) * 100, 1)

        avg_sentiment = round(sum(r["sentiment_score"] for r in reviews) / max(1, total_revs), 2) if reviews else 0.85

        # Highlights & Recommendations
        highlights = [
            f"Achieved a {response_rate}% response rate across Google and Yelp profiles.",
            f"Net positive customer sentiment stands strong at {int((pos_count / max(1, total_revs)) * 100)}%.",
            f"{sum(1 for k in keywords if k['in_local_pack'])} target keywords currently locked in Google's coveted Top-3 Map Pack."
        ]

        recommendations = [
            f"Invite recent happy {biz['category']} customers to leave a review right after their visit to maintain review velocity.",
            "Continue approving AI-drafted responses within 24 hours to reinforce Google's local relevance signals.",
            f"Target new local search keywords in upcoming responses (e.g. '{biz.get('target_keywords', ['local business'])[0]}')."
        ]

        report_id = f"rep-{int(now.timestamp())}"
        report_data = {
            "id": report_id,
            "business_id": business_id,
            "business_name": biz["name"],
            "period_start": start_date,
            "period_end": end_date,
            "total_reviews_period": total_revs,
            "avg_rating_period": avg_rating,
            "positive_count": pos_count,
            "neutral_count": neu_count,
            "negative_count": neg_count,
            "response_rate_percent": response_rate,
            "net_sentiment_score": avg_sentiment,
            "top_keywords_ranked": keywords,
            "key_highlights": highlights,
            "actionable_recommendations": recommendations,
            "email_sent": False,
            "generated_at": now.isoformat()
        }

        # Render HTML
        template = Template(EMAIL_HTML_TEMPLATE)
        html_content = template.render(**report_data)
        report_data["html_content"] = html_content

        # Dispatch email if requested and Resend key exists
        if send_email or settings.RESEND_API_KEY:
            sent_status = self._send_resend_email(
                recipient=biz.get("notification_email", "owner@business.com"),
                subject=f"Weekly Reputation & SEO Summary: {biz['name']} ({start_date} - {end_date})",
                html_body=html_content
            )
            report_data["email_sent"] = sent_status

        # Save to database
        save_weekly_report(report_data)
        return report_data

    def _send_resend_email(self, recipient: str, subject: str, html_body: str) -> bool:
        if not settings.RESEND_API_KEY:
            print(f"[Resend Email Mock] No RESEND_API_KEY set. Simulated email sent to {recipient} with subject: '{subject}'")
            return True

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": settings.REPORT_SENDER_EMAIL,
            "to": [recipient],
            "subject": subject,
            "html": html_body
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code in (200, 201):
                print(f"Resend email dispatched successfully to {recipient}!")
                return True
            print(f"Resend error: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Resend exception: {e}")
        return False

report_generator = ReportGenerator()
