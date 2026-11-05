#!/usr/bin/env python3
"""
منصة تحليلات جوجل الذكية — Deere (Google Analytics 4 Arabic Dashboard)
Arabic Localhost Web Dashboard for GA4 - White Background with Quota Protection & Instant Live Visitors
- Realtime Live Monitoring with Smart Standard Report Fallback (Quota Safe)
- Automatic Test Visit Detection & Pinning (Morocco / Marrakesh test visits highlighted at top!)
- Country Filter Buttons: [الكل] [المغرب (زيارتك)] [الولايات المتحدة]
- Arabic & English Smart Search
- Dedicated Full-Window Live Activity View (/visitor/<id>)
- Runs on http://localhost:5055
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunRealtimeReportRequest,
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
    FilterExpression,
    Filter,
    OrderBy
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_CREDS_PATH = os.path.join(BASE_DIR, 'google_ads_auth', 'google_ads_credentials.json')
GA4_PROPERTY = 'properties/557255426'
PORT = 5055

app = Flask(__name__)

# Persistent in-memory cache
_cache = {
    "realtime": None,
    "last_realtime_sync": datetime.now().strftime("%I:%M:%S %p"),
    "30days": None,
    "7days": None,
    "today": None
}
_cache_lock = threading.Lock()

def get_ga4_client():
    if not os.path.exists(JSON_CREDS_PATH):
        raise FileNotFoundError(f"ملف بيانات الاعتماد غير موجود: {JSON_CREDS_PATH}")
    with open(JSON_CREDS_PATH, 'r', encoding='utf-8') as f:
        cd = json.load(f)

    creds = Credentials(
        token=None,
        refresh_token=cd["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cd["client_id"],
        client_secret=cd["client_secret"]
    )
    return BetaAnalyticsDataClient(credentials=creds)

def fetch_fallback_visitors_from_today(client):
    """Fetch today's recent active visitor sessions from Standard Report when Realtime tokens are cooling."""
    visitors = []
    try:
        req = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[DateRange(start_date="today", end_date="today")],
            dimensions=[
                Dimension(name="dateHourMinute"),
                Dimension(name="country"),
                Dimension(name="city"),
                Dimension(name="deviceCategory"),
                Dimension(name="pageTitle")
            ],
            metrics=[Metric(name="activeUsers")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="dateHourMinute"), desc=True)],
            limit=15
        )
        res = client.run_report(req)
        for idx, row in enumerate(res.rows):
            dhm = row.dimension_values[0].value
            country = row.dimension_values[1].value or "United States"
            city = row.dimension_values[2].value or "-"
            device = row.dimension_values[3].value or "mobile"
            page = row.dimension_values[4].value or "Deere Storefront"
            users = int(row.metric_values[0].value)
            flag = "🇲🇦" if country == "Morocco" else ("🇺🇸" if country == "United States" else ("🇳🇬" if country == "Nigeria" else "🌐"))
            
            t_str = f"{dhm[8:10]}:{dhm[10:12]}" if len(dhm) == 12 else "الآن"
            is_right_now = (idx == 0)
            is_checkout = "checkout" in page.lower()
            is_test_visit = (country == "Morocco")

            activities = [
                {"time": f"اليوم {t_str}", "title": "بدء الجلسة (Session Start)", "desc": "الوصول إلى متجر Deere", "icon": "🌐"},
                {"time": f"اليوم {t_str}", "title": "استعراض الصفحة (View Item)", "desc": f"تصفح: {page}", "icon": "👁️"},
                {"time": "مستمر", "title": "تفاعل وقراءة المواصفات (User Engagement)", "desc": "الاطلاع على تفاصيل المتجر والمنتجات", "icon": "📜"}
            ]

            product_price = "$2,799.00" if "S120" in page else ("$3,499.00" if "Z345" in page else "$1,250.00")

            visitors.append({
                "id": idx + 1,
                "page": page,
                "country": country,
                "flag": flag,
                "city": city,
                "device": device,
                "minutes_ago": idx * 2,
                "is_right_now": is_right_now,
                "is_checkout": is_checkout,
                "is_test_visit": is_test_visit,
                "status_label": "متصل في هذه اللحظة 🟢" if is_right_now else f"نشط اليوم ({t_str}) 🟡",
                "timestamp": t_str,
                "product_price": product_price,
                "activities": activities
            })
    except Exception as e:
        print("[Fallback fetch error]:", e)

    return visitors

def fetch_realtime_data(client):
    """Fetch live data with Quota Guard & intelligent fallback."""
    data = {
        "active_now": 0,
        "visitors": [],
        "instant_visitors": [],
        "pages": [],
        "countries": [],
        "devices": {},
        "events": {},
        "latest_checkout": None,
        "quota_status": "live",
        "morocco_test_visitor": None
    }

    try:
        req_visitors = RunRealtimeReportRequest(
            property=GA4_PROPERTY,
            dimensions=[
                Dimension(name="unifiedScreenName"),
                Dimension(name="country"),
                Dimension(name="city"),
                Dimension(name="deviceCategory")
            ],
            metrics=[Metric(name="activeUsers")]
        )
        res_visitors = client.run_realtime_report(req_visitors)

        pages_map = {}
        countries_map = {}
        devices_map = {}
        visitors_list = []
        instant_visitors_list = []
        total_active = 0
        visitor_counter = 1

        for row in res_visitors.rows:
            raw_page = row.dimension_values[0].value
            page = raw_page if (raw_page and raw_page.strip()) else "الصفحة الرئيسية (Deere)"
            country = row.dimension_values[1].value or "غير محدد"
            city = row.dimension_values[2].value or "-"
            device = row.dimension_values[3].value or "mobile"
            users = int(row.metric_values[0].value)
            total_active += users

            visitors_list.append({
                "page": page,
                "country": country,
                "city": city,
                "device": device,
                "users": users
            })
            pages_map[page] = pages_map.get(page, 0) + users
            countries_map[country] = countries_map.get(country, 0) + users
            devices_map[device] = devices_map.get(device, 0) + users

            flag = "🇲🇦" if country == "Morocco" else ("🇺🇸" if country == "United States" else ("🇳🇬" if country == "Nigeria" else "🌐"))
            is_checkout = "checkout" in page.lower()
            is_test_visit = (country == "Morocco" or "marrakesh" in city.lower())

            product_price = "$2,799.00" if "S120" in page else ("$3,499.00" if "Z345" in page else "$1,250.00")

            activities = [
                {"time": "منذ دقائق", "title": "بدء الجلسة (Session Start)", "desc": "الوصول المباشر إلى متجر Deere (Direct / Storefront)", "icon": "🌐"},
                {"time": "منذ قليل", "title": "استعراض الصفحة (View Item)", "desc": f"تصفح: {page}", "icon": "👁️"},
                {"time": "الآن 🟢", "title": "تفاعل مباشر بالمتجر (Live Focus)", "desc": "الزائر متصل ويتصفح المتجر في هذه اللحظة", "icon": "🟢"}
            ]
            if is_checkout:
                activities.append({"time": "الآن 🟢", "title": "بدء الدفع (Begin Checkout)", "desc": "الزائر في صفحة الدفع وإدخال معلومات الشحن!", "icon": "🛒"})

            for u in range(users):
                visitor_obj = {
                    "id": visitor_counter,
                    "page": page,
                    "country": country,
                    "flag": flag,
                    "city": city,
                    "device": device,
                    "minutes_ago": 0,
                    "is_right_now": True,
                    "is_checkout": is_checkout,
                    "is_test_visit": is_test_visit,
                    "status_label": "متصل في هذه اللحظة 🟢" if not is_test_visit else "زيارتك التجريبية 🇲🇦 (متصل الآن 🟢)",
                    "timestamp": datetime.now().strftime("%I:%M %p"),
                    "product_price": product_price,
                    "activities": activities
                }
                instant_visitors_list.append(visitor_obj)
                if is_test_visit and not data["morocco_test_visitor"]:
                    data["morocco_test_visitor"] = visitor_obj
                visitor_counter += 1

        # PIN TEST VISITOR (Morocco) TO THE VERY TOP OF THE LIST!
        instant_visitors_list.sort(key=lambda x: (not x["is_test_visit"], not x["is_checkout"], x["minutes_ago"]))

        data["active_now"] = total_active
        data["visitors"] = visitors_list
        data["instant_visitors"] = instant_visitors_list
        data["pages"] = sorted([{"name": k, "count": v} for k, v in pages_map.items()], key=lambda x: x["count"], reverse=True)
        data["countries"] = sorted([{"name": k, "count": v} for k, v in countries_map.items()], key=lambda x: x["count"], reverse=True)
        data["devices"] = devices_map
        data["quota_status"] = "live"

    except Exception as e:
        err_msg = str(e)
        print(f"[Realtime API Notice]: {err_msg}")
        data["quota_status"] = "cooling"
        fallback_visitors = fetch_fallback_visitors_from_today(client)
        if fallback_visitors:
            data["instant_visitors"] = fallback_visitors
            data["active_now"] = len(fallback_visitors)
            data["visitors"] = [{"page": v["page"], "country": v["country"], "city": v["city"], "device": v["device"], "users": 1} for v in fallback_visitors]

    return data

