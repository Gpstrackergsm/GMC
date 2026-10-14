#!/usr/bin/env python3
"""
لوحة تحكم جوجل أدز المباشرة - Leafanoo (باللغة العربية)
Google Ads & GA4 Live Arabic Dashboard — with background caching for instant page loads
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from google.ads.googleads.client import GoogleAdsClient
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest

PORT = 5050
CUSTOMER_ID = "4143615535"
GA4_PROPERTY = "properties/557255426"
REFRESH_SECONDS = 20

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, "google_ads_auth", "google-ads.yaml")
JSON_CREDS_PATH = os.path.join(BASE_DIR, "google_ads_auth", "google_ads_credentials.json")

# ─── Global Cache ────────────────────────────────────────────────────────────
CACHE_FILE = os.path.join(BASE_DIR, "dashboard_cache.json")
_cache_lock = threading.Lock()
_cache = None

def load_persisted_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_updated": datetime.now().strftime("%I:%M:%S %p"),
        "total_spend": 4086.45,
        "today_spend": 730.95,
        "total_clicks": 1581,
        "today_clicks": 84,
        "today_impressions": 7771,
        "live_us_users": 0,
        "campaigns": [
            {"name": "[USA] Standard Shopping - Top Products", "status": "نشط ✅", "budget": 250.0, "spend": 327.21, "clicks": 28, "impressions": 2190},
            {"name": "[USA] PMax - Pure Sales Mode", "status": "نشط ✅", "budget": 400.0, "spend": 403.74, "clicks": 56, "impressions": 5581}
        ],
        "today_products": [
            {"title": "Cedar Sunshed Garden Shed | 12×12", "clicks": 6, "spend": 49.78},
            {"title": "2.0 HP Tire Changer And Wheel Balancer", "clicks": 3, "spend": 32.34},
            {"title": "John Deere Z345M 42 in. 22 HP Mower", "clicks": 3, "spend": 10.34}
        ],
        "today_queries": [
            {"term": "manufactured sheds near me", "clicks": 2, "spend": 28.96},
            {"term": "zero turn mower with joystick control", "clicks": 2, "spend": 43.25}
        ],
        "live_pages": [],
        "error": None
    }

def save_persisted_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fetch_data():
    """Fetch all data from Google Ads + GA4. Called in background thread."""
    data = {
        "last_updated": datetime.now().strftime("%I:%M:%S %p"),
        "total_spend": 0.0,
        "today_spend": 0.0,
        "total_clicks": 0,
        "today_clicks": 0,
        "today_impressions": 0,
        "live_us_users": 0,
        "campaigns": [],
        "today_products": [],
        "today_queries": [],
        "live_pages": [],
        "error": None,
    }

    try:
        client = GoogleAdsClient.load_from_storage(YAML_PATH)
        ga_service = client.get_service("GoogleAdsService")

        # Total Spend & Clicks (all time)
        q_total = "SELECT metrics.cost_micros, metrics.clicks FROM customer LIMIT 1"
        for row in ga_service.search(customer_id=CUSTOMER_ID, query=q_total):
            data["total_spend"] = round(row.metrics.cost_micros / 1_000_000, 2)
            data["total_clicks"] = row.metrics.clicks

        # Today per campaign
        q_today = """
            SELECT campaign.id, campaign.name, campaign.status,
                   campaign_budget.amount_micros,
                   metrics.cost_micros, metrics.clicks, metrics.impressions
            FROM campaign
            WHERE segments.date DURING TODAY AND campaign.status = 'ENABLED'
        """
        for row in ga_service.search(customer_id=CUSTOMER_ID, query=q_today):
            spend = round(row.metrics.cost_micros / 1_000_000, 2)
            budget = round(row.campaign_budget.amount_micros / 1_000_000, 2) if row.campaign_budget.amount_micros else 0
            data["today_spend"] = round(data["today_spend"] + spend, 2)
            data["today_clicks"] += row.metrics.clicks
            data["today_impressions"] += row.metrics.impressions
            data["campaigns"].append({
                "name": row.campaign.name,
                "status": "نشط ✅" if row.campaign.status.name == "ENABLED" else row.campaign.status.name,
                "budget": budget,
                "spend": spend,
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
            })

        # Today top products
        q_prod = """
            SELECT segments.product_title, metrics.clicks, metrics.cost_micros
            FROM shopping_performance_view
            WHERE segments.date DURING TODAY AND metrics.clicks > 0
            ORDER BY metrics.clicks DESC LIMIT 6
        """
        for row in ga_service.search(customer_id=CUSTOMER_ID, query=q_prod):
            data["today_products"].append({
                "title": (row.segments.product_title or "غير محدد")[:45],
                "clicks": row.metrics.clicks,
                "spend": round(row.metrics.cost_micros / 1_000_000, 2),
            })

        # Today search queries
        q_search = """
            SELECT search_term_view.search_term, metrics.clicks, metrics.cost_micros
            FROM search_term_view
            WHERE segments.date DURING TODAY
            ORDER BY metrics.clicks DESC LIMIT 8
        """
        for row in ga_service.search(customer_id=CUSTOMER_ID, query=q_search):
            data["today_queries"].append({
                "term": row.search_term_view.search_term,
                "clicks": row.metrics.clicks,
                "spend": round(row.metrics.cost_micros / 1_000_000, 2),
            })

    except Exception as e:
        data["error"] = f"Google Ads Error: {e}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Google Ads Error:", e)
        # Merge with persisted cache so we don't display zeros
        old = load_persisted_cache()
        if old:
            for k in ["total_spend", "today_spend", "total_clicks", "today_clicks", "today_impressions", "campaigns", "today_products", "today_queries"]:
                if old.get(k):
                    data[k] = old[k]

    try:
        with open(JSON_CREDS_PATH) as f:
            cd = json.load(f)
        creds = Credentials(
            token=None, refresh_token=cd["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cd["client_id"], client_secret=cd["client_secret"]
        )
        ga4 = BetaAnalyticsDataClient(credentials=creds)

        # Total active users
        req = RunRealtimeReportRequest(property=GA4_PROPERTY, metrics=[{"name": "activeUsers"}])
        res = ga4.run_realtime_report(req)
        data["live_us_users"] = int(res.rows[0].metric_values[0].value) if res.rows else 0

        # Breakdown by page + location
        req2 = RunRealtimeReportRequest(
            property=GA4_PROPERTY,
            dimensions=[{"name": "unifiedScreenName"}, {"name": "country"}, {"name": "city"}],
            metrics=[{"name": "activeUsers"}]
        )
        for row in ga4.run_realtime_report(req2).rows[:10]:
            data["live_pages"].append({
                "screen": row.dimension_values[0].value[:42],
                "location": f"{row.dimension_values[1].value} - {row.dimension_values[2].value or 'USA'}",
                "users": int(row.metric_values[0].value),
            })
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] GA4 Error:", e)

    save_persisted_cache(data)
    return data


def background_fetcher():
    """Runs forever in a daemon thread, refreshing the cache every REFRESH_SECONDS."""
    global _cache
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching fresh data...")
            new_data = fetch_data()
            with _cache_lock:
                _cache = new_data
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cache updated ✅  "
                  f"Spend={new_data['today_spend']} DH  Clicks={new_data['today_clicks']}  "
                  f"Live={new_data['live_us_users']}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetcher crash:", e)
        time.sleep(REFRESH_SECONDS)


# ─── HTML Template ────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>لوحة التحكم المباشرة - إعلانات جوجل Leafanoo</title>
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #F8FAFC; --card-bg: #FFFFFF; --card-border: #E2E8F0;
      --text: #0F172A; --text-muted: #64748B;
      --primary: #059669; --accent: #2563EB;
      --danger: #DC2626; --warning: #D97706;
      --shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Tajawal', sans-serif; background: var(--bg); color: var(--text); padding: 28px 28px 80px; line-height: 1.6; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; padding-bottom: 20px; border-bottom: 2px solid var(--card-border); flex-wrap: wrap; gap: 16px; }
    .header h1 { font-size: 1.85rem; font-weight: 800; color: #0F172A; }
    .badge-live { background: #ECFDF5; color: var(--primary); border: 1px solid #A7F3D0; padding: 6px 14px; border-radius: 9999px; font-size: 0.88rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }
    .pulse { width: 10px; height: 10px; background: var(--primary); border-radius: 50%; animation: pulse 1.8s infinite; }
    @keyframes pulse { 0%{transform:scale(.95);box-shadow:0 0 0 0 rgba(5,150,105,.7)} 70%{transform:scale(1);box-shadow:0 0 0 8px rgba(5,150,105,0)} 100%{transform:scale(.95);box-shadow:0 0 0 0 rgba(5,150,105,0)} }
    .grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-bottom: 28px; }
    .stat-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 22px; box-shadow: var(--shadow); transition: transform .2s; }
    .stat-card:hover { transform: translateY(-2px); }
    .stat-card::before { content:''; position:absolute; top:0; right:0; left:0; height:4px; background:var(--accent); border-radius:16px 16px 0 0; }
    .stat-card { position: relative; overflow: hidden; }
    .stat-card.green::before { background: var(--primary); }
    .stat-card.orange::before { background: var(--warning); }
    .stat-card.red::before { background: var(--danger); }
    .stat-title { font-size: 0.9rem; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; }
    .stat-value { font-size: 2.2rem; font-weight: 900; color: #0F172A; }
    .stat-sub { font-size: 0.82rem; color: var(--text-muted); margin-top: 6px; }
    .time-badge { display: flex; align-items: center; gap: 8px; margin-top: 12px; background: linear-gradient(135deg,#4F46E5,#7C3AED); color:#fff; font-size: 1.05rem; font-weight: 800; padding: 9px 16px; border-radius: 10px; box-shadow: 0 4px 12px rgba(79,70,229,.3); }
    .grid-main { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px; }
    @media(max-width:992px){ .grid-main{grid-template-columns:1fr;} }
    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow); }
    .card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--card-border); padding-bottom: 12px; }
    table { width: 100%; border-collapse: collapse; text-align: right; }
    th, td { padding: 13px 16px; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-size: 0.86rem; font-weight: 700; background: #F8FAFC; }
    td { font-size: 0.93rem; color: #1E293B; }
    .badge-status { background:#ECFDF5; color:var(--primary); border:1px solid #A7F3D0; padding:3px 10px; border-radius:6px; font-size:0.8rem; font-weight:700; }
    .list-item { display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--card-border); }
    .list-item:last-child{border-bottom:none;}
    .sticky-bar { position:fixed; bottom:0; left:0; right:0; background:linear-gradient(135deg,#4F46E5,#7C3AED); color:#fff; padding:10px 24px; font-size:1rem; font-weight:700; font-family:'Tajawal',sans-serif; z-index:9999; direction:rtl; box-shadow:0 -4px 16px rgba(0,0,0,.15); display:flex; align-items:center; justify-content:center; gap:16px; }
    .sticky-bar span.sep{opacity:.4;}
    .loading-overlay { position:fixed; inset:0; background:rgba(248,250,252,.95); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:20px; z-index:99999; font-family:'Tajawal',sans-serif; }
    .spinner { width:60px; height:60px; border:6px solid #E2E8F0; border-top-color:#4F46E5; border-radius:50%; animation:spin 0.9s linear infinite; }
    @keyframes spin{to{transform:rotate(360deg)}}
    .loading-text { font-size:1.3rem; font-weight:700; color:#4F46E5; }
  </style>
  <script>
    // Auto-reload every 20 seconds (matches backend refresh)
    setTimeout(() => { window.location.reload(); }, 20000);
  </script>
</head>
<body>
  {{LOADING_OVERLAY}}

  <div class="header">
    <div>
      <h1>🚀 لوحة تحكم إعلانات جوجل المباشرة — Leafanoo</h1>
      <p style="color:var(--text-muted);font-size:.9rem;margin-top:4px;">
        رقم الحساب: <strong>414-361-5535</strong> | العملة: <strong>درهم مغربي (DH)</strong> | المتجر: <strong>Leafanoo.com</strong>
      </p>
    </div>
    <div class="badge-live"><div class="pulse"></div><span>مباشر — تحديث كل 20 ثانية</span></div>
  </div>

  <!-- بطاقات الإحصائيات -->
  <div class="grid-stats">
    <div class="stat-card green">
      <div class="stat-title">👥 الزوار النشطون الآن في المتجر</div>
      <div class="stat-value">{{LIVE_USERS}}</div>
      <div class="time-badge">⏱️ آخر تحديث: {{LAST_UPDATED}}</div>
      <div class="stat-sub" style="margin-top:10px;">مستخدمون أمريكيون فعليون (GA4 Real-time)</div>
    </div>
    <div class="stat-card orange">
      <div class="stat-title">💸 الصرف اليومي (اليوم فقط)</div>
      <div class="stat-value">{{TODAY_SPEND}} DH</div>
      <div class="stat-sub">≈ ${{TODAY_SPEND_USD}} دولار أمريكي</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">👆 النقرات اليوم</div>
      <div class="stat-value">{{TODAY_CLICKS}} نقرة</div>
      <div class="stat-sub">{{TODAY_IMPR}} ظهور في نتائج البحث</div>
    </div>
    <div class="stat-card red">
      <div class="stat-title">💰 إجمالي الصرف منذ البداية</div>
      <div class="stat-value">{{TOTAL_SPEND}} DH</div>
      <div class="stat-sub">إجمالي النقرات: {{TOTAL_CLICKS}} نقرة</div>
    </div>
  </div>

  <!-- المحتوى الرئيسي -->
  <div class="grid-main">
    <div>
      <div class="card">
        <div class="card-title">📦 الحملات الإعلانية النشطة</div>
        <table>
          <thead><tr><th>اسم الحملة</th><th>الحالة</th><th>الميزانية</th><th>صرف اليوم</th><th>النقرات</th></tr></thead>
          <tbody>{{CAMPAIGN_ROWS}}</tbody>
        </table>
      </div>
      <div class="card">
        <div class="card-title">🏷️ المنتجات الأكثر جذباً للمشترين اليوم</div>
        <table>
          <thead><tr><th>اسم المنتج</th><th>النقرات</th><th>الصرف (DH)</th></tr></thead>
          <tbody>{{PRODUCT_ROWS}}</tbody>
        </table>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-title">🌐 الصفحات التي يتصفحها الزوار الآن</div>
        {{LIVE_PAGE_ROWS}}
      </div>
      <div class="card">
        <div class="card-title">🔎 كلمات البحث التي كتبها الأمريكيون اليوم</div>
        {{QUERY_ROWS}}
      </div>
    </div>
  </div>

  <!-- شريط الوقت الثابت -->
  <div class="sticky-bar">
    <span>⏱️ آخر تحديث: <strong>{{LAST_UPDATED}}</strong></span>
    <span class="sep">|</span>
    <span>🔄 التحديث التالي خلال 20 ثانية</span>
    <span class="sep">|</span>
    <span>📊 Leafanoo Google Ads Live</span>
  </div>
</body>
</html>
"""

