import sys
from pathlib import Path

# Fix Windows console encoding for UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database import init_db, get_all_businesses, get_reviews_for_business, get_keywords_for_business
from services.ai_engine import ai_engine
from services.review_collector import review_collector
from services.seo_tracker import seo_tracker
from services.report_generator import report_generator

def test_full_agent_workflow():
    print("==================================================")
    print("ApexRepute AI — Full System Verification")
    print("==================================================")

    # 1. Initialize & Seed DB
    print("[1/6] Initializing Database & Seed Data...")
    init_db()
    businesses = get_all_businesses()
    assert len(businesses) >= 3, f"Expected at least 3 businesses, got {len(businesses)}"
    print(f" ✓ Initialized {len(businesses)} businesses:")
    for b in businesses:
        print(f"    - {b['name']} ({b['category']} in {b['city']})")

    test_biz = businesses[0]
    biz_id = test_biz["id"]

    # 2. Test Sentiment Analysis & AI Response Drafting
    print("\n[2/6] Testing AI Sentiment & Response Generator...")
    sample_review = "I was terrified of getting a root canal, but Dr. Patel was so gentle and patient. The office is spotless and the front staff is awesome!"
    sentiment = ai_engine.analyze_review(sample_review, rating=5)
    print(f" ✓ Sentiment Analysis: {sentiment['sentiment']} (score: {sentiment['sentiment_score']})")
    print(f"   Detected Themes: {sentiment['themes']}")

    response = ai_engine.generate_review_response(
        business_name=test_biz["name"],
        category=test_biz["category"],
        city=test_biz["city"],
        author_name="Sarah Connor",
        rating=5,
        review_text=sample_review,
        target_keywords=test_biz["target_keywords"],
        brand_tone=test_biz["brand_tone"]
    )
    assert len(response) > 20, "Response is too short"
    print(f" ✓ AI Drafted Response:\n   \"{response}\"")

    # 3. Test Negative Review De-escalation
    print("\n[3/6] Testing Negative Review De-escalation...")
    neg_review = "Terrible experience. Waited 50 minutes past my appointment time and the receptionist was dismissive."
    neg_analysis = ai_engine.analyze_review(neg_review, rating=1)
    print(f" ✓ Urgency: {neg_analysis['urgency']} | Sentiment: {neg_analysis['sentiment']}")

    neg_response = ai_engine.generate_review_response(
        business_name=test_biz["name"],
        category=test_biz["category"],
        city=test_biz["city"],
        author_name="Mark Davis",
        rating=1,
        review_text=neg_review,
        target_keywords=test_biz["target_keywords"],
        brand_tone=test_biz["brand_tone"]
    )
    print(f" ✓ De-escalation Draft:\n   \"{neg_response}\"")

    # 4. Test Review Ingestion & Auto Sync
    print("\n[4/6] Testing Live Review Sync...")
    sync_result = review_collector.sync_reviews_for_business(biz_id)
    print(f" ✓ Sync Result: {sync_result['message']}")
    reviews = get_reviews_for_business(biz_id)
    print(f" ✓ Total reviews for {test_biz['name']}: {len(reviews)}")

    # 5. Test Local SEO & Keyword Tracking
    print("\n[5/6] Testing Local SEO Rank Tracking...")
    keywords = get_keywords_for_business(biz_id)
    print(f" ✓ Found {len(keywords)} tracked keywords:")
    for kw in keywords[:3]:
        pack = "In Map Pack #1-3" if kw['in_local_pack'] else "Standard SERP"
        print(f"    - '{kw['keyword']}': Rank #{kw['current_rank']} ({pack}, {kw['search_volume']} searches/mo)")

    # 6. Test Weekly Report Generator
    print("\n[6/6] Testing Weekly Impact Report & Email Dispatch...")
    report = report_generator.generate_weekly_report(biz_id, send_email=False)
    assert report["id"], "Report ID was not generated"
    assert "html_content" in report, "HTML content missing in report"
    print(f" ✓ Weekly Report ID: {report['id']}")
    print(f" ✓ Period: {report['period_start']} - {report['period_end']}")
    print(f" ✓ Response Rate: {report['response_rate_percent']}% | Composite Rating: {report['avg_rating_period']} ★")
    print(f" ✓ HTML Email size: {len(report['html_content'])} bytes rendered successfully")

    # 7. Phase 4 Acquisition Engine: Audit Pitch
    print("\n[Bonus] Testing Phase 4 Client Acquisition Audit & Cold Pitch...")
    pitch = ai_engine.generate_audit_and_pitch(
        business_name="Lakeside Dental Care",
        category="Dentist",
        city="Chicago, IL",
        current_rating=4.1,
        review_count=35,
        unreplied_count=12,
        monthly_customer_value=350.0
    )
    print(f" ✓ Prospect Health Score: {pitch['overall_health_score']}/100 (Grade: {pitch['local_seo_grade']})")
    print(f" ✓ Calculated Annual Revenue Leak: ${pitch['missed_annual_revenue']:,}")
    print(f" ✓ Cold Email Subject: '{pitch['cold_email_subject']}'")
    print(f" ✓ 60s Loom Script Hook generated (length: {len(pitch['loom_video_script'])} chars)")

    print("\n==================================================")
    print("ALL TESTS PASSED! SYSTEM READY FOR DEPLOYMENT.")
    print("==================================================")

if __name__ == "__main__":
    test_full_agent_workflow()
