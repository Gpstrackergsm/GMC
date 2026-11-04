#!/usr/bin/env python3
"""
منصة المراقبة المباشرة لـ Google Analytics (Realtime Dashboard)
- Arabic Interface (RTL)
- Live active visitors (آخر 30 دقيقة واللحظة الحالية)
- Country, City, Device breakdown
- Active pages visited in real time
- Auto-refresh every 5 seconds (SSE / Polling API)
- Running on http://localhost:5055
"""

import json
import os
import sys
from flask import Flask, jsonify, render_template_string
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunRealtimeReportRequest,
    RunReportRequest,
    DateRange,
    Metric,
    Dimension
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_CREDS_PATH = os.path.join(BASE_DIR, 'google_ads_auth', 'google_ads_credentials.json')
GA4_PROPERTY = 'properties/557255426'

app = Flask(__name__)

def get_ga4_client():
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

@app.route('/api/realtime')
def api_realtime():
    try:
        ga4 = get_ga4_client()

        # 1. Total Active Users (Right now)
        req_total = RunRealtimeReportRequest(
            property=GA4_PROPERTY,
            metrics=[Metric(name="activeUsers")]
        )
        res_total = ga4.run_realtime_report(req_total)
        active_now = int(res_total.rows[0].metric_values[0].value) if res_total.rows else 0

        # 2. Detailed Realtime Visitors by Page, Country, City, Device
        req_details = RunRealtimeReportRequest(
            property=GA4_PROPERTY,
            dimensions=[
                Dimension(name="unifiedScreenName"),
                Dimension(name="country"),
                Dimension(name="city"),
                Dimension(name="deviceCategory")
            ],
            metrics=[Metric(name="activeUsers"), Metric(name="screenPageViews")]
        )
        res_details = ga4.run_realtime_report(req_details)

        visitors = []
        countries_map = {}
        pages_map = {}
        devices_map = {}

        for row in res_details.rows:
            page = row.dimension_values[0].value or "/"
            country = row.dimension_values[1].value or "غير معروف"
            city = row.dimension_values[2].value or "-"
            device = row.dimension_values[3].value or "mobile"
            users = int(row.metric_values[0].value)
            views = int(row.metric_values[1].value)

            visitors.append({
                "page": page,
                "country": country,
                "city": city,
                "device": device,
                "users": users,
                "views": views
            })

            countries_map[country] = countries_map.get(country, 0) + users
            pages_map[page] = pages_map.get(page, 0) + users
            devices_map[device] = devices_map.get(device, 0) + users

        # 3. Quick Today Overview (Standard Report)
        req_today = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[DateRange(start_date="today", end_date="today")],
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
                Metric(name="addToCarts"),
                Metric(name="checkouts")
            ]
        )
        res_today = ga4.run_report(req_today)
        today_stats = {"users": 0, "views": 0, "atc": 0, "checkouts": 0}
        if res_today.rows:
            vals = res_today.rows[0].metric_values
            today_stats = {
                "users": int(vals[0].value),
                "views": int(vals[1].value),
                "atc": int(vals[2].value),
                "checkouts": int(vals[3].value)
            }

        return jsonify({
            "status": "success",
            "active_now": active_now,
            "visitors": visitors,
            "countries": sorted([{"name": k, "count": v} for k, v in countries_map.items()], key=lambda x: x["count"], reverse=True),
            "pages": sorted([{"name": k, "count": v} for k, v in pages_map.items()], key=lambda x: x["count"], reverse=True),
            "devices": devices_map,
            "today": today_stats
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>لوحة المراقبة الحية — Google Analytics Realtime</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0B0F19;
      --card: #151D2F;
      --border: #232F48;
      --primary: #10B981;
      --primary-glow: rgba(16, 185, 129, 0.25);
      --text: #F1F5F9;
      --text-muted: #94A3B8;
      --danger: #EF4444;
      --accent: #3B82F6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Cairo', sans-serif;
      padding: 24px;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    .logo-area { display: flex; align-items: center; gap: 12px; }
    .pulse-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--primary);
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 700;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--primary);
      box-shadow: 0 0 10px var(--primary);
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.3); }
    }
    .grid-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
      overflow: hidden;
    }
    .stat-card.hero {
      border-color: var(--primary);
      box-shadow: 0 0 25px var(--primary-glow);
    }
    .stat-label { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; }
    .stat-val { font-size: 2.2rem; font-weight: 900; line-height: 1; }
    .stat-card.hero .stat-val { color: var(--primary); }

    .main-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    }
    @media (max-width: 992px) {
      .main-grid { grid-template-columns: 1fr; }
    }
    .panel {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .panel-title {
      font-size: 1.1rem;
      font-weight: 800;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: right;
    }
    th {
      padding: 12px 14px;
      color: var(--text-muted);
      font-size: 0.82rem;
      border-bottom: 1px solid var(--border);
      font-weight: 700;
    }
    td {
      padding: 14px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      font-size: 0.9rem;
    }
    tr:last-child td { border-bottom: none; }
    .tag {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      background: rgba(255,255,255,0.06);
    }
    .tag-us {
      background: rgba(59, 130, 246, 0.18);
      color: #60A5FA;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .progress-bar-bg {
      background: rgba(255,255,255,0.06);
      height: 6px;
      border-radius: 3px;
      overflow: hidden;
      margin-top: 6px;
    }
    .progress-bar-fill {
      height: 100%;
      background: var(--primary);
      border-radius: 3px;
    }
    .empty-state {
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted);
    }
    .empty-icon { font-size: 2.5rem; margin-bottom: 8px; }
  </style>
