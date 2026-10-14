#!/usr/bin/env python3
"""
GMC Google Ads Automation & Optimizer
Leafanoo Account Manager (Customer ID: 414-361-5535)
"""

import os
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(__file__), "google_ads_auth", "google-ads.yaml")


def get_client():
    return GoogleAdsClient.load_from_storage(YAML_PATH)


def show_active_campaigns():
    client = get_client()
    ga_service = client.get_service("GoogleAdsService")

    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.maximize_conversion_value.target_roas,
            campaign_budget.amount_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

    print("\n" + "=" * 80)
    print("                    LEAFANOO CAMPAIGN PERFORMANCE")
    print("=" * 80)
    for row in response:
        c = row.campaign
        m = row.metrics
        b = row.campaign_budget
        budget = (b.amount_micros / 1_000_000) if b.amount_micros else 0
        spend = (m.cost_micros / 1_000_000) if m.cost_micros else 0
        roas = c.maximize_conversion_value.target_roas
        roas_str = f"{roas * 100:.0f}%" if roas else "Manual / Max"

        print(f"📦 Campaign: {c.name} [ID: {c.id}]")
        print(f"   Status:   {c.status.name} | Type: {c.advertising_channel_type.name}")
        print(f"   Budget:   {budget:.2f} DH/day | Target ROAS: {roas_str}")
        print(f"   Spent:    {spend:.2f} DH | Clicks: {m.clicks:,} | Impr: {m.impressions:,}")
        print(f"   Conv:     {m.conversions:.1f} | Value: {m.conversions_value:.2f} DH")
        print("-" * 80)
    print()


def update_campaign_budget(campaign_id: str, new_daily_amount_dollars: float):
    client = get_client()
    ga_service = client.get_service("GoogleAdsService")
    budget_service = client.get_service("CampaignBudgetService")

    # Get budget resource name
    query = f"SELECT campaign.campaign_budget FROM campaign WHERE campaign.id = {campaign_id}"
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    budget_resource = None
    for row in response:
        budget_resource = row.campaign.campaign_budget
        break

    if not budget_resource:
        print(f"Campaign {campaign_id} not found.")
        return

    op = client.get_type("CampaignBudgetOperation")
    b = op.update
    b.resource_name = budget_resource
    b.amount_micros = int(new_daily_amount_dollars * 1_000_000)
    client.copy_from(op.update_mask, field_mask_pb2.FieldMask(paths=["amount_micros"]))

    budget_service.mutate_campaign_budgets(customer_id=CUSTOMER_ID, operations=[op])
    print(f"✅ Budget for campaign {campaign_id} updated to {new_daily_amount_dollars:.2f} DH/day!")


def update_target_roas(campaign_id: str, roas_percentage: float):
    client = get_client()
    campaign_service = client.get_service("CampaignService")

    op = client.get_type("CampaignOperation")
    c = op.update
    c.resource_name = f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}"
    c.maximize_conversion_value.target_roas = roas_percentage / 100.0
    client.copy_from(op.update_mask, field_mask_pb2.FieldMask(paths=["maximize_conversion_value.target_roas"]))

    campaign_service.mutate_campaigns(customer_id=CUSTOMER_ID, operations=[op])
    print(f"✅ Target ROAS for campaign {campaign_id} set to {roas_percentage:.0f}%!")


def toggle_campaign_status(campaign_id: str, pause: bool = True):
    client = get_client()
    campaign_service = client.get_service("CampaignService")

    status_enum = client.enums.CampaignStatusEnum.PAUSED if pause else client.enums.CampaignStatusEnum.ENABLED

    op = client.get_type("CampaignOperation")
    c = op.update
    c.resource_name = f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}"
    c.status = status_enum
    client.copy_from(op.update_mask, field_mask_pb2.FieldMask(paths=["status"]))

    campaign_service.mutate_campaigns(customer_id=CUSTOMER_ID, operations=[op])
    action = "PAUSED" if pause else "ENABLED"
    print(f"✅ Campaign {campaign_id} is now {action}!")


def show_top_products():
    client = get_client()
    ga_service = client.get_service("GoogleAdsService")

    query = """
        SELECT
            segments.product_title,
            segments.product_item_id,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros
        FROM shopping_performance_view
        WHERE segments.date DURING LAST_30_DAYS
        ORDER BY metrics.cost_micros DESC
        LIMIT 15
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

    print("\n" + "=" * 80)
    print("                    TOP PRODUCTS SPEND & CLICKS (LAST 30 DAYS)")
    print("=" * 80)
    for row in response:
        title = row.segments.product_title or "Unknown"
        spend = row.metrics.cost_micros / 1_000_000
        cpc = (spend / row.metrics.clicks) if row.metrics.clicks else 0
        print(f"🏷️  {title[:45]:<45} | Clicks: {row.metrics.clicks:>4} | Spend: ${spend:>7.2f} | Avg CPC: ${cpc:>5.2f}")
    print("=" * 80 + "\n")


def main():
    while True:
        print("\n" + "=" * 50)
        print("    🤖 GMC GOOGLE ADS CONTROL PANEL")
        print("=" * 50)
        print(" 1. View Campaign Performance")
        print(" 2. View Top Products (Spend & Clicks)")
        print(" 3. Update Campaign Daily Budget")
        print(" 4. Update Target ROAS")
        print(" 5. Pause / Enable a Campaign")
        print(" 0. Exit")
        print("-" * 50)

        choice = input("Select an option: ").strip()

        try:
            if choice == "1":
                show_active_campaigns()
            elif choice == "2":
                show_top_products()
            elif choice == "3":
                cid = input("Enter Campaign ID (e.g., 24328651612 for Merchant): ").strip()
                amt = float(input("Enter new daily budget in USD ($): ").strip())
                update_campaign_budget(cid, amt)
            elif choice == "4":
                cid = input("Enter Campaign ID: ").strip()
                roas = float(input("Enter Target ROAS percentage (e.g., 350 for 350%): ").strip())
                update_target_roas(cid, roas)
            elif choice == "5":
                cid = input("Enter Campaign ID: ").strip()
                p = input("Pause campaign? (y/n): ").strip().lower() == "y"
                toggle_campaign_status(cid, pause=p)
            elif choice == "0":
                print("Exiting.")
                break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
