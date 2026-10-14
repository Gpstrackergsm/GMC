#!/usr/bin/env python3
"""
Add negative keywords to active Google Ads campaigns to prevent non-mower spend.
"""
import os
import sys
from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_ads_auth", "google-ads.yaml")

NEGATIVE_KEYWORDS = [
    "swing set",
    "playset",
    "swingset",
    "pergola",
    "gazebo",
    "storage shed",
    "garden shed",
    "super 73",
    "super73",
    "ebike",
    "e-bike",
    "electric bike",
    "vehicle lift",
    "car lift",
    "tire changer",
    "wheel balancer",
    "generator",
    "portable generator",
    "treadmill",
    "trampoline",
    "exercise bike"
]

def add_negatives():
    print(f"Loading credentials from {YAML_PATH}...")
    client = GoogleAdsClient.load_from_storage(YAML_PATH)
    ga_service = client.get_service("GoogleAdsService")
    campaign_criterion_service = client.get_service("CampaignCriterionService")

    # Get active campaigns
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type
        FROM campaign
        WHERE campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    
    active_campaigns = []
    for row in response:
        c = row.campaign
        if c.status.name in ["ENABLED", "PAUSED"]:
            active_campaigns.append((c.id, c.name, c.advertising_channel_type.name))
            print(f"Found Campaign: {c.name} (ID: {c.id}, Type: {c.advertising_channel_type.name})")

    for camp_id, camp_name, camp_type in active_campaigns:
        # Standard Shopping supports campaign-level negative keywords directly
        if camp_type == "SHOPPING":
            print(f"\nAdding negative keywords to Shopping Campaign '{camp_name}' (ID: {camp_id})...")
            
            # Fetch existing negative keywords to avoid duplicates
            existing_query = f"""
                SELECT
                    campaign_criterion.criterion_id,
                    campaign_criterion.keyword.text,
                    campaign_criterion.keyword.match_type
                FROM campaign_criterion
                WHERE campaign.id = {camp_id}
                  AND campaign_criterion.type = 'KEYWORD'
                  AND campaign_criterion.negative = TRUE
            """
            existing_negs = set()
            try:
                ex_res = ga_service.search(customer_id=CUSTOMER_ID, query=existing_query)
                for row in ex_res:
                    existing_negs.add(row.campaign_criterion.keyword.text.lower())
            except Exception as e:
                print(f"Notice when querying existing criteria: {e}")

            operations = []
            for kw in NEGATIVE_KEYWORDS:
                if kw.lower() in existing_negs:
                    print(f"  - Already exists: '{kw}'")
                    continue

                op = client.get_type("CampaignCriterionOperation")
                crit = op.create
                crit.campaign = f"customers/{CUSTOMER_ID}/campaigns/{camp_id}"
                crit.negative = True
                crit.keyword.text = kw
                crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                operations.append(op)

            if operations:
                try:
                    res = campaign_criterion_service.mutate_campaign_criteria(
                        customer_id=CUSTOMER_ID, operations=operations
                    )
                    print(f"✅ Successfully added {len(res.results)} negative keywords to '{camp_name}'!")
                except Exception as e:
                    print(f"❌ Failed to mutate criteria: {e}")
            else:
                print(f"ℹ️ All negative keywords are already applied to '{camp_name}'.")

if __name__ == '__main__':
    add_negatives()
