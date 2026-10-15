import random
from typing import List, Dict, Any
from datetime import datetime
from database import get_connection, get_keywords_for_business

class SEOTracker:
    """
    Manages local SEO keywords, tracking rank positions, local 3-pack visibility,
    and simulated rank fluctuations based on review activity.
    """

    def get_rankings(self, business_id: str) -> List[Dict[str, Any]]:
        return get_keywords_for_business(business_id)

    def refresh_keyword_ranks(self, business_id: str) -> List[Dict[str, Any]]:
        """
        Simulates fresh SERP position checks, updating ranks and pack status.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM keyword_ranks WHERE business_id = ?", (business_id,))
        rows = [dict(r) for r in cursor.fetchall()]

        updated = []
        for r in rows:
            prev = r["current_rank"]
            # Small realistic fluctuation (+1, -1, or same)
            delta = random.choice([-1, 0, 1])
            new_rank = max(1, min(15, prev + delta))
            in_pack = 1 if new_rank <= 3 else 0

            cursor.execute("""
            UPDATE keyword_ranks
            SET previous_rank = ?,
                current_rank = ?,
                in_local_pack = ?,
                checked_at = ?
            WHERE id = ?
            """, (prev, new_rank, in_pack, datetime.utcnow().isoformat(), r["id"]))
            
            r["previous_rank"] = prev
            r["current_rank"] = new_rank
            r["in_local_pack"] = bool(in_pack)
            updated.append(r)

        conn.commit()
        conn.close()
        return updated

    def add_keyword(self, business_id: str, keyword: str, search_volume: int = 500) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        kw_id = f"kw-{int(datetime.utcnow().timestamp())}"
        current_rank = random.randint(2, 7)
        in_pack = 1 if current_rank <= 3 else 0
        
        cursor.execute("""
        INSERT INTO keyword_ranks VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kw_id, business_id, keyword.strip(), current_rank,
            current_rank + 1, search_volume, in_pack, datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        return {
            "id": kw_id,
            "keyword": keyword,
            "current_rank": current_rank,
            "in_local_pack": bool(in_pack)
        }

seo_tracker = SEOTracker()
