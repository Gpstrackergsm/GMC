#!/usr/bin/env python3
"""
Deep Platform Audit: Google Ads, GA4, GMC Feed, and Shopify Storefront/Checkout.
Analyzes why campaigns may or may not be converting to sales.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADS_YAML = os.path.join(BASE_DIR, "google_ads_auth", "google-ads.yaml")
GA4_CREDS = os.path.join(BASE_DIR, "google_ads_auth", "google_ads_credentials.json")
CUSTOMER_ID = "4143615535"
GA4_PROPERTY = "properties/557255426"

audit_results = {}

# 1. Google Ads Audit
print("\n" + "="*80)
print("1. QUERYING GOOGLE ADS API...")
print("="*80)
try:
    from google.ads.googleads.client import GoogleAdsClient
    client = GoogleAdsClient.load_from_storage(ADS_YAML)
    ga_service = client.get_service("GoogleAdsService")

    # A. Account level summary
    q_account = """
        SELECT
            customer.id,
            customer.descriptive_name,
            customer.currency_code,
            customer.time_zone
        FROM customer
        LIMIT 1
    """
    for row in ga_service.search(customer_id=CUSTOMER_ID, query=q_account):
        audit_results["account"] = {
            "id": row.customer.id,
            "name": row.customer.descriptive_name,
            "currency": row.customer.currency_code,
            "tz": row.customer.time_zone
        }
        print(f"Connected to Account: {row.customer.descriptive_name} ({row.customer.id}) | Currency: {row.customer.currency_code} | TZ: {row.customer.time_zone}")

    # B. Campaigns Summary (All Time, Last 7 Days, Today)
    def fetch_campaign_metrics(date_range_str="LAST_7_DAYS"):
        date_filter = f"segments.date DURING {date_range_str}" if date_range_str != "ALL_TIME" else ""
        where_clause = "WHERE campaign.status != 'REMOVED'"
        if date_filter:
            where_clause += f" AND {date_filter}"
        
        q = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            {where_clause}
        """
        rows_data = []
        for r in ga_service.search(customer_id=CUSTOMER_ID, query=q):
            b_amount = (r.campaign_budget.amount_micros / 1e6) if r.campaign_budget.amount_micros else 0
            cost = (r.metrics.cost_micros / 1e6) if r.metrics.cost_micros else 0
            cpc = (r.metrics.average_cpc / 1e6) if r.metrics.average_cpc else 0
            rows_data.append({
                "id": str(r.campaign.id),
                "name": r.campaign.name,
                "status": r.campaign.status.name,
                "type": r.campaign.advertising_channel_type.name,
                "budget_daily": b_amount,
                "impressions": r.metrics.impressions,
                "clicks": r.metrics.clicks,
                "cost": round(cost, 2),
                "cpc": round(cpc, 2),
                "ctr": round(r.metrics.ctr * 100, 2),
                "conversions": round(r.metrics.conversions, 1),
                "conv_value": round(r.metrics.conversions_value, 2)
            })
        return rows_data

    audit_results["campaigns_today"] = fetch_campaign_metrics("TODAY")
    audit_results["campaigns_yesterday"] = fetch_campaign_metrics("YESTERDAY")
    audit_results["campaigns_last_7_days"] = fetch_campaign_metrics("LAST_7_DAYS")
    audit_results["campaigns_all_time"] = fetch_campaign_metrics("ALL_TIME")

    print("\n--- CAMPAIGNS TODAY ---")
    for c in audit_results["campaigns_today"]:
        print(f"[{c['status']}] {c['name']} | Spend: {c['cost']} {audit_results['account']['currency']} | Clicks: {c['clicks']} | Impr: {c['impressions']} | Avg CPC: {c['cpc']} | Conv: {c['conversions']}")

    print("\n--- CAMPAIGNS LAST 7 DAYS ---")
    for c in audit_results["campaigns_last_7_days"]:
        print(f"[{c['status']}] {c['name']} | Spend: {c['cost']} {audit_results['account']['currency']} | Clicks: {c['clicks']} | Impr: {c['impressions']} | Avg CPC: {c['cpc']} | Conv: {c['conversions']}")

    # C. Conversion Actions
    q_conv = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.status,
            conversion_action.type,
            conversion_action.category,
            conversion_action.primary_for_goal
        FROM conversion_action
        WHERE conversion_action.status != 'HIDDEN'
    """
    conv_actions = []
    for r in ga_service.search(customer_id=CUSTOMER_ID, query=q_conv):
        ca = r.conversion_action
        conv_actions.append({
            "id": str(ca.id),
            "name": ca.name,
            "status": ca.status.name,
            "type": ca.type.name,
            "category": ca.category.name,
            "primary": ca.primary_for_goal
        })
        print(f"Conversion Action: {ca.name} (ID: {ca.id}) | Category: {ca.category.name} | Primary: {ca.primary_for_goal} | Status: {ca.status.name}")
    audit_results["conversion_actions"] = conv_actions

    # D. Top Search Queries (Last 7 Days)
    q_sq = """
        SELECT
            search_term_view.search_term,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM search_term_view
        WHERE segments.date DURING LAST_7_DAYS
        ORDER BY metrics.clicks DESC
        LIMIT 25
    """
    search_queries = []
    print("\n--- TOP SEARCH QUERIES (LAST 7 DAYS) ---")
    for r in ga_service.search(customer_id=CUSTOMER_ID, query=q_sq):
        cost = (r.metrics.cost_micros / 1e6) if r.metrics.cost_micros else 0
        search_queries.append({
            "term": r.search_term_view.search_term,
            "clicks": r.metrics.clicks,
            "impressions": r.metrics.impressions,
            "cost": round(cost, 2),
            "conversions": r.metrics.conversions
        })
        print(f"Term: '{r.search_term_view.search_term}' | Clicks: {r.metrics.clicks} | Spend: {cost:.2f} | Conv: {r.metrics.conversions}")
    audit_results["top_search_queries"] = search_queries

    # E. Top Products (Last 7 Days)
    q_prod = """
        SELECT
            shopping_performance_view.resource_name,
            segments.product_title,
            segments.product_item_id,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM shopping_performance_view
        WHERE segments.date DURING LAST_7_DAYS
        ORDER BY metrics.clicks DESC
        LIMIT 25
    """
    top_prods = []
    print("\n--- TOP PRODUCTS SPENDING (LAST 7 DAYS) ---")
    for r in ga_service.search(customer_id=CUSTOMER_ID, query=q_prod):
        cost = (r.metrics.cost_micros / 1e6) if r.metrics.cost_micros else 0
        top_prods.append({
            "title": r.segments.product_title,
            "id": r.segments.product_item_id,
            "clicks": r.metrics.clicks,
            "impressions": r.metrics.impressions,
            "cost": round(cost, 2),
            "conversions": r.metrics.conversions,
            "conv_value": round(r.metrics.conversions_value, 2)
        })
        print(f"Product: {r.segments.product_title[:45]} | Clicks: {r.metrics.clicks} | Spend: {cost:.2f} | Conv: {r.metrics.conversions}")
    audit_results["top_products"] = top_prods

    # F. Device Performance
    q_dev = """
        SELECT
            segments.device,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE segments.date DURING LAST_7_DAYS AND campaign.status != 'REMOVED'
    """
    dev_stats = {}
    for r in ga_service.search(customer_id=CUSTOMER_ID, query=q_dev):
        dev = r.segments.device.name
        if dev not in dev_stats:
            dev_stats[dev] = {"clicks": 0, "impressions": 0, "cost": 0.0, "conversions": 0.0}
        dev_stats[dev]["clicks"] += r.metrics.clicks
        dev_stats[dev]["impressions"] += r.metrics.impressions
        dev_stats[dev]["cost"] += (r.metrics.cost_micros / 1e6) if r.metrics.cost_micros else 0
        dev_stats[dev]["conversions"] += r.metrics.conversions
    
    print("\n--- DEVICE BREAKDOWN (LAST 7 DAYS) ---")
    for dev, st in dev_stats.items():
        st["cost"] = round(st["cost"], 2)
        print(f"Device: {dev:<10} | Clicks: {st['clicks']:<5} | Spend: {st['cost']:<8} | Conv: {st['conversions']}")
    audit_results["device_breakdown"] = dev_stats

except Exception as e:
    print(f"❌ Error querying Google Ads: {e}")
    audit_results["ads_error"] = str(e)


# 2. Google Analytics 4 (GA4) Audit
print("\n" + "="*80)
print("2. QUERYING GOOGLE ANALYTICS 4 (GA4)...")
print("="*80)
try:
    from google.oauth2.credentials import Credentials
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunRealtimeReportRequest,
        RunReportRequest,
        DateRange,
        Metric,
        Dimension
    )

    with open(GA4_CREDS, 'r', encoding='utf-8') as f:
        cd = json.load(f)

    creds = Credentials(
        token=None,
        refresh_token=cd["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cd["client_id"],
        client_secret=cd["client_secret"]
    )
    ga4 = BetaAnalyticsDataClient(credentials=creds)

    # Realtime Active Users
    req_rt = RunRealtimeReportRequest(
        property=GA4_PROPERTY,
        metrics=[Metric(name="activeUsers")]
    )
    res_rt = ga4.run_realtime_report(req_rt)
    active_now = int(res_rt.rows[0].metric_values[0].value) if res_rt.rows else 0
    print(f"⚡ GA4 Realtime Active Visitors (Right Now): {active_now}")
    audit_results["ga4_realtime_users"] = active_now

    # Funnel Events (Last 7 Days)
    req_events = RunReportRequest(
        property=GA4_PROPERTY,
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount"), Metric(name="totalUsers")]
    )
    res_events = ga4.run_report(req_events)
    events_map = {}
    print("\n--- GA4 TOP EVENTS (LAST 7 DAYS) ---")
    for r in res_events.rows:
        ev_name = r.dimension_values[0].value
        ev_count = int(r.metric_values[0].value)
        ev_users = int(r.metric_values[1].value)
        events_map[ev_name] = {"count": ev_count, "users": ev_users}
        if ev_name in ["page_view", "view_item", "add_to_cart", "begin_checkout", "purchase", "session_start", "first_visit"]:
            print(f"Event: {ev_name:<20} | Count: {ev_count:<6} | Users: {ev_users:<6}")
    audit_results["ga4_events"] = events_map

    # Traffic Source / Medium (Last 7 Days)
    req_sources = RunReportRequest(
        property=GA4_PROPERTY,
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="engagedSessions"), Metric(name="averageSessionDuration")]
    )
    res_sources = ga4.run_report(req_sources)
    sources_list = []
    print("\n--- GA4 SESSIONS BY SOURCE/MEDIUM (LAST 7 DAYS) ---")
    for r in res_sources.rows:
        src = r.dimension_values[0].value
        sess = int(r.metric_values[0].value)
        users = int(r.metric_values[1].value)
        eng = int(r.metric_values[2].value)
        dur = float(r.metric_values[3].value)
        sources_list.append({"source": src, "sessions": sess, "users": users, "engaged": eng, "avg_dur_sec": round(dur, 1)})
        print(f"Source: {src:<30} | Sessions: {sess:<5} | Users: {users:<5} | Engaged: {eng:<5} | Avg Dur: {dur:.1f}s")
    audit_results["ga4_sources"] = sources_list

    # Country Breakdown
    req_geo = RunReportRequest(
        property=GA4_PROPERTY,
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="activeUsers"), Metric(name="sessions")]
    )
    res_geo = ga4.run_report(req_geo)
    geo_list = []
    print("\n--- GA4 USERS BY COUNTRY (LAST 7 DAYS) ---")
    for r in res_geo.rows:
        cntry = r.dimension_values[0].value
        users = int(r.metric_values[0].value)
        sess = int(r.metric_values[1].value)
        geo_list.append({"country": cntry, "users": users, "sessions": sess})
        print(f"Country: {cntry:<25} | Users: {users:<5} | Sessions: {sess:<5}")
    audit_results["ga4_countries"] = geo_list

except Exception as e:
    print(f"❌ Error querying GA4: {e}")
    audit_results["ga4_error"] = str(e)


# 3. Shopify Storefront & Checkout Live Test
print("\n" + "="*80)
print("3. TESTING SHOPIFY STOREFRONT & CHECKOUT HEALTH...")
print("="*80)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*"
}

# A. Storefront status
try:
    req = urllib.request.Request("https://leafanoo.com/", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        audit_results["storefront_status"] = resp.status
        print(f"✅ Storefront Homepage: HTTP {resp.status}")
except Exception as e:
    print(f"❌ Storefront Homepage Failed: {e}")
    audit_results["storefront_status"] = str(e)

# B. Cart and Product Endpoint test
try:
    req = urllib.request.Request("https://leafanoo.com/cart.js", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        cart_data = json.loads(resp.read().decode("utf-8"))
        print(f"✅ Shopify Cart Endpoint: OK, Currency: {cart_data.get('currency')}, Items: {cart_data.get('item_count')}")
        audit_results["store_currency"] = cart_data.get('currency')
except Exception as e:
    print(f"❌ Cart Endpoint Error: {e}")

# C. Check top product availability & price
top_test_handles = ["craftsman-r110-11-5hp-manual-gear-36-riding-mower", "john-deere-s120-mower-42-in-22-hp-v-twin-gas", "super73-zx-core"]
for handle in top_test_handles:
    try:
        req = urllib.request.Request(f"https://leafanoo.com/products/{handle}.js", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            p_data = json.loads(resp.read().decode("utf-8"))
            avail = p_data.get("available")
            price = p_data.get("price", 0) / 100.0
            variants = len(p_data.get("variants", []))
            first_variant_id = p_data.get("variants", [])[0]["id"] if p_data.get("variants") else None
            print(f"✅ Product '{handle}': Available={avail}, Price=${price:.2f}, Variant ID={first_variant_id}")
    except Exception as e:
        print(f"⚠️ Product '{handle}' check: {e}")

# Write raw audit data to file
out_path = os.path.join(BASE_DIR, "catalog", "deep_audit_snapshot.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(audit_results, f, ensure_ascii=False, indent=2)
print(f"\nAudit complete! Snapshot saved to {out_path}")