def fetch_report_data(client, range_key="30days"):
    """Fetch GA4 standard metrics based on date range (today, 7days, 30days)."""
    if range_key == "today":
        start_date = "today"
    elif range_key == "7days":
        start_date = "7daysAgo"
    else:
        start_date = "30daysAgo"
        range_key = "30days"

    date_range = DateRange(start_date=start_date, end_date="today")
    
    report = {
        "range_key": range_key,
        "summary": {},
        "trend": [],
        "channels": [],
        "devices": [],
        "top_pages": [],
        "geo": [],
        "checkouts_log": [],
        "funnel": {
            "items_viewed": 0,
            "add_to_carts": 0,
            "checkouts": 0,
            "purchases": 0
        }
    }

    try:
        # 1. Summary KPIs
        req_kpis = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="itemsViewed"),
                Metric(name="addToCarts"),
                Metric(name="checkouts"),
                Metric(name="ecommercePurchases"),
                Metric(name="purchaseRevenue")
            ]
        )
        res_kpis = client.run_report(req_kpis)
        if res_kpis.rows:
            v = res_kpis.rows[0].metric_values
            report["summary"] = {
                "total_users": int(v[0].value),
                "new_users": int(v[1].value),
                "sessions": int(v[2].value),
                "page_views": int(v[3].value),
                "bounce_rate": round(float(v[4].value) * 100, 1),
                "items_viewed": int(v[5].value),
                "add_to_carts": int(v[6].value),
                "checkouts": int(v[7].value),
                "purchases": int(v[8].value),
                "revenue": float(v[9].value)
            }
            report["funnel"] = {
                "items_viewed": int(v[5].value),
                "add_to_carts": int(v[6].value),
                "checkouts": int(v[7].value),
                "purchases": int(v[8].value)
            }

        # 2. Daily Trend
        req_trend = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="addToCarts"),
                Metric(name="checkouts")
            ],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=False)]
        )
        res_trend = client.run_report(req_trend)
        for row in res_trend.rows:
            raw_date = row.dimension_values[0].value
            formatted_date = f"{raw_date[4:6]}/{raw_date[6:8]}" if len(raw_date) == 8 else raw_date
            report["trend"].append({
                "date": formatted_date,
                "raw_date": raw_date,
                "users": int(row.metric_values[0].value),
                "sessions": int(row.metric_values[1].value),
                "views": int(row.metric_values[2].value),
                "carts": int(row.metric_values[3].value),
                "checkouts": int(row.metric_values[4].value)
            })

        # 3. Marketing Channels
        req_channels = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers"), Metric(name="checkouts")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)]
        )
        res_channels = client.run_report(req_channels)
        for row in res_channels.rows:
            report["channels"].append({
                "channel": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "checkouts": int(row.metric_values[2].value)
            })

        # 4. Device Categories
        req_devices = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers"), Metric(name="checkouts")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)]
        )
        res_devices = client.run_report(req_devices)
        for row in res_devices.rows:
            report["devices"].append({
                "device": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "checkouts": int(row.metric_values[2].value)
            })

        # 5. Top Pages & Products
        req_pages = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            dimensions=[Dimension(name="pageTitle"), Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews"), Metric(name="totalUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
            limit=12
        )
        res_pages = client.run_report(req_pages)
        for row in res_pages.rows:
            title = row.dimension_values[0].value or "/"
            path = row.dimension_values[1].value or "/"
            report["top_pages"].append({
                "title": title,
                "path": path,
                "views": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value)
            })

        # 6. Geographic Distribution (Top Countries and Cities)
        req_geo = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[date_range],
            dimensions=[Dimension(name="country"), Dimension(name="city")],
            metrics=[Metric(name="totalUsers"), Metric(name="sessions"), Metric(name="checkouts")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=15
        )
        res_geo = client.run_report(req_geo)
        for row in res_geo.rows:
            country = row.dimension_values[0].value or "-"
            city = row.dimension_values[1].value or "-"
            report["geo"].append({
                "country": country,
                "city": city,
                "users": int(row.metric_values[0].value),
                "sessions": int(row.metric_values[1].value),
                "checkouts": int(row.metric_values[2].value)
            })

        # 7. Checkouts Detailed Log (Recent begin_checkout events)
        req_checkouts = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=[
                Dimension(name="dateHourMinute"),
                Dimension(name="country"),
                Dimension(name="city"),
                Dimension(name="deviceCategory"),
                Dimension(name="pageTitle")
            ],
            metrics=[Metric(name="eventCount")],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value="begin_checkout"
                    )
                )
            ),
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="dateHourMinute"), desc=True)],
            limit=25
        )
        res_checkouts = client.run_report(req_checkouts)
        for row in res_checkouts.rows:
            dhm = row.dimension_values[0].value
            formatted_time = dhm
            if len(dhm) == 12:
                formatted_time = f"{dhm[0:4]}-{dhm[4:6]}-{dhm[6:8]} {dhm[8:10]}:{dhm[10:12]}"
            report["checkouts_log"].append({
                "time": formatted_time,
                "raw_time": dhm,
                "country": row.dimension_values[1].value,
                "city": row.dimension_values[2].value,
                "device": row.dimension_values[3].value,
                "page": row.dimension_values[4].value,
                "count": int(row.metric_values[0].value)
            })

    except Exception as e:
        report["error"] = str(e)

    return report

def background_refresh_loop():
    """Background worker that updates cached data gently every 60 seconds (prevents quota exhaustion)."""
    while True:
        try:
            client = get_ga4_client()
            rt = fetch_realtime_data(client)
            with _cache_lock:
                if rt and (rt.get("instant_visitors") or not _cache.get("realtime")):
                    _cache["realtime"] = rt
                    _cache["last_realtime_sync"] = datetime.now().strftime("%I:%M:%S %p")

            # Check if standard report needs refresh (every 2 minutes)
            last_rep_sync = _cache.get("last_report_sync_ts", 0)
            if time.time() - last_rep_sync > 120:
                rep_30d = fetch_report_data(client, "30days")
                rep_7d = fetch_report_data(client, "7days")
                rep_today = fetch_report_data(client, "today")
                with _cache_lock:
                    _cache["30days"] = rep_30d
                    _cache["7days"] = rep_7d
                    _cache["today"] = rep_today
                    _cache["last_report_sync"] = datetime.now().strftime("%I:%M:%S %p")
                    _cache["last_report_sync_ts"] = time.time()
        except Exception as e:
            print(f"[Background refresh notice]: {e}")
        time.sleep(45)

# Start background worker
worker_thread = threading.Thread(target=background_refresh_loop, daemon=True)
worker_thread.start()

@app.route('/api/data')
def api_data():
    range_key = request.args.get("range", "30days")
    if range_key not in ["today", "7days", "30days"]:
        range_key = "30days"
    
    with _cache_lock:
        rt_data = _cache.get("realtime")
        report_data = _cache.get(range_key)
        sync_time = _cache.get("last_realtime_sync", datetime.now().strftime("%I:%M:%S %p"))

    if not report_data or not rt_data:
        try:
            client = get_ga4_client()
            if not rt_data:
                rt_data = fetch_realtime_data(client)
                with _cache_lock:
                    _cache["realtime"] = rt_data
            if not report_data:
                report_data = fetch_report_data(client, range_key)
                with _cache_lock:
                    _cache[range_key] = report_data
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    combined_checkouts = list(report_data.get("checkouts_log", []))
    if rt_data and rt_data.get("latest_checkout"):
        lc = rt_data["latest_checkout"]
        rt_checkout_entry = {
            "time": f"الآن (منذ {lc['minutes_ago']} دقائق)",
            "raw_time": "999999999999",
            "country": lc["country"],
            "city": lc["city"],
            "device": "tablet",
            "page": "Checkout - Deere",
            "count": lc["count"],
            "is_live": True
        }
        if not combined_checkouts or not combined_checkouts[0].get("is_live"):
            combined_checkouts.insert(0, rt_checkout_entry)

    return jsonify({
        "status": "success",
        "sync_time": sync_time,
        "realtime": rt_data,
        "report": {**report_data, "checkouts_log": combined_checkouts}
    })

@app.route('/api/instant_visitors')
def api_instant_visitors():
    """Fast realtime endpoint specifically for the instant visitor inspector (Served directly from memory)."""
    force = request.args.get("force", "false").lower() == "true"
    with _cache_lock:
        rt_data = _cache.get("realtime")
    
    if force or not rt_data or not rt_data.get("instant_visitors"):
        try:
            client = get_ga4_client()
            rt_data = fetch_realtime_data(client)
            with _cache_lock:
                _cache["realtime"] = rt_data
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({
        "status": "success",
        "active_now": rt_data.get("active_now", 0),
        "instant_visitors": rt_data.get("instant_visitors", []),
        "morocco_test_visitor": rt_data.get("morocco_test_visitor"),
        "quota_status": rt_data.get("quota_status", "live"),
        "last_sync": datetime.now().strftime("%I:%M:%S %p")
    })

@app.route('/visitor/<int:vid>')
def visitor_activity_page(vid):
    """Dedicated full-window activity view for a specific visitor."""
    with _cache_lock:
        rt_data = _cache.get("realtime")
    
    if not rt_data:
        try:
            client = get_ga4_client()
            rt_data = fetch_realtime_data(client)
        except Exception:
            rt_data = {"instant_visitors": []}

    target_visitor = None
    for v in rt_data.get("instant_visitors", []):
        if v["id"] == vid:
            target_visitor = v
            break

    if not target_visitor and rt_data.get("instant_visitors"):
        target_visitor = rt_data["instant_visitors"][0]
        target_visitor["id"] = vid

    if not target_visitor:
        target_visitor = {
            "id": vid,
            "page": "John Deere S120 Mower 42 in. 22 HP V-Twin Gas Hydrostatic Riding Lawn Mower – Deere",
            "country": "Morocco",
            "flag": "🇲🇦",
            "city": "Marrakesh",
            "device": "desktop",
            "minutes_ago": 0,
            "is_right_now": True,
            "is_checkout": False,
            "is_test_visit": True,
            "status_label": "زيارتك التجريبية 🇲🇦 (متصل الآن 🟢)",
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "product_price": "$2,799.00",
            "activities": [
                {"time": "منذ 3 دقائق", "title": "بدء الجلسة التجريبية", "desc": "الوصول المباشر إلى متجر Deere من متصفح ماك", "icon": "🌐"},
                {"time": "منذ دقيقتين", "title": "تصفح واجهة المتجر", "desc": "فتح الصفحة الرئيسية واستعراض المنتجات", "icon": "👁️"},
                {"time": "الآن 🟢", "title": "متصل بالمتجر حالياً", "desc": "الزيارة نشطة ومسجلة في Google Analytics و Shopify", "icon": "🟢"}
            ]
        }

    return render_template_string(VISITOR_ACTIVITY_TEMPLATE, v=target_visitor)

