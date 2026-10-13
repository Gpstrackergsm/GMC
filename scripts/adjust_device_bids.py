#!/usr/bin/env python3
"""
Inspect and adjust mobile bid modifier on campaign 24318560132.
"""
import os
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

CUSTOMER_ID = "4143615535"
YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_ads_auth", "google-ads.yaml")

def adjust_mobile_modifier(new_modifier=0.5):
    client = GoogleAdsClient.load_from_storage(YAML_PATH)
    ga_service = client.get_service("GoogleAdsService")
    campaign_criterion_service = client.get_service("CampaignCriterionService")

    q = """
        SELECT
            campaign_criterion.criterion_id,
            campaign_criterion.resource_name,
            campaign_criterion.device.type,
            campaign_criterion.bid_modifier
        FROM campaign_criterion
        WHERE campaign.id = 24318560132
          AND campaign_criterion.type = 'DEVICE'
    """
    res = ga_service.search(customer_id=CUSTOMER_ID, query=q)
    for r in res:
        cc = r.campaign_criterion
        device_type = cc.device.type.name
        print(f"Device: {device_type:<10} | Current Modifier: {cc.bid_modifier} | Resource: {cc.resource_name}")
        
        if device_type == "MOBILE":
            op = client.get_type("CampaignCriterionOperation")
            c = op.update
            c.resource_name = cc.resource_name
            c.bid_modifier = new_modifier
            client.copy_from(op.update_mask, field_mask_pb2.FieldMask(paths=["bid_modifier"]))
            
            mut_res = campaign_criterion_service.mutate_campaign_criteria(
                customer_id=CUSTOMER_ID, operations=[op]
            )
            print(f"✅ Successfully updated MOBILE modifier to {new_modifier} (-{(1-new_modifier)*100:.0f}%)!")

if __name__ == '__main__':
    adjust_mobile_modifier(0.5)