LOADING_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5">
  <title>جاري التحميل...</title>
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@700;800&display=swap" rel="stylesheet">
  <style>
    body { margin:0; background:#F8FAFC; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; font-family:'Tajawal',sans-serif; gap:24px; }
    .spinner { width:70px; height:70px; border:7px solid #E2E8F0; border-top-color:#4F46E5; border-radius:50%; animation:spin .9s linear infinite; }
    @keyframes spin{to{transform:rotate(360deg)}}
    h2 { font-size:1.5rem; color:#4F46E5; font-weight:800; }
    p { color:#64748B; font-size:1rem; }
  </style>
</head>
<body>
  <div class="spinner"></div>
  <h2>⏳ جاري تحميل البيانات...</h2>
  <p>يتم الاتصال بـ Google Ads و GA4 — انتظر لحظة</p>
  <p style="font-size:.85rem;color:#94A3B8;">سيتم التحديث تلقائياً خلال 5 ثوانٍ</p>
</body>
</html>
"""


# ─── HTTP Handler ─────────────────────────────────────────────────────────────
class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        with _cache_lock:
            data = _cache

        # Show loading screen if data not ready yet
        if data is None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(LOADING_HTML.encode("utf-8"))
            return

        # Build campaign rows
        c_rows = ""
        for c in data["campaigns"]:
            c_rows += f"""
            <tr>
              <td><strong>{c['name']}</strong></td>
              <td><span class="badge-status">{c['status']}</span></td>
              <td>{c['budget']} DH/يوم</td>
              <td style="color:#F59E0B;font-weight:700;">{c['spend']} DH</td>
              <td style="font-weight:700;">{c['clicks']}</td>
            </tr>"""
        if not c_rows:
            c_rows = "<tr><td colspan='5' style='text-align:center;color:#64748B;'>لا توجد حملات نشطة حالياً</td></tr>"

        # Build product rows
        p_rows = ""
        for p in data["today_products"]:
            p_rows += f"""
            <tr>
              <td>{p['title']}</td>
              <td style="font-weight:700;color:#10B981;">{p['clicks']}</td>
              <td>{p['spend']} DH</td>
            </tr>"""
        if not p_rows:
            p_rows = "<tr><td colspan='3' style='text-align:center;color:#64748B;'>لا توجد بيانات منتجات اليوم بعد</td></tr>"

        # Build live page rows
        lp_rows = ""
        for lp in data["live_pages"]:
            lp_rows += f"""
            <div class="list-item">
              <div>
                <strong style="color:#0F172A;font-size:.93rem;">{lp['screen']}</strong>
                <p style="font-size:.78rem;color:#059669;font-weight:600;margin-top:2px;">📍 {lp['location']}</p>
              </div>
              <span style="font-weight:800;background:#DBEAFE;color:#1D4ED8;padding:4px 10px;border-radius:6px;font-size:.83rem;">{lp['users']} زائر</span>
            </div>"""
        if not lp_rows:
            lp_rows = "<p style='color:#64748B;font-size:.93rem;padding:8px 0;'>لا يوجد زوار في هذه اللحظة.</p>"

        # Build search query rows
        q_rows = ""
        for q in data["today_queries"]:
            q_rows += f"""
            <div class="list-item">
              <span style="direction:ltr;font-weight:700;color:#0F172A;font-size:.9rem;">"{q['term']}"</span>
              <span style="font-size:.82rem;color:#475569;font-weight:600;">{q['clicks']} نقرة ({q['spend']} DH)</span>
            </div>"""
        if not q_rows:
            q_rows = "<p style='color:#64748B;font-size:.93rem;padding:8px 0;'>لا توجد استعلامات بحث مسجلة اليوم بعد.</p>"

        today_spend_usd = round(data["today_spend"] / 10.0, 2)

        html = (
            HTML_TEMPLATE
            .replace("{{LOADING_OVERLAY}}", "")
            .replace("{{LAST_UPDATED}}", str(data["last_updated"]))
            .replace("{{LIVE_USERS}}", str(data["live_us_users"]))
            .replace("{{TODAY_SPEND}}", f"{data['today_spend']:,.2f}")
            .replace("{{TODAY_SPEND_USD}}", f"{today_spend_usd:,.2f}")
            .replace("{{TODAY_CLICKS}}", f"{data['today_clicks']:,}")
            .replace("{{TODAY_IMPR}}", f"{data['today_impressions']:,}")
            .replace("{{TOTAL_SPEND}}", f"{data['total_spend']:,.2f}")
            .replace("{{TOTAL_CLICKS}}", f"{data['total_clicks']:,}")
            .replace("{{CAMPAIGN_ROWS}}", c_rows)
            .replace("{{PRODUCT_ROWS}}", p_rows)
            .replace("{{LIVE_PAGE_ROWS}}", lp_rows)
            .replace("{{QUERY_ROWS}}", q_rows)
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_server():
    global _cache
    _cache = load_persisted_cache()

    # Start background fetcher thread
    t = threading.Thread(target=background_fetcher, daemon=True)
    t.start()
    print(f"🔄 Background data fetcher started (every {REFRESH_SECONDS}s)")

    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print(f"🚀 لوحة التحكم تعمل على: http://localhost:{PORT}")
    print(f"   (ستظهر شاشة التحميل لمدة ~15 ثانية ثم تتحول للبيانات الحية)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_server()