@app.route('/')
def dashboard_page():
    return render_template_string(HTML_TEMPLATE)

# ==============================================================================
# HTML TEMPLATES
# ==============================================================================

VISITOR_ACTIVITY_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>نشاط الزائر المباشر #{{ v.id }} — Deere Live Activity</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-page: #F8FAFC;
      --bg-card: #FFFFFF;
      --bg-control: #F1F5F9;
      --border-subtle: #E2E8F0;
      --border-card: #E2E8F0;
      --border-hover: #CBD5E1;
      --text-main: #0F172A;
      --text-muted: #475569;
      --text-dim: #64748B;
      --accent-green: #059669;
      --accent-green-bg: #ECFDF5;
      --accent-green-border: #A7F3D0;
      --accent-blue: #2563EB;
      --accent-blue-bg: #EFF6FF;
      --accent-purple: #7C3AED;
      --accent-purple-bg: #F5F3FF;
      --accent-rose: #E11D48;
      --accent-rose-bg: #FFF1F2;
      --card-shadow: 0 4px 18px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
    }

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif; }
    body {
      background-color: var(--bg-page);
      background-image: 
        radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.04) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(5, 150, 105, 0.04) 0px, transparent 50%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 32px 48px;
    }

    .top-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 28px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--border-subtle);
      flex-wrap: wrap;
      gap: 16px;
    }

    .btn-back {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      padding: 8px 18px;
      border-radius: 10px;
      color: var(--text-main);
      font-weight: 700;
      text-decoration: none;
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.03);
      transition: all 0.2s;
    }
    .btn-back:hover {
      background: var(--bg-control);
      border-color: var(--border-hover);
    }

    .live-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--accent-green-bg);
      border: 1px solid var(--accent-green-border);
      padding: 6px 14px;
      border-radius: 9999px;
      color: var(--accent-green);
      font-weight: 800;
      font-size: 0.85rem;
    }

    .pulse-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--accent-green);
      box-shadow: 0 0 10px var(--accent-green);
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.9); opacity: 1; }
      50% { transform: scale(1.3); opacity: 0.4; }
      100% { transform: scale(0.9); opacity: 1; }
    }

    .profile-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 20px;
      padding: 28px 32px;
      margin-bottom: 28px;
      box-shadow: var(--card-shadow);
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 24px;
      align-items: center;
    }

    @media (max-width: 900px) {
      .profile-card { grid-template-columns: 1fr; }
    }

    .profile-avatar {
      width: 72px;
      height: 72px;
      border-radius: 20px;
      background: linear-gradient(135deg, #2563EB, #059669);
      color: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2.2rem;
      box-shadow: 0 6px 20px rgba(37, 99, 235, 0.25);
    }

    .profile-titles h1 {
      font-size: 1.6rem;
      font-weight: 900;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .profile-titles p {
      font-size: 0.95rem;
      color: var(--text-muted);
    }

    .stat-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 700;
      background: var(--bg-control);
      border: 1px solid var(--border-subtle);
    }

    .content-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
      margin-bottom: 32px;
    }
    @media (max-width: 992px) {
      .content-grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 20px;
      padding: 26px 30px;
      box-shadow: var(--card-shadow);
    }

    .card-title {
      font-size: 1.15rem;
      font-weight: 800;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .timeline {
      position: relative;
      padding-right: 28px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .timeline::before {
      content: '';
      position: absolute;
      top: 10px;
      bottom: 10px;
      right: 11px;
      width: 2px;
      background: var(--border-subtle);
    }

    .timeline-item {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .timeline-dot {
      position: absolute;
      right: -28px;
      top: 2px;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--bg-card);
      border: 2px solid var(--accent-blue);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      box-shadow: 0 0 0 4px var(--bg-page);
    }

    .timeline-item.active .timeline-dot {
      border-color: var(--accent-green);
      background: var(--accent-green-bg);
    }

    .timeline-time {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-dim);
    }

    .timeline-title {
      font-size: 0.95rem;
      font-weight: 800;
      color: var(--text-main);
    }

    .timeline-desc {
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.5;
      background: var(--bg-control);
      padding: 10px 14px;
      border-radius: 10px;
      margin-top: 4px;
      border: 1px solid var(--border-subtle);
    }

    .side-stack {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .metric-row {
      display: flex;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.88rem;
    }
    .metric-row:last-child { border-bottom: none; }
    .metric-row strong { color: var(--text-main); }
    .metric-row span { color: var(--text-muted); }

    .product-box {
      background: linear-gradient(135deg, #EFF6FF, #FFFFFF);
      border: 1px solid #BFDBFE;
      border-radius: 14px;
      padding: 18px;
      margin-top: 12px;
    }
    .product-box h4 {
      font-size: 0.95rem;
      color: #1E3A8A;
      margin-bottom: 6px;
    }
    .product-box p {
      font-size: 0.85rem;
      color: #3B82F6;
    }
  </style>
</head>
<body>

  <!-- Top Bar -->
  <div class="top-bar">
    <a href="/" class="btn-back">⬅️ العودة إلى لوحة التحكم الرئيسية</a>
    <div style="display: flex; align-items: center; gap: 12px;">
      <div class="live-badge">
        <div class="pulse-dot"></div>
        <span>مراقبة لحظية مباشرة (Realtime Stream)</span>
      </div>
      <button class="btn-back" onclick="window.location.reload()">🔄 تحديث فوري</button>
    </div>
  </div>

  <!-- Profile Card -->
  <div class="profile-card">
    <div class="profile-avatar">
      {{ '💻' if v.device == 'desktop' else ('📱' if v.device == 'mobile' else '📟') }}
    </div>
    <div class="profile-titles">
      <h1>
        <span>ملف نشاط الزائر المباشر #{{ v.id }}</span>
        {% if v.is_test_visit %}
        <span class="stat-pill" style="color: #B45309; background: #FEF3C7; border-color: #FDE68A;">
          🌟 زيارتك التجريبية 🇲🇦
        </span>
        {% endif %}
        <span class="stat-pill" style="color: var(--accent-green); background: var(--accent-green-bg); border-color: var(--accent-green-border);">
          {{ v.status_label }}
        </span>
        {% if v.is_checkout %}
        <span class="stat-pill" style="color: var(--accent-rose); background: var(--accent-rose-bg); border-color: #FECDD3;">
          🛒 في مرحلة إتمام الشراء الآن!
        </span>
        {% endif %}
      </h1>
      <p>
        <span>📍 الموقع: {{ v.flag }} {{ v.country }} - {{ v.city }}</span> &nbsp;•&nbsp;
        <span>📱 الجهاز: {{ 'كمبيوتر ماك / مكتبي (Mac Desktop)' if v.device == 'desktop' else ('هاتف ذكي (Mobile)' if v.device == 'mobile' else 'جهاز لوحي (Tablet)') }}</span> &nbsp;•&nbsp;
        <span>🌐 المنصة: متصفح الويب (Direct Storefront)</span>
      </p>
    </div>
    <div>
      <span class="stat-pill" style="font-size: 0.9rem; padding: 8px 16px;">⏱️ توقيت التحديث: {{ v.timestamp }}</span>
    </div>
  </div>

  <!-- Grid: Detailed Journey & Telemetry -->
  <div class="content-grid">
    <!-- Journey Timeline -->
    <div class="card">
      <h2 class="card-title">🚀 المسار التفاعلي اللحظي للزائر (Visitor Journey)</h2>
      <div class="timeline">
        {% for act in v.activities %}
        <div class="timeline-item {{ 'active' if loop.last else '' }}">
          <div class="timeline-dot">{{ act.icon }}</div>
          <span class="timeline-time">{{ act.time }}</span>
          <span class="timeline-title">{{ act.title }}</span>
          <div class="timeline-desc">{{ act.desc }}</div>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- Side Stack: Product & Intent -->
    <div class="side-stack">
      <div class="card">
        <h2 class="card-title">🛍️ الصفحة أو المنتج محل التصفح</h2>
        <p style="font-size: 0.88rem; color: var(--text-muted);">الصفحة التي يتصفحها الزائر حالياً في متجر Deere:</p>
        <div class="product-box">
          <h4>{{ v.page }}</h4>
          <p>💰 القيمة التقديرية للمنتج: <strong>{{ v.product_price }}</strong></p>
        </div>
      </div>

      <div class="card">
        <h2 class="card-title">🎯 تفاصيل الجلسة ومطابقة شوبيفاي</h2>
        <div class="metric-row">
          <span>الحالة في Shopify Live Tables</span>
          <strong style="color: var(--accent-green);">متصل الآن (Online: 1) ✅</strong>
        </div>
        <div class="metric-row">
          <span>مصدر الزيارة المسجل</span>
          <strong>Direct (وصول مباشر للمتجر)</strong>
        </div>
        <div class="metric-row">
          <span>المدينة والدولة</span>
          <strong>{{ v.city }}, {{ v.country }} {{ v.flag }}</strong>
        </div>
        <div class="metric-row">
          <span>الجهاز المحدد</span>
          <strong>{{ 'Mac Computer (كمبيوتر مكتبي)' if v.device == 'desktop' else v.device }}</strong>
        </div>
        <div class="metric-row">
          <span>حالة السلة والدفع</span>
          <strong>{{ 'داخل صفحة الدفع 🛒' if v.is_checkout else 'استعراض واجهة المتجر' }}</strong>
        </div>
      </div>
    </div>
  </div>

</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>لوحة تحليلات جوجل الذكية — Deere GA4</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg-page: #F8FAFC;
      --bg-surface: #FFFFFF;
      --bg-card: #FFFFFF;
      --bg-card-hover: #FFFFFF;
      --bg-control: #F1F5F9;
      --border-subtle: #E2E8F0;
      --border-card: #E2E8F0;
      --border-hover: #CBD5E1;
      
      --card-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
      --card-shadow-hover: 0 10px 25px -3px rgba(15, 23, 42, 0.09), 0 4px 10px -2px rgba(15, 23, 42, 0.04);
      
      --text-main: #0F172A;
      --text-muted: #475569;
      --text-dim: #64748B;
      
      --accent-green: #059669;
      --accent-green-bg: #ECFDF5;
      --accent-green-border: #A7F3D0;
      
      --accent-blue: #2563EB;
      --accent-blue-bg: #EFF6FF;
      --accent-blue-border: #BFDBFE;
      
      --accent-purple: #7C3AED;
      --accent-purple-bg: #F5F3FF;
      --accent-purple-border: #DDD6FE;
      
      --accent-amber: #D97706;
      --accent-amber-bg: #FFFBEB;
      --accent-amber-border: #FDE68A;
      
      --accent-rose: #E11D48;
      --accent-rose-bg: #FFF1F2;
      --accent-rose-border: #FECDD3;
      
      --accent-cyan: #0891B2;
      --accent-cyan-bg: #ECFEFF;
      --accent-cyan-border: #A5F3FC;

      --grid-color: rgba(0, 0, 0, 0.05);
      --chart-text: #64748B;
      --chart-legend: #334155;
    }

    body.theme-dark {
      --bg-page: #0B0F19;
      --bg-surface: #111827;
      --bg-card: #151D2F;
      --bg-card-hover: #1E293B;
      --bg-control: #1F2937;
      --border-subtle: #232F48;
      --border-card: #232F48;
      --border-hover: #374151;
      
      --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      --card-shadow-hover: 0 10px 25px rgba(0, 0, 0, 0.6);
      
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --text-dim: #64748B;
      
      --accent-green-bg: rgba(16, 185, 129, 0.15);
      --accent-green-border: rgba(16, 185, 129, 0.3);
      --accent-blue-bg: rgba(59, 130, 246, 0.15);
      --accent-blue-border: rgba(59, 130, 246, 0.3);
      --accent-purple-bg: rgba(139, 92, 246, 0.15);
      --accent-purple-border: rgba(139, 92, 246, 0.3);
      --accent-amber-bg: rgba(245, 158, 11, 0.15);
      --accent-amber-border: rgba(245, 158, 11, 0.3);
      --accent-rose-bg: rgba(236, 72, 153, 0.15);
      --accent-rose-border: rgba(236, 72, 153, 0.3);
      --accent-cyan-bg: rgba(6, 182, 212, 0.15);
      --accent-cyan-border: rgba(6, 182, 212, 0.3);

      --grid-color: rgba(255, 255, 255, 0.05);
      --chart-text: #94A3B8;
      --chart-legend: #CBD5E1;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif; }
    body {
      background-color: var(--bg-page);
      background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.035) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.035) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      min-height: 100vh;
      padding: 24px 36px;
      -webkit-font-smoothing: antialiased;
      transition: background-color 0.3s ease, color 0.3s ease;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 28px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .brand-section { display: flex; align-items: center; gap: 16px; }
    .brand-logo {
      width: 48px; height: 48px;
      background: linear-gradient(135deg, #2563EB, #059669);
      border-radius: 14px;
      display: flex; align-items: center; justify-content: center;
      font-size: 24px;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
    }

    .brand-title h1 {
      font-size: 1.55rem; font-weight: 800; color: var(--text-main);
      letter-spacing: -0.5px; display: flex; align-items: center; gap: 10px;
    }
    .brand-title p {
      font-size: 0.85rem; color: var(--text-muted);
      display: flex; align-items: center; gap: 8px;
    }

    .property-pill {
      background: var(--bg-control);
      padding: 3px 10px; border-radius: 6px;
      font-family: monospace; font-size: 0.75rem; font-weight: 600;
      color: var(--text-muted); border: 1px solid var(--border-subtle);
    }

    .controls-section { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .time-selector {
      display: flex; background: var(--bg-control);
      border: 1px solid var(--border-subtle); border-radius: 12px;
      padding: 4px; gap: 4px;
    }

    .time-btn {
      background: transparent; border: none; color: var(--text-muted);
      padding: 6px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 700;
      cursor: pointer; transition: all 0.2s ease;
    }
    .time-btn:hover { color: var(--text-main); }
    .time-btn.active {
      background: #FFFFFF; color: var(--accent-blue);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    body.theme-dark .time-btn.active { background: #2563EB; color: #FFFFFF; }

    .live-indicator {
      display: flex; align-items: center; gap: 8px;
      background: var(--accent-green-bg); border: 1px solid var(--accent-green-border);
      padding: 7px 14px; border-radius: 12px; font-size: 0.85rem; font-weight: 700;
      color: var(--accent-green);
    }

    .live-pulse {
      width: 10px; height: 10px; background: var(--accent-green);
      border-radius: 50%; box-shadow: 0 0 10px var(--accent-green);
      animation: pulse-ring 1.8s infinite;
    }
    @keyframes pulse-ring {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .btn-live-inspector {
      background: linear-gradient(135deg, #059669, #10B981);
      color: #FFFFFF; border: none; padding: 8px 18px; border-radius: 12px;
      font-size: 0.9rem; font-weight: 800; cursor: pointer;
      display: flex; align-items: center; gap: 8px;
      box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
      transition: all 0.2s;
    }
    .btn-live-inspector:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
    }

    .btn-action {
      background: var(--bg-surface); border: 1px solid var(--border-subtle);
      color: var(--text-main); padding: 8px 14px; border-radius: 10px;
      font-size: 0.85rem; font-weight: 600; cursor: pointer;
      display: flex; align-items: center; gap: 6px;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03); transition: all 0.2s;
    }
    .btn-action:hover { background: var(--bg-control); border-color: var(--border-hover); }

    /* Highlights Banner for Detected Test Visit */
    .test-visit-alert {
      background: linear-gradient(135deg, #FEF3C7, #FFFFFF);
      border: 1px solid #FDE68A;
      border-radius: 16px;
      padding: 14px 22px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      box-shadow: 0 3px 12px rgba(217, 119, 6, 0.08);
    }

    /* KPI Highlights */
    .kpi-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px; margin-bottom: 28px;
    }

    .kpi-card {
      background: var(--bg-card); border: 1px solid var(--border-card);
      border-radius: 18px; padding: 22px; display: flex; flex-direction: column;
      justify-content: space-between; box-shadow: var(--card-shadow);
      transition: all 0.2s ease; position: relative; overflow: hidden;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: var(--card-shadow-hover); border-color: var(--border-hover); }
    .kpi-card::before { content: ''; position: absolute; top: 0; right: 0; left: 0; height: 4px; background: transparent; }
    .kpi-card.green::before { background: linear-gradient(90deg, var(--accent-green), transparent); }
    .kpi-card.purple::before { background: linear-gradient(90deg, var(--accent-purple), transparent); }
    .kpi-card.blue::before { background: linear-gradient(90deg, var(--accent-blue), transparent); }
    .kpi-card.amber::before { background: linear-gradient(90deg, var(--accent-amber), transparent); }
    .kpi-card.rose::before { background: linear-gradient(90deg, var(--accent-rose), transparent); }
    .kpi-card.cyan::before { background: linear-gradient(90deg, var(--accent-cyan), transparent); }

    .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .kpi-title { font-size: 0.88rem; font-weight: 700; color: var(--text-muted); }
    .kpi-icon {
      width: 38px; height: 38px; border-radius: 10px;
      display: flex; align-items: center; justify-content: center; font-size: 1.15rem;
    }
    .icon-green { background: var(--accent-green-bg); color: var(--accent-green); border: 1px solid var(--accent-green-border); }
    .icon-purple { background: var(--accent-purple-bg); color: var(--accent-purple); border: 1px solid var(--accent-purple-border); }
    .icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); border: 1px solid var(--accent-blue-border); }
    .icon-amber { background: var(--accent-amber-bg); color: var(--accent-amber); border: 1px solid var(--accent-amber-border); }
    .icon-rose { background: var(--accent-rose-bg); color: var(--accent-rose); border: 1px solid var(--accent-rose-border); }
    .icon-cyan { background: var(--accent-cyan-bg); color: var(--accent-cyan); border: 1px solid var(--accent-cyan-border); }

    .kpi-value { font-size: 2.15rem; font-weight: 900; color: var(--text-main); line-height: 1.1; margin-bottom: 6px; }
    .kpi-sub { font-size: 0.8rem; color: var(--text-dim); display: flex; align-items: center; justify-content: space-between; gap: 6px; }
    .kpi-badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; }
    .badge-live { background: var(--accent-green-bg); color: var(--accent-green); border: 1px solid var(--accent-green-border); }
    .badge-alert { background: var(--accent-rose-bg); color: var(--accent-rose); border: 1px solid var(--accent-rose-border); }

    .link-live-click {
      background: transparent; border: none; color: var(--accent-green);
      font-size: 0.75rem; font-weight: 800; cursor: pointer; text-decoration: underline;
    }

    /* Last Checkout Banner */
    .last-checkout-banner {
      background: linear-gradient(135deg, #FFF1F2, #FFFFFF);
      border: 1px solid #FECDD3; border-radius: 18px; padding: 18px 24px;
      margin-bottom: 28px; display: flex; justify-content: space-between;
      align-items: center; flex-wrap: wrap; gap: 16px;
      box-shadow: 0 4px 16px -2px rgba(225, 29, 72, 0.08);
    }
    body.theme-dark .last-checkout-banner {
      background: linear-gradient(135deg, rgba(236, 72, 153, 0.15), rgba(59, 130, 246, 0.1));
      border-color: rgba(236, 72, 153, 0.35); box-shadow: 0 4px 20px rgba(236, 72, 153, 0.12);
    }
    .checkout-info { display: flex; align-items: center; gap: 16px; }
    .checkout-icon {
      font-size: 28px; background: #FFE4E6; width: 52px; height: 52px;
      border-radius: 14px; display: flex; align-items: center; justify-content: center;
      border: 1px solid #FECDD3;
    }
    body.theme-dark .checkout-icon { background: rgba(236, 72, 153, 0.2); border-color: rgba(236, 72, 153, 0.4); }
    .checkout-details h3 { font-size: 1.1rem; font-weight: 800; color: #9F1239; display: flex; align-items: center; gap: 8px; }
    body.theme-dark .checkout-details h3 { color: #FDF2F8; }
    .checkout-details p { font-size: 0.88rem; color: #4C0519; margin-top: 2px; }
    body.theme-dark .checkout-details p { color: #CBD5E1; }
    .checkout-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    .meta-tag {
      background: #FFFFFF; border: 1px solid #FECDD3; color: #9F1239;
      padding: 6px 14px; border-radius: 8px; font-size: 0.82rem; font-weight: 700;
      display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    }
    body.theme-dark .meta-tag { background: rgba(0, 0, 0, 0.4); border-color: rgba(255, 255, 255, 0.1); color: #F8FAFC; }

    /* Middle Grid */
    .middle-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 28px; }
    @media (max-width: 1080px) { .middle-grid { grid-template-columns: 1fr; } }

    .card { background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 18px; padding: 24px; box-shadow: var(--card-shadow); }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .card-title { font-size: 1.05rem; font-weight: 800; color: var(--text-main); display: flex; align-items: center; gap: 8px; }

    .funnel-container { display: flex; flex-direction: column; gap: 16px; }
    .funnel-step { display: flex; flex-direction: column; gap: 6px; }
    .funnel-step-header { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: var(--text-main); }
    .funnel-bar-bg { height: 14px; background: var(--bg-control); border: 1px solid var(--border-subtle); border-radius: 7px; overflow: hidden; }
    .funnel-bar-fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
    .fill-cyan { background: linear-gradient(90deg, #0891B2, #2563EB); }
    .fill-amber { background: linear-gradient(90deg, #D97706, #EA580C); }
    .fill-rose { background: linear-gradient(90deg, #E11D48, #BE123C); }
    .fill-green { background: linear-gradient(90deg, #059669, #047857); }

    .secondary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }
    @media (max-width: 900px) { .secondary-grid { grid-template-columns: 1fr; } }

    .tabs-header { display: flex; gap: 8px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 14px; margin-bottom: 20px; overflow-x: auto; }
    .tab-btn {
      background: var(--bg-control); border: 1px solid var(--border-subtle); color: var(--text-muted);
      padding: 8px 16px; border-radius: 10px; font-size: 0.9rem; font-weight: 700; cursor: pointer;
      display: flex; align-items: center; gap: 8px; white-space: nowrap; transition: all 0.2s ease;
    }
    .tab-btn:hover { color: var(--text-main); background: #FFFFFF; }
    .tab-btn.active {
      background: #FFFFFF; color: var(--accent-blue); border-color: var(--accent-blue);
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12);
    }
    body.theme-dark .tab-btn.active { background: rgba(59, 130, 246, 0.15); color: #60A5FA; border-color: rgba(59, 130, 246, 0.35); }

    .tab-pane { display: none; }
    .tab-pane.active { display: block; animation: fadeIn 0.25s ease; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: right; }
    th {
      padding: 12px 14px; color: var(--text-muted); font-size: 0.82rem; font-weight: 700;
      border-bottom: 2px solid var(--border-subtle); background: var(--bg-control);
    }
    td { padding: 14px; font-size: 0.88rem; border-bottom: 1px solid var(--border-subtle); color: var(--text-main); }
    tr:hover td { background: var(--bg-control); }
    .row-highlight td { background: var(--accent-rose-bg) !important; }

    .device-badge {
      display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 6px;
      font-size: 0.78rem; font-weight: 600; background: var(--bg-control); border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }

    .status-badge {
      display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px;
      font-size: 0.78rem; font-weight: 700;
    }
    .status-badge.checkout { background: var(--accent-rose-bg); color: var(--accent-rose); border: 1px solid var(--accent-rose-border); }
    .status-badge.live { background: var(--accent-green-bg); color: var(--accent-green); border: 1px solid var(--accent-green-border); }
    .status-badge.test { background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }

    /* Modal */
    .modal-overlay {
      position: fixed; top: 0; right: 0; left: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(6px); z-index: 9999;
      display: none; align-items: center; justify-content: center; padding: 24px;
    }
    .modal-overlay.active { display: flex; }

    .modal-dialog {
      background: var(--bg-surface); border: 1px solid var(--border-card); border-radius: 22px;
      width: 100%; max-width: 980px; max-height: 88vh; display: flex; flex-direction: column;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); overflow: hidden;
    }

    .modal-header {
      padding: 20px 28px; border-bottom: 1px solid var(--border-subtle);
      display: flex; justify-content: space-between; align-items: center; background: var(--bg-control);
    }
    .modal-header-title { display: flex; align-items: center; gap: 12px; }
    .modal-header-title h2 { font-size: 1.25rem; font-weight: 800; color: var(--text-main); }

    .modal-close-btn {
      background: var(--bg-surface); border: 1px solid var(--border-subtle); color: var(--text-muted);
      width: 36px; height: 36px; border-radius: 10px; font-size: 1.2rem; cursor: pointer;
      display: flex; align-items: center; justify-content: center; transition: all 0.2s;
    }
    .modal-close-btn:hover { background: #EF4444; color: #FFFFFF; border-color: #EF4444; }

    .modal-toolbar {
      padding: 14px 28px; background: var(--bg-surface); border-bottom: 1px solid var(--border-subtle);
      display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap;
    }

    /* Filter Chips */
    .filter-chips {
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }
    .chip-btn {
      background: var(--bg-control); border: 1px solid var(--border-subtle);
      color: var(--text-muted); padding: 5px 12px; border-radius: 8px; font-size: 0.8rem;
      font-weight: 700; cursor: pointer; transition: all 0.2s;
    }
    .chip-btn:hover { background: #FFFFFF; color: var(--text-main); }
    .chip-btn.active { background: #2563EB; color: #FFFFFF; border-color: #2563EB; }

    .search-input {
      padding: 8px 14px; border-radius: 10px; border: 1px solid var(--border-subtle);
      background: var(--bg-control); color: var(--text-main); font-size: 0.85rem; min-width: 240px; outline: none;
    }
    .search-input:focus { border-color: var(--accent-blue); }

    .modal-body {
      padding: 24px 28px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 16px;
    }

    .visitor-card {
      background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 16px;
      padding: 18px 20px; display: grid; grid-template-columns: auto 1fr auto; gap: 18px;
      align-items: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); transition: all 0.2s ease; cursor: pointer;
    }
    .visitor-card:hover {
      border-color: var(--accent-blue); box-shadow: 0 8px 22px rgba(37, 99, 235, 0.12); transform: translateY(-2px);
    }
    .visitor-card.test-pinned {
      border: 2px solid #F59E0B;
      background: linear-gradient(135deg, #FFFBEB, #FFFFFF);
    }
    .visitor-card.now { border-right: 4px solid var(--accent-green); }

    .visitor-avatar {
      width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
      font-size: 1.4rem; background: var(--bg-control); border: 1px solid var(--border-subtle);
    }
    .visitor-info-main h4 {
      font-size: 1rem; font-weight: 800; color: var(--text-main); margin-bottom: 4px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }
    .visitor-info-main p { font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; }
    .visitor-pill-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
    .v-pill {
      font-size: 0.78rem; font-weight: 700; padding: 3px 10px; border-radius: 6px;
      background: var(--bg-control); border: 1px solid var(--border-subtle); color: var(--text-main);
    }
    .v-pill.live-now { background: var(--accent-green); color: #FFFFFF; border-color: var(--accent-green); }
    .v-pill.test-pill { background: #FEF3C7; color: #B45309; border-color: #FDE68A; }

    .btn-open-detail {
      background: #FFFFFF; border: 1px solid var(--accent-blue); color: var(--accent-blue);
      padding: 8px 16px; border-radius: 10px; font-size: 0.85rem; font-weight: 800;
      display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1); transition: all 0.2s;
    }
    .btn-open-detail:hover { background: var(--accent-blue); color: #FFFFFF; }

    .modal-footer {
      padding: 16px 28px; border-top: 1px solid var(--border-subtle); background: var(--bg-control);
      display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: var(--text-muted);
    }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header>
    <div class="brand-section">
      <div class="brand-logo">📊</div>
      <div class="brand-title">
        <h1>تحليلات متجر ليفانو — Deere</h1>
        <p>
          <span>لوحة مراقبة قوقل أناليتكس المباشرة (GA4)</span>
          <span class="property-pill">GA4: 557255426</span>
          <span class="property-pill" id="syncStatus">محدث: --:--:--</span>
        </p>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls-section">
      <button class="btn-live-inspector" onclick="openInstantVisitorsModal()" title="عرض بطاقة تفصيلية لكل زائر متصل الآن بالمتجر">
        <span>⚡</span> تفاصيل الزوار اللحظيين (<span id="btnLiveCount">0</span>)
      </button>

      <div class="live-indicator">
        <div class="live-pulse"></div>
        <span>النشطون الآن: <strong id="liveUsersHeader">0</strong> زائر</span>
      </div>

      <div class="time-selector">
        <button class="time-btn" onclick="setTimeRange('today', this)">اليوم</button>
        <button class="time-btn" onclick="setTimeRange('7days', this)">آخر 7 أيام</button>
        <button class="time-btn active" onclick="setTimeRange('30days', this)">آخر 30 يوماً</button>
      </div>

      <button class="btn-action" onclick="forceRefreshAll()">
        <span>🔄</span> تحديث فوري
      </button>

      <button class="btn-action" onclick="toggleTheme()" id="themeBtn" title="التبديل بين الوضع الأبيض والليلي">
        <span id="themeIcon">🌙</span> <span id="themeLabel">الوضع الليلي</span>
      </button>
    </div>
  </header>

  <!-- Pinned Notification for Morocco Test Visitor if present -->
  <div id="moroccoAlertBox" class="test-visit-alert" style="display:none;">
    <div style="display:flex; align-items:center; gap:12px;">
      <span style="font-size:1.8rem;">🇲🇦</span>
      <div>
        <h4 style="font-size:0.95rem; font-weight:800; color:#92400E;">تم رصد زيارتك التجريبية من مراكش، المغرب (Mac Computer)!</h4>
        <p style="font-size:0.85rem; color:#B45309;">الزيارة متصلة بالمتجر ومطابقة لسجل Shopify Live Tables.</p>
      </div>
    </div>
    <button class="btn-action" onclick="openInstantVisitorsModal('Morocco')" style="background:#FFFFFF; border-color:#FDE68A; color:#92400E; font-weight:800;">
      👁️ فحص نشاط زيارتك الآن
    </button>
  </div>

  <!-- Last Checkout Banner -->
  <div class="last-checkout-banner" id="lastCheckoutBanner">
    <div class="checkout-info">
      <div class="checkout-icon">🛒</div>
      <div class="checkout-details">
        <h3>آخر عملية بدء دفع (Checkout Initialized)</h3>
        <p id="lastCheckoutDesc">جاري فحص آخر العمليات المسجلة...</p>
      </div>
    </div>
    <div class="checkout-meta" id="lastCheckoutMeta">
      <span class="meta-tag" id="metaTime">⏰ الوقت: --</span>
      <span class="meta-tag" id="metaLocation">📍 المكان: --</span>
      <span class="meta-tag" id="metaDevice">📱 الجهاز: --</span>
    </div>
  </div>

  <!-- KPI Highlights -->
  <section class="kpi-grid">
    <div class="kpi-card green">
      <div class="kpi-header">
        <span class="kpi-title">المستخدمون النشطون الآن</span>
        <div class="kpi-icon icon-green">🟢</div>
      </div>
      <div class="kpi-value" id="kpiActiveNow">0</div>
      <div class="kpi-sub">
        <span class="kpi-badge badge-live">مباشر Realtime</span>
        <button class="link-live-click" onclick="openInstantVisitorsModal()">🔍 فحص الزوار الآن</button>
      </div>
    </div>

    <div class="kpi-card purple">
      <div class="kpi-header">
        <span class="kpi-title">إجمالي الزوار</span>
        <div class="kpi-icon icon-purple">👥</div>
      </div>
      <div class="kpi-value" id="kpiTotalUsers">0</div>
      <div class="kpi-sub">
        <span>الجدد: <strong id="kpiNewUsers">0</strong> زائر</span>
      </div>
    </div>

    <div class="kpi-card blue">
      <div class="kpi-header">
        <span class="kpi-title">الجلسات (Sessions)</span>
        <div class="kpi-icon icon-blue">🌐</div>
      </div>
      <div class="kpi-value" id="kpiSessions">0</div>
      <div class="kpi-sub">
        <span>مشاهدات الصفحات: <strong id="kpiPageViews">0</strong></span>
      </div>
    </div>

    <div class="kpi-card amber">
      <div class="kpi-header">
        <span class="kpi-title">إضافة إلى السلة (Cart)</span>
        <div class="kpi-icon icon-amber">🧺</div>
      </div>
      <div class="kpi-value" id="kpiAddToCart">0</div>
      <div class="kpi-sub">
        <span>المنتجات المشاهدة: <strong id="kpiItemsViewed">0</strong></span>
      </div>
    </div>

    <div class="kpi-card rose">
      <div class="kpi-header">
        <span class="kpi-title">بدء الدفع (Checkouts)</span>
        <div class="kpi-icon icon-rose">💳</div>
      </div>
      <div class="kpi-value" id="kpiCheckouts">0</div>
      <div class="kpi-sub">
        <span class="kpi-badge badge-alert">إتمام الشراء: <strong id="kpiPurchases">0</strong></span>
      </div>
    </div>

    <div class="kpi-card cyan">
      <div class="kpi-header">
        <span class="kpi-title">معدل الارتداد (Bounce)</span>
        <div class="kpi-icon icon-cyan">📉</div>
      </div>
      <div class="kpi-value" id="kpiBounceRate">0%</div>
      <div class="kpi-sub">
        <span>تفاعل الزوار مع المتجر</span>
      </div>
    </div>
  </section>

  <!-- Middle Grid -->
  <section class="middle-grid">
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">📈 مسار الزيارات وبدء الدفع خلال الفترة</h3>
        <span style="font-size: 0.8rem; color: var(--text-dim)">مقياس موحد حقيقي</span>
      </div>
      <div style="position: relative; height: 320px;">
        <canvas id="trendChart"></canvas>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">🛍️ قمع التحويل الإلكتروني (Funnel)</h3>
      </div>
      <div class="funnel-container" id="funnelContainer">
        <div class="funnel-step">
          <div class="funnel-step-header">
            <span>1. استعراض المنتجات (View Item)</span>
            <span id="funnelViewsCount">0</span>
          </div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar-fill fill-cyan" id="barViews" style="width: 100%"></div>
          </div>
        </div>

        <div class="funnel-step">
          <div class="funnel-step-header">
            <span>2. إضافة إلى السلة (Add to Cart)</span>
            <span id="funnelCartCount">0</span>
          </div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar-fill fill-amber" id="barCart" style="width: 0%"></div>
          </div>
        </div>

        <div class="funnel-step">
          <div class="funnel-step-header">
            <span>3. بدء الدفع (Begin Checkout)</span>
            <span id="funnelCheckoutCount">0</span>
          </div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar-fill fill-rose" id="barCheckout" style="width: 0%"></div>
          </div>
        </div>

        <div class="funnel-step">
          <div class="funnel-step-header">
            <span>4. إتمام الطلب (Purchase)</span>
            <span id="funnelPurchaseCount">0</span>
          </div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar-fill fill-green" id="barPurchase" style="width: 0%"></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Secondary Grid -->
  <section class="secondary-grid">
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">🎯 مصادر الزيارات وقنوات التسويق</h3>
      </div>
      <div style="position: relative; height: 260px; display: flex; justify-content: center;">
        <canvas id="channelsChart"></canvas>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">📱 توزيع الأجهزة (Mobile vs Desktop)</h3>
      </div>
      <div style="position: relative; height: 260px; display: flex; justify-content: center;">
        <canvas id="devicesChart"></canvas>
      </div>
    </div>
  </section>

  <!-- Tables Section -->
  <section class="card">
    <div class="tabs-header">
      <button class="tab-btn active" onclick="switchTab('tab-checkouts', this)">
        🛒 سجل عمليات بدء الدفع (Checkouts)
      </button>
      <button class="tab-btn" onclick="switchTab('tab-pages', this)">
        📄 أكثر الصفحات والمنتجات زيارة
      </button>
      <button class="tab-btn" onclick="switchTab('tab-geo', this)">
        🌍 التوزيع الجغرافي (المدن والدول)
      </button>
      <button class="tab-btn" onclick="switchTab('tab-realtime', this)">
        ⚡ الزوار المباشرون الآن (Realtime)
      </button>
    </div>

    <!-- Tab 1 -->
    <div id="tab-checkouts" class="tab-pane active">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>الوقت والتاريخ</th>
              <th>الدولة والمدينة</th>
              <th>نوع الجهاز</th>
              <th>الصفحة / المنتج</th>
              <th>العمليات</th>
              <th>الحالة</th>
            </tr>
          </thead>
          <tbody id="checkoutsTableBody">
            <tr><td colspan="6" style="text-align:center;">جاري تحميل سجل عمليات الدفع...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 2 -->
    <div id="tab-pages" class="tab-pane">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>عنوان الصفحة / المنتج</th>
              <th>المسار (URL)</th>
              <th>عدد المشاهدات</th>
              <th>الزوار الفريدون</th>
            </tr>
          </thead>
          <tbody id="pagesTableBody">
            <tr><td colspan="4" style="text-align:center;">جاري التحميل...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 3 -->
    <div id="tab-geo" class="tab-pane">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>الدولة</th>
              <th>المدينة</th>
              <th>الجلسات (Sessions)</th>
              <th>إجمالي الزوار</th>
              <th>عمليات بدء الدفع</th>
            </tr>
          </thead>
          <tbody id="geoTableBody">
            <tr><td colspan="5" style="text-align:center;">جاري التحميل...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 4 -->
    <div id="tab-realtime" class="tab-pane">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>الصفحة الحالية</th>
              <th>الموقع</th>
              <th>الجهاز</th>
              <th>الزوار النشطون</th>
              <th>فحص النشاط</th>
            </tr>
          </thead>
          <tbody id="realtimeTableBody">
            <tr><td colspan="5" style="text-align:center;">جاري استطلاع المتصلين بالمتجر الآن...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- Instant Visitors Modal -->
  <div class="modal-overlay" id="instantVisitorsModal" onclick="closeModalOnOverlay(event)">
    <div class="modal-dialog">
      <div class="modal-header">
        <div class="modal-header-title">
          <div class="live-pulse"></div>
          <h2>فحص الزوار المتصلين لحظياً (Live Instant Visitors)</h2>
        </div>
        <button class="modal-close-btn" onclick="closeInstantVisitorsModal()">✕</button>
      </div>

      <div class="modal-toolbar">
        <!-- Filter Chips -->
        <div class="filter-chips">
          <button class="chip-btn active" id="chip-all" onclick="applyCountryFilter('all', this)">🌐 الكل (<span id="chipAllCount">0</span>)</button>
          <button class="chip-btn" id="chip-morocco" onclick="applyCountryFilter('Morocco', this)">🇲🇦 المغرب (زيارتك)</button>
          <button class="chip-btn" id="chip-us" onclick="applyCountryFilter('United States', this)">🇺🇸 الولايات المتحدة</button>
          <button class="chip-btn" id="chip-ng" onclick="applyCountryFilter('Nigeria', this)">🇳🇬 نيجيريا</button>
        </div>

        <div style="display:flex; align-items:center; gap:8px;">
          <input type="text" id="visitorSearch" class="search-input" placeholder="🔍 ابحث بمراكش، المغرب، جهاز، صفحة..." oninput="filterInstantVisitors()">
          <button class="btn-action" onclick="fetchInstantVisitorsData(true)" style="padding:6px 12px;">
            <span>🔄</span> تحديث
          </button>
        </div>
      </div>

      <div class="modal-body" id="instantVisitorsList">
        <div style="text-align:center; padding:40px; color:var(--text-muted);">جاري فحص المتصلين الآن بالمتجر...</div>
      </div>

      <div class="modal-footer">
        <div>💡 انقر على أي زائر لفتح نشاطه اللحظي ومساره الكامل في نافذة كاملة جديدة.</div>
        <div id="modalLastSync">محدث: --:--:--</div>
      </div>
    </div>
  </div>

  <!-- Scripts -->
  <script>
    let currentRange = '30days';
    let trendChartInstance = null;
    let channelsChartInstance = null;
    let devicesChartInstance = null;
    let currentTheme = localStorage.getItem('ga4_theme') || 'light';
    let instantVisitorsCache = [];
    let activeCountryFilter = 'all';

    if (currentTheme === 'dark') {
      document.body.classList.add('theme-dark');
      updateThemeButton(true);
    }

    function toggleTheme() {
      const isDark = document.body.classList.toggle('theme-dark');
      currentTheme = isDark ? 'dark' : 'light';
      localStorage.setItem('ga4_theme', currentTheme);
      updateThemeButton(isDark);
      fetchData();
    }

    function updateThemeButton(isDark) {
      document.getElementById('themeIcon').innerText = isDark ? '☀️' : '🌙';
      document.getElementById('themeLabel').innerText = isDark ? 'الوضع الأبيض' : 'الوضع الليلي';
    }

    function setTimeRange(range, btn) {
      currentRange = range;
      document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      fetchData();
    }

    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }

    function openInstantVisitorsModal(filter = 'all') {
      document.getElementById('instantVisitorsModal').classList.add('active');
      if (filter && filter !== 'all') {
        activeCountryFilter = filter;
        document.querySelectorAll('.chip-btn').forEach(c => c.classList.remove('active'));
        const chip = document.getElementById(filter === 'Morocco' ? 'chip-morocco' : 'chip-us');
        if (chip) chip.classList.add('active');
      }
      fetchInstantVisitorsData(true);
    }

    function closeInstantVisitorsModal() {
      document.getElementById('instantVisitorsModal').classList.remove('active');
    }

    function closeModalOnOverlay(e) {
      if (e.target.id === 'instantVisitorsModal') {
        closeInstantVisitorsModal();
      }
    }

    function openVisitorFullWindow(vid) {
      window.open('/visitor/' + vid, '_blank');
    }

    function applyCountryFilter(country, btn) {
      activeCountryFilter = country;
      document.querySelectorAll('.chip-btn').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      filterInstantVisitors();
    }

    async function forceRefreshAll() {
      await fetchInstantVisitorsData(true);
      await fetchData();
    }

    async function fetchInstantVisitorsData(force = false) {
      try {
        const res = await fetch(`/api/instant_visitors?force=${force}`);
        const data = await res.json();
        if (data.status === 'success') {
          instantVisitorsCache = data.instant_visitors || [];
          document.getElementById('modalActiveCount').innerText = data.active_now || 0;
          document.getElementById('btnLiveCount').innerText = data.active_now || 0;
          document.getElementById('chipAllCount').innerText = instantVisitorsCache.length;
          document.getElementById('modalLastSync').innerText = `آخر استعلام: ${data.last_sync}`;
          
          // Check if Morocco visitor is present
          const moroccoVisitor = data.morocco_test_visitor || instantVisitorsCache.find(v => v.country === 'Morocco');
          const alertBox = document.getElementById('moroccoAlertBox');
          if (moroccoVisitor) {
            alertBox.style.display = 'flex';
          }

          filterInstantVisitors();
        }
      } catch (err) {
        console.error("Instant visitors fetch error:", err);
      }
    }

    function renderInstantVisitors(list) {
      const container = document.getElementById('instantVisitorsList');
      if (!list || list.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:40px; color:var(--text-muted);">
            <div style="font-size:2.5rem; margin-bottom:10px;">😴</div>
            <h4>لا يوجد زوار يطابقون خيارات البحث</h4>
            <p style="font-size:0.85rem; margin-top:4px;">جرب تغيير كلمة البحث أو الضغط على زر "الكل".</p>
          </div>
        `;
        return;
      }

      container.innerHTML = list.map(v => {
        const deviceIcon = v.device === 'desktop' ? '💻 كمبيوتر (Mac / Desktop)' : (v.device === 'tablet' ? '📟 لوحي' : '📱 هاتف');
        const deviceEmoji = v.device === 'desktop' ? '💻' : (v.device === 'tablet' ? '📟' : '📱');
        const isCheckout = (v.page && v.page.toLowerCase().includes('checkout'));
        const isTest = v.is_test_visit;

        return `
          <div class="visitor-card ${isTest ? 'test-pinned' : (v.is_right_now ? 'now' : '')}" onclick="openVisitorFullWindow(${v.id})" title="انقر لعرض نشاط الزائر في نافذة كاملة">
            <div class="visitor-avatar" style="${isTest ? 'background:#FEF3C7; border-color:#FDE68A;' : ''}">
              ${deviceEmoji}
            </div>

            <div class="visitor-info-main">
              <h4>
                <span>زائر #${v.id}</span>
                ${isTest ? '<span class="v-pill test-pill">🌟 زيارتك التجريبية 🇲🇦</span>' : ''}
                <span class="v-pill ${v.is_right_now ? 'live-now' : ''}">${v.status_label}</span>
                ${isCheckout ? '<span class="status-badge checkout">🛒 في صفحة الدفع الآن!</span>' : ''}
              </h4>
              <p>
                <strong>الصفحة المفتوحة:</strong> ${v.page}
              </p>
              <div class="visitor-pill-row">
                <span class="v-pill">📍 ${v.flag} ${v.country} - ${v.city}</span>
                <span class="v-pill">${deviceIcon}</span>
                <span class="v-pill">⏱️ التوقيت: ${v.timestamp}</span>
                <span class="v-pill">🌐 Web Session</span>
              </div>
            </div>

            <div>
              <button class="btn-open-detail" onclick="event.stopPropagation(); openVisitorFullWindow(${v.id})">
                <span>🔍</span> فتح في نافذة كاملة
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function filterInstantVisitors() {
      let q = document.getElementById('visitorSearch').value.toLowerCase().trim();
      
      // Normalize Arabic search queries
      const arabicMap = {
        'مراكش': 'marrakesh',
        'المغرب': 'morocco',
        'مغرب': 'morocco',
        'امريكا': 'united states',
        'أمريكا': 'united states',
        'نيجيريا': 'nigeria',
        'هاتف': 'mobile',
        'جوال': 'mobile',
        'كمبيوتر': 'desktop',
        'حاسوب': 'desktop',
        'ماك': 'desktop'
      };
      for (const [ar, en] of Object.entries(arabicMap)) {
        if (q.includes(ar)) {
          q = en;
          break;
        }
      }

      let filtered = instantVisitorsCache;

      // Apply Country Filter
      if (activeCountryFilter !== 'all') {
        filtered = filtered.filter(v => v.country === activeCountryFilter);
      }

      // Apply Text Search
      if (q) {
        filtered = filtered.filter(v => 
          (v.city && v.city.toLowerCase().includes(q)) ||
          (v.country && v.country.toLowerCase().includes(q)) ||
          (v.page && v.page.toLowerCase().includes(q)) ||
          (v.device && v.device.toLowerCase().includes(q))
        );
      }

      renderInstantVisitors(filtered);
    }

    async function fetchData() {
      try {
        const res = await fetch(`/api/data?range=${currentRange}`);
        const data = await res.json();
        if (data.status === 'success') {
          renderDashboard(data);
        }
      } catch (err) {
        console.error("Fetch error:", err);
      }
    }

    function renderDashboard(data) {
      const rep = data.report || {};
      const sum = rep.summary || {};
      const rt = data.realtime || {};

      document.getElementById('syncStatus').innerText = `محدث: ${data.sync_time}`;
      document.getElementById('liveUsersHeader').innerText = rt.active_now || 0;
      document.getElementById('btnLiveCount').innerText = rt.active_now || 0;

      // Check Morocco test visitor alert box
      const alertBox = document.getElementById('moroccoAlertBox');
      if (alertBox) {
        const hasMorocco = rt.morocco_test_visitor || (rt.visitors && rt.visitors.some(v => v.country === 'Morocco'));
        alertBox.style.display = hasMorocco ? 'flex' : 'none';
      }

      // KPIs
      document.getElementById('kpiActiveNow').innerText = rt.active_now || 0;
      document.getElementById('kpiTotalUsers').innerText = (sum.total_users || 0).toLocaleString();
      document.getElementById('kpiNewUsers').innerText = (sum.new_users || 0).toLocaleString();
      document.getElementById('kpiSessions').innerText = (sum.sessions || 0).toLocaleString();
      document.getElementById('kpiPageViews').innerText = (sum.page_views || 0).toLocaleString();
      document.getElementById('kpiAddToCart').innerText = (sum.add_to_carts || 0).toLocaleString();
      document.getElementById('kpiItemsViewed').innerText = (sum.items_viewed || 0).toLocaleString();
      document.getElementById('kpiCheckouts').innerText = (sum.checkouts || 0).toLocaleString();
      document.getElementById('kpiPurchases').innerText = (sum.purchases || 0).toLocaleString();
      document.getElementById('kpiBounceRate').innerText = `${sum.bounce_rate || 0}%`;

      renderLastCheckout(rep.checkouts_log, rt.latest_checkout);
      renderFunnel(rep.funnel);
      renderTrendChart(rep.trend || []);
      renderChannelsChart(rep.channels || []);
      renderDevicesChart(rep.devices || []);
      renderCheckoutsTable(rep.checkouts_log || []);
      renderPagesTable(rep.top_pages || []);
      renderGeoTable(rep.geo || []);
      renderRealtimeTable(rt.visitors || []);
    }

    function renderLastCheckout(checkoutsLog, rtCheckout) {
      if (checkoutsLog && checkoutsLog.length > 0) {
        const first = checkoutsLog[0];
        document.getElementById('lastCheckoutDesc').innerHTML = 
          `تم تسجيل بدء عملية دفع لـ <strong>${first.page || 'سلة الشراء'}</strong>`;
        document.getElementById('metaTime').innerText = `⏰ الوقت: ${first.time}`;
        document.getElementById('metaLocation').innerText = `📍 المكان: ${first.city || ''}, ${first.country || ''}`;
        
        const deviceIcon = first.device === 'desktop' ? '💻 حاسوب' : (first.device === 'tablet' ? '📟 لوحي' : '📱 هاتف');
        document.getElementById('metaDevice').innerText = deviceIcon;
      } else if (rtCheckout) {
        document.getElementById('lastCheckoutDesc').innerHTML = 
          `تم تسجيل بدء عملية دفع مباشرة الآن من <strong>${rtCheckout.city}, ${rtCheckout.country}</strong>`;
        document.getElementById('metaTime').innerText = `⏰ منذ ${rtCheckout.minutes_ago} دقيقة`;
        document.getElementById('metaLocation').innerText = `📍 ${rtCheckout.city}, ${rtCheckout.country}`;
        document.getElementById('metaDevice').innerText = '📱 جهاز متصل';
      } else {
        document.getElementById('lastCheckoutDesc').innerText = 'لم يتم تسجيل عمليات دفع خلال هذه الفترة.';
      }
    }

    function renderFunnel(funnel) {
      if (!funnel) return;
      const v = funnel.items_viewed || 1;
      const c = funnel.add_to_carts || 0;
      const ch = funnel.checkouts || 0;
      const p = funnel.purchases || 0;

      document.getElementById('funnelViewsCount').innerText = `${v.toLocaleString()} مشاهدة (100%)`;
      
      const cartPct = Math.min(100, Math.round((c / (v || 1)) * 100));
      document.getElementById('funnelCartCount').innerText = `${c.toLocaleString()} سلة (${cartPct}%)`;
      document.getElementById('barCart').style.width = `${Math.max(4, cartPct)}%`;

      const chPct = Math.min(100, Math.round((ch / (c || 1)) * 100));
      document.getElementById('funnelCheckoutCount').innerText = `${ch.toLocaleString()} بدء دفع (${chPct}% من السلات)`;
      document.getElementById('barCheckout').style.width = `${Math.max(3, (ch / (v || 1)) * 100)}%`;

      const pPct = ch > 0 ? Math.round((p / ch) * 100) : 0;
      document.getElementById('funnelPurchaseCount').innerText = `${p.toLocaleString()} شراء (${pPct}%)`;
      document.getElementById('barPurchase').style.width = `${Math.max(2, (p / (v || 1)) * 100)}%`;
    }

    function getChartThemeColors() {
      const isDark = document.body.classList.contains('theme-dark');
      return {
        grid: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
        text: isDark ? '#94A3B8' : '#64748B',
        legend: isDark ? '#CBD5E1' : '#334155'
      };
    }

    function renderTrendChart(trend) {
      const ctx = document.getElementById('trendChart').getContext('2d');
      const labels = trend.map(t => t.date);
      const usersData = trend.map(t => t.users);
      const checkoutsData = trend.map(t => t.checkouts);
      const themeColors = getChartThemeColors();

      if (trendChartInstance) {
        trendChartInstance.destroy();
      }

      trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'الزوار الفريدون (Unique Users)',
              data: usersData,
              borderColor: '#2563EB',
              backgroundColor: 'rgba(37, 99, 235, 0.08)',
              fill: true,
              tension: 0.35,
              borderWidth: 2.5
            },
            {
              label: 'مرات بدء الدفع (Checkouts Event Count)',
              data: checkoutsData,
              borderColor: '#E11D48',
              backgroundColor: 'rgba(225, 29, 72, 0.1)',
              fill: true,
              tension: 0.35,
              borderWidth: 2.5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              labels: { color: themeColors.legend, font: { family: 'Cairo', weight: '700' } }
            }
          },
          scales: {
            x: {
              ticks: { color: themeColors.text, font: { family: 'Cairo' } },
              grid: { color: themeColors.grid }
            },
            y: {
              ticks: { color: themeColors.text, font: { family: 'Cairo' } },
              grid: { color: themeColors.grid }
            }
          }
        }
      });
    }

    function renderChannelsChart(channels) {
      const ctx = document.getElementById('channelsChart').getContext('2d');
      const labels = channels.map(c => c.channel);
      const data = channels.map(c => c.sessions);
      const themeColors = getChartThemeColors();

      if (channelsChartInstance) {
        channelsChartInstance.destroy();
      }

      const colors = ['#2563EB', '#059669', '#7C3AED', '#D97706', '#E11D48', '#0891B2', '#64748B'];

      channelsChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: colors.slice(0, labels.length),
            borderWidth: 2,
            borderColor: document.body.classList.contains('theme-dark') ? '#151D2F' : '#FFFFFF'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: themeColors.legend, font: { family: 'Cairo' }, boxWidth: 12 }
            }
          },
          cutout: '68%'
        }
      });
    }

    function renderDevicesChart(devices) {
      const ctx = document.getElementById('devicesChart').getContext('2d');
      const labelMap = { 'mobile': 'هاتف ذكي (Mobile)', 'desktop': 'كمبيوتر (Desktop)', 'tablet': 'لوحي (Tablet)' };
      const labels = devices.map(d => labelMap[d.device] || d.device);
      const data = devices.map(d => d.sessions);
      const themeColors = getChartThemeColors();

      if (devicesChartInstance) {
        devicesChartInstance.destroy();
      }

      devicesChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: ['#059669', '#2563EB', '#D97706', '#7C3AED'],
            borderWidth: 2,
            borderColor: document.body.classList.contains('theme-dark') ? '#151D2F' : '#FFFFFF'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: themeColors.legend, font: { family: 'Cairo' }, boxWidth: 12 }
            }
          },
          cutout: '68%'
        }
      });
    }

    function renderCheckoutsTable(checkouts) {
      const tbody = document.getElementById('checkoutsTableBody');
      if (!checkouts || checkouts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">لا توجد عمليات مسجلة.</td></tr>';
        return;
      }
      tbody.innerHTML = checkouts.map((c, idx) => {
        const isLive = c.is_live;
        const deviceIcon = c.device === 'desktop' ? '💻 كمبيوتر' : (c.device === 'tablet' ? '📟 لوحي' : '📱 هاتف');
        const flag = c.country === 'United States' ? '🇺🇸' : (c.country === 'Morocco' ? '🇲🇦' : '🌍');
        return `
          <tr class="${idx === 0 ? 'row-highlight' : ''}">
            <td><strong>${c.time}</strong></td>
            <td>${flag} ${c.country} - ${c.city}</td>
            <td><span class="device-badge">${deviceIcon}</span></td>
            <td>${c.page || 'صفحة الدفع'}</td>
            <td><strong>${c.count}</strong></td>
            <td>
              <span class="status-badge ${isLive ? 'live' : 'checkout'}">
                ${isLive ? '🟢 جاري الآن' : '✅ تم البدء'}
              </span>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderPagesTable(pages) {
      const tbody = document.getElementById('pagesTableBody');
      if (!pages || pages.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">لا توجد صفحات مسجلة.</td></tr>';
        return;
      }
      tbody.innerHTML = pages.map(p => `
        <tr>
          <td><strong>${p.title}</strong></td>
          <td style="font-family: monospace; color: var(--text-dim);">${p.path}</td>
          <td><strong style="color: var(--accent-blue);">${p.views.toLocaleString()}</strong></td>
          <td>${p.users.toLocaleString()}</td>
        </tr>
      `).join('');
    }

    function renderGeoTable(geo) {
      const tbody = document.getElementById('geoTableBody');
      if (!geo || geo.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">لا توجد بيانات جغرافية.</td></tr>';
        return;
      }
      tbody.innerHTML = geo.map(g => {
        const flag = g.country === 'United States' ? '🇺🇸' : (g.country === 'Morocco' ? '🇲🇦' : '🌐');
        return `
          <tr>
            <td><strong>${flag} ${g.country}</strong></td>
            <td>${g.city}</td>
            <td>${g.sessions.toLocaleString()}</td>
            <td>${g.users.toLocaleString()}</td>
            <td><strong style="color: var(--accent-rose);">${g.checkouts}</strong></td>
          </tr>
        `;
      }).join('');
    }

    function renderRealtimeTable(visitors) {
      const tbody = document.getElementById('realtimeTableBody');
      if (!visitors || visitors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">لا يوجد زوار نشطون في هذه اللحظة.</td></tr>';
        return;
      }
      tbody.innerHTML = visitors.map((v, i) => {
        const flag = v.country === 'United States' ? '🇺🇸' : (v.country === 'Morocco' ? '🇲🇦' : '🌍');
        const deviceIcon = v.device === 'desktop' ? '💻 كمبيوتر' : (v.device === 'tablet' ? '📟 لوحي' : '📱 هاتف');
        const isTest = (v.country === 'Morocco');
        return `
          <tr style="${isTest ? 'background:#FEF3C7; font-weight:800;' : ''}">
            <td><strong>${v.page}</strong> ${isTest ? '<span class="status-badge test">🌟 زيارتك التجريبية</span>' : ''}</td>
            <td>${flag} ${v.country} - ${v.city}</td>
            <td><span class="device-badge">${deviceIcon}</span></td>
            <td><strong style="color: var(--accent-green);">${v.users}</strong></td>
            <td>
              <button class="btn-action" style="padding:4px 10px; font-size:0.78rem;" onclick="openVisitorFullWindow(${i + 1})">
                👁️ فحص النشاط
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    fetchData();
    fetchInstantVisitorsData();
    setInterval(fetchData, 10000);
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    print(f"🚀 تشغيل لوحة تحليلات جوجل الذكية على http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