</head>
<body>

  <header class="header">
    <div class="logo-area">
      <h1 style="font-size: 1.4rem; font-weight: 900;">⚡ لوحة المراقبة الحية (GA4 Live)</h1>
      <span class="pulse-badge"><span class="pulse-dot"></span> بث مباشر وتحديث كل 5 ثوانٍ</span>
    </div>
    <div style="font-size: 0.85rem; color: var(--text-muted);">
      المتجر: <strong style="color: #fff;">Leafanoo.com</strong> (US Target)
    </div>
  </header>

  <!-- Top Stats Summary -->
  <div class="grid-stats">
    <div class="stat-card hero">
      <span class="stat-label">المتواجدون بالموقع الآن (Real-Time)</span>
      <span class="stat-val" id="activeUsersVal">0</span>
      <span style="font-size: 0.75rem; color: var(--text-muted);">آخر 30 دقيقة واللحظة الحالية</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">إجمالي الزوار اليوم (اليوم كاملاً)</span>
      <span class="stat-val" id="todayUsersVal">0</span>
      <span style="font-size: 0.75rem; color: var(--text-muted);">زوار حقيقيون مسجلون اليوم</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">مشاهدات الصفحات اليوم</span>
      <span class="stat-val" id="todayViewsVal">0</span>
      <span style="font-size: 0.75rem; color: var(--text-muted);">مرات تصفح المنتجات</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">إضافة إلى السلة اليوم (Add to Cart)</span>
      <span class="stat-val" style="color: #F59E0B;" id="todayAtcVal">0</span>
      <span style="font-size: 0.75rem; color: var(--text-muted);">محاولات الشراء</span>
    </div>
  </div>

  <div class="main-grid">
    <!-- Left: Live Visitors Table & Top Pages -->
    <div>
      <div class="panel">
        <div class="panel-title">
          <span>👥 الزوار المباشرون الآن (الصفحات والمدن)</span>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>الصفحة التي يتصفحها الزائر</th>
                <th>الدولة والمدينة</th>
                <th>نوع الجهاز</th>
                <th>العدد</th>
              </tr>
            </thead>
            <tbody id="visitorsTableBody">
              <tr>
                <td colspan="4">
                  <div class="empty-state">
                    <div class="empty-icon">📡</div>
                    <div>في انتظار وصول زائر للموقع الآن... سيظهر فوراً هنا</div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>🔥 الصفحات الأكثر نشاطاً في الوقت الفعلي</span>
        </div>
        <div id="topPagesList">
          <div class="empty-state">لا توجد زيارات نشطة حالياً</div>
        </div>
      </div>
    </div>

    <!-- Right: Geographic Distribution & Devices -->
    <div>
      <div class="panel">
        <div class="panel-title">
          <span>🌍 الدول المتصلة الآن</span>
        </div>
        <div id="countriesList">
          <div class="empty-state">لا توجد دول متصلة حالياً</div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>📱 توزيع الأجهزة</span>
        </div>
        <div id="devicesList">
          <div class="empty-state">لا توجد بيانات</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    async function updateRealtimeData() {
      try {
        const res = await fetch('/api/realtime');
        const data = await res.json();

        if (data.status !== 'success') return;

        // 1. Hero stats
        document.getElementById('activeUsersVal').innerText = data.active_now;
        document.getElementById('todayUsersVal').innerText = data.today.users;
        document.getElementById('todayViewsVal').innerText = data.today.views;
        document.getElementById('todayAtcVal').innerText = data.today.atc;

        // 2. Visitors Table
        const tbody = document.getElementById('visitorsTableBody');
        if (data.visitors && data.visitors.length > 0) {
          tbody.innerHTML = data.visitors.map(v => {
            const isUS = v.country.includes('United States') || v.country.includes('US');
            const countryTag = isUS ? `<span class="tag tag-us">🇺🇸 ${v.country} - ${v.city}</span>` : `<span class="tag">${v.country} - ${v.city}</span>`;
            const devIcon = v.device.toLowerCase() === 'mobile' ? '📱 جوال' : (v.device.toLowerCase() === 'desktop' ? '💻 كمبيوتر' : '📟 تابلت');
            return `
              <tr>
                <td><strong style="color: #60A5FA;">${escapeHtml(v.page)}</strong></td>
                <td>${countryTag}</td>
                <td><span class="tag">${devIcon}</span></td>
                <td><strong style="color: #10B981;">${v.users}</strong></td>
              </tr>
            `;
          }).join('');
        } else {
          tbody.innerHTML = `
            <tr>
              <td colspan="4">
                <div class="empty-state">
                  <div class="empty-icon">📡</div>
                  <div>لا يوجد زوار نشطون في هذه اللحظة بالضبط. سيظهر الزائر الجديد هنا لحظياً.</div>
                </div>
              </td>
            </tr>
          `;
        }

        // 3. Top Pages
        const pagesList = document.getElementById('topPagesList');
        if (data.pages && data.pages.length > 0) {
          pagesList.innerHTML = data.pages.map(p => `
            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.88rem; margin-bottom: 4px;">
                <span style="font-weight: 700; color: #E2E8F0;">${escapeHtml(p.name)}</span>
                <span style="color: #10B981; font-weight: 800;">${p.count} زائر</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${Math.min(100, (p.count / (data.active_now || 1)) * 100)}%;"></div>
              </div>
            </div>
          `).join('');
        } else {
          pagesList.innerHTML = `<div class="empty-state" style="padding: 15px;">لا توجد صفحات نشطة الآن</div>`;
        }

        // 4. Countries
        const countriesList = document.getElementById('countriesList');
        if (data.countries && data.countries.length > 0) {
          countriesList.innerHTML = data.countries.map(c => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
              <span>${c.name.includes('United States') ? '🇺🇸' : '🌐'} ${escapeHtml(c.name)}</span>
              <strong style="color: #10B981;">${c.count}</strong>
            </div>
          `).join('');
        } else {
          countriesList.innerHTML = `<div class="empty-state" style="padding: 15px;">لا توجد بيانات دول نشطة حالياً</div>`;
        }

        // 5. Devices
        const devList = document.getElementById('devicesList');
        const devKeys = Object.keys(data.devices || {});
        if (devKeys.length > 0) {
          devList.innerHTML = devKeys.map(k => `
            <div style="display: flex; justify-content: space-between; padding: 6px 0;">
              <span>${k === 'mobile' ? '📱 جوال' : (k === 'desktop' ? '💻 كمبيوتر' : '📟 لوحي')}</span>
              <strong>${data.devices[k]}</strong>
            </div>
          `).join('');
        } else {
          devList.innerHTML = `<div class="empty-state" style="padding: 15px;">لا توجد بيانات أجهزة نشطة</div>`;
        }

      } catch (err) {
        console.error("Fetch error:", err);
      }
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // Refresh every 5 seconds
    updateRealtimeData();
    setInterval(updateRealtimeData, 5000);
  </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = 5055
    print(f"🚀 تشغيل لوحة المراقبة الحية على http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
