#!/usr/bin/env python3
"""
Verify conversion actions in Google Ads account.
"""
import os
import sys
from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_ads_auth", "google-ads.yaml")

def check_conversions():
    client = GoogleAdsClient.load_from_storage(YAML_PATH)
    ga_service = client.get_service("GoogleAdsService")

    query = """
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
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    
    print("\n" + "=" * 70)
    print("GOOGLE ADS CONVERSION ACTIONS AUDIT")
    print("=" * 70)
    for row in response:
        ca = row.conversion_action
        status = ca.status.name
        primary = "⭐ PRIMARY" if ca.primary_for_goal else "SECONDARY / OBSERVE"
        print(f"ID: {ca.id:<12} | Name: {ca.name:<25} | Status: {status:<8} | {primary} | Category: {ca.category.name}")
    print()

if __name__ == '__main__':
    check_conversions()
