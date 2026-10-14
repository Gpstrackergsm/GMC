#!/usr/bin/env python3
"""
Inspect and lock campaigns to USA Presence only.
"""
import os
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(__file__), "google_ads_auth", "google-ads.yaml")

def get_client():
    return GoogleAdsClient.load_from_storage(YAML_PATH)

def inspect_and_lock():
    client = get_client()
    ga_service = client.get_service("GoogleAdsService")
    campaign_service = client.get_service("CampaignService")

    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.geo_target_type_setting.positive_geo_target_type,
            campaign.geo_target_type_setting.negative_geo_target_type
        FROM campaign
        WHERE campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

    campaigns_to_update = []
    print("\n--- Current Campaign Location Settings ---")
    for row in response:
        c = row.campaign
        pos_type = c.geo_target_type_setting.positive_geo_target_type.name if c.geo_target_type_setting else "NOT_SET"
        neg_type = c.geo_target_type_setting.negative_geo_target_type.name if c.geo_target_type_setting else "NOT_SET"
        print(f"Campaign: {c.name} (ID: {c.id}) | Status: {c.status.name}")
        print(f"  Positive Geo Target: {pos_type}")
        print(f"  Negative Geo Target: {neg_type}")

        if c.status.name in ["ENABLED", "PAUSED"]:
            campaigns_to_update.append((c.id, c.name, pos_type, neg_type))

    # Now let's check location criteria for these campaigns
    criterion_query = """
        SELECT
            campaign.id,
            campaign_criterion.criterion_id,
            campaign_criterion.location.geo_target_constant,
            campaign_criterion.negative
        FROM campaign_criterion
        WHERE campaign_criterion.type = 'LOCATION'
    """
    try:
        crit_res = ga_service.search(customer_id=CUSTOMER_ID, query=criterion_query)
        print("\n--- Existing Location Criteria ---")
        for row in crit_res:
            c_id = row.campaign.id
            crit = row.campaign_criterion
            print(f"Campaign ID: {c_id} | Location Constant: {crit.location.geo_target_constant} | Negative: {crit.negative}")
    except Exception as e:
        print(f"Could not fetch criteria: {e}")

    # Now apply updates
    print("\n--- Applying Lock to USA Presence Only ---")
    operations = []
    for c_id, c_name, pos_type, neg_type in campaigns_to_update:
        op = client.get_type("CampaignOperation")
        camp = op.update
        camp.resource_name = f"customers/{CUSTOMER_ID}/campaigns/{c_id}"
        
        # Set to PRESENCE
        camp.geo_target_type_setting.positive_geo_target_type = client.enums.PositiveGeoTargetTypeEnum.PRESENCE
        camp.geo_target_type_setting.negative_geo_target_type = client.enums.NegativeGeoTargetTypeEnum.PRESENCE
        
        client.copy_from(
            op.update_mask,
            field_mask_pb2.FieldMask(
                paths=[
                    "geo_target_type_setting.positive_geo_target_type",
                    "geo_target_type_setting.negative_geo_target_type",
                ]
            ),
        )
        operations.append((c_id, c_name, op))

    for c_id, c_name, op in operations:
        try:
            res = campaign_service.mutate_campaigns(customer_id=CUSTOMER_ID, operations=[op])
            print(f"✅ Successfully updated campaign '{c_name}' (ID: {c_id}) to PRESENCE only!")
        except Exception as e:
            print(f"❌ Failed to update campaign '{c_name}' (ID: {c_id}): {e}")

if __name__ == "__main__":
    inspect_and_lock()
