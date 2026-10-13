#!/usr/bin/env python3
"""
Add secondary tier negative keywords to Google Ads campaign:
- Parts & replacement components
- Repair manuals & DIY troubleshooting
- Used / classifieds / rental
- Competitor brick-and-mortar stores & 'near me'
"""
import os
import sys
from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_ads_auth", "google-ads.yaml")

GRANULAR_NEGATIVES = [
    # Parts & Hardware (Not buying a mower)
    "parts",
    "replacement parts",
    "filter",
    "oil filter",
    "air filter",
    "fuel filter",
    "belt",
    "deck belt",
    "drive belt",
    "blade",
    "blades",
    "mower blade",
    "battery",
    "tires",
    "spindle",
    "carburetor",
    "spark plug",
    "starter",
    "solenoid",
    "pulley",
    "key",
    "cover",
    
    # Informational & Troubleshooting
    "manual",
    "owners manual",
    "service manual",
    "repair manual",
    "pdf",
    "how to",
    "problems",
    "diagram",
    "schematic",
    "recall",
    "troubleshooting",
    "repair",
    "repair shop",
    "fix",
    "maintenance",
    
    # Used & Classifieds
    "used",
    "craigslist",
    "facebook marketplace",
    "ebay",
    "offerup",
    "salvage",
    "junkyard",
    
    # Rental & Local Retail Stores
    "rental",
    "rent",
    "near me",
    "rural king",
    "harbor freight",
    "tractor supply",
    "tsc",
    "lowes",
    "home depot",
    "weingartz",
    "dealership near me",
    
    # Toys
    "toy",
    "toys",
    "diecast"
]

def add_negatives():
    print(f"Loading credentials from {YAML_PATH}...")
    client = GoogleAdsClient.load_from_storage(YAML_PATH)
    ga_service = client.get_service("GoogleAdsService")
    campaign_criterion_service = client.get_service("CampaignCriterionService")

    # Find active Shopping campaigns
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type
        FROM campaign
        WHERE campaign.status = 'ENABLED'
          AND campaign.advertising_channel_type = 'SHOPPING'
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
    
    for row in response:
        camp_id = row.campaign.id
        camp_name = row.campaign.name
        print(f"\nTargeting Campaign: '{camp_name}' (ID: {camp_id})")
        
        # Fetch existing negatives to avoid duplicates
        existing_query = f"""
            SELECT
                campaign_criterion.criterion_id,
                campaign_criterion.keyword.text
            FROM campaign_criterion
            WHERE campaign.id = {camp_id}
              AND campaign_criterion.type = 'KEYWORD'
              AND campaign_criterion.negative = TRUE
        """
        existing_negs = set()
        try:
            ex_res = ga_service.search(customer_id=CUSTOMER_ID, query=existing_query)
            for r in ex_res:
                existing_negs.add(r.campaign_criterion.keyword.text.lower())
        except Exception as e:
            print(f"Notice querying existing: {e}")

        operations = []
        for kw in GRANULAR_NEGATIVES:
            kw_clean = kw.strip().lower()
            if kw_clean in existing_negs:
                continue
            
            op = client.get_type("CampaignCriterionOperation")
            crit = op.create
            crit.campaign = f"customers/{CUSTOMER_ID}/campaigns/{camp_id}"
            crit.negative = True
            crit.keyword.text = kw_clean
            crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            operations.append(op)

        if operations:
            print(f"Adding {len(operations)} new granular negative keywords...")
            # Mutate in batches of 50
            batch_size = 50
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                try:
                    res = campaign_criterion_service.mutate_campaign_criteria(
                        customer_id=CUSTOMER_ID, operations=batch
                    )
                    print(f"  ✅ Batch {i//batch_size + 1} added ({len(res.results)} criteria).")
                except Exception as e:
                    print(f"  ❌ Batch error: {e}")
        else:
            print("  ℹ️ All granular negatives already present.")

if __name__ == '__main__':
    add_negatives()
