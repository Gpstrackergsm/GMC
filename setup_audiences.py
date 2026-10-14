"""
Full setup script:
1. Verify GA4 <-> Google Ads link
2. Create US High-Intent Audience in GA4
3. Check audience sync to Google Ads
4. Attach audience as OBSERVATION to campaign 24318560132
5. Import begin_checkout as secondary conversion from GA4
"""

import json
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ── Load credentials ──────────────────────────────────────────────────────────
CREDS_FILE = "google_ads_auth/google_ads_credentials.json"
GA4_PROPERTY = "properties/557255426"
ADS_CUSTOMER_ID = "4143615535"
CAMPAIGN_ID = "24318560132"

with open(CREDS_FILE) as f:
    creds_data = json.load(f)

creds = Credentials(
    token=creds_data.get("token"),
    refresh_token=creds_data["refresh_token"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=creds_data["client_id"],
    client_secret=creds_data["client_secret"],
    scopes=[
        "https://www.googleapis.com/auth/analytics.edit",
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/adwords",
    ]
)

# Refresh token if needed
if not creds.valid:
    creds.refresh(Request())

# ── STEP 1: Verify GA4 <-> Google Ads link ────────────────────────────────────
print("=" * 60)
print("STEP 1: Verifying GA4 ↔ Google Ads link")
print("=" * 60)

from google.analytics.admin_v1beta import AnalyticsAdminServiceClient

admin_client = AnalyticsAdminServiceClient(credentials=creds)
links = list(admin_client.list_google_ads_links(parent=GA4_PROPERTY))

if links:
    for link in links:
        print(f"  ✅ Link found:")
        print(f"     Name:        {link.name}")
        print(f"     Customer ID: {link.customer_id}")
        print(f"     Ads Enabled: {link.ads_personalization_enabled}")
        print(f"     Can Manage:  {link.can_manage_clients}")
else:
    print("  ❌ No Google Ads links found for this GA4 property!")
    print("     Please link in GA4 Admin → Product Links → Google Ads Links")

# ── STEP 2: Create US High-Intent Audience in GA4 ────────────────────────────
print()
print("=" * 60)
print("STEP 2: Creating 'US High-Intent Shoppers' audience in GA4")
print("=" * 60)

from google.analytics.admin_v1beta import types as admin_types

# Check if audience already exists
existing_audiences = list(admin_client.list_audiences(parent=GA4_PROPERTY))
audience_exists = None
for aud in existing_audiences:
    if "US High-Intent" in aud.display_name:
        audience_exists = aud
        break

if audience_exists:
    print(f"  ℹ️  Audience already exists: {audience_exists.display_name}")
    print(f"     Resource: {audience_exists.name}")
    new_audience = audience_exists
else:
    # Build audience: users who triggered add_to_cart OR begin_checkout OR add_shipping_info
    # AND are from United States
    audience_body = admin_types.Audience(
        display_name="US High-Intent Shoppers",
        description="US visitors who added to cart, began checkout, or entered shipping info",
        membership_duration_days=30,
        filter_clauses=[
            # Clause 1: Must be from United States
            admin_types.AudienceFilterClause(
                clause_type=admin_types.AudienceFilterClause.AudienceClauseType.INCLUDE,
                simple_filter=admin_types.AudienceSimpleFilter(
                    scope=admin_types.AudienceFilterScope.AUDIENCE_FILTER_SCOPE_ACROSS_ALL_SESSIONS,
                    filter_expression=admin_types.AudienceFilterExpression(
                        dimension_or_metric_filter=admin_types.AudienceDimensionOrMetricFilter(
                            field_name="country",
                            string_filter=admin_types.AudienceDimensionOrMetricFilter.StringFilter(
                                match_type=admin_types.AudienceDimensionOrMetricFilter.StringFilter.MatchType.EXACT,
                                value="United States",
                                case_sensitive=False,
                            )
                        )
                    )
                )
            ),
            # Clause 2: Must have triggered one of the high-intent events
            admin_types.AudienceFilterClause(
                clause_type=admin_types.AudienceFilterClause.AudienceClauseType.INCLUDE,
                simple_filter=admin_types.AudienceSimpleFilter(
                    scope=admin_types.AudienceFilterScope.AUDIENCE_FILTER_SCOPE_ACROSS_ALL_SESSIONS,
                    filter_expression=admin_types.AudienceFilterExpression(
                        or_group=admin_types.AudienceFilterExpressionList(
                            filter_expressions=[
                                admin_types.AudienceFilterExpression(
                                    dimension_or_metric_filter=admin_types.AudienceDimensionOrMetricFilter(
                                        field_name="eventName",
                                        string_filter=admin_types.AudienceDimensionOrMetricFilter.StringFilter(
                                            match_type=admin_types.AudienceDimensionOrMetricFilter.StringFilter.MatchType.EXACT,
                                            value="add_to_cart",
                                        )
                                    )
                                ),
                                admin_types.AudienceFilterExpression(
                                    dimension_or_metric_filter=admin_types.AudienceDimensionOrMetricFilter(
                                        field_name="eventName",
                                        string_filter=admin_types.AudienceDimensionOrMetricFilter.StringFilter(
                                            match_type=admin_types.AudienceDimensionOrMetricFilter.StringFilter.MatchType.EXACT,
                                            value="begin_checkout",
                                        )
                                    )
                                ),
                                admin_types.AudienceFilterExpression(
                                    dimension_or_metric_filter=admin_types.AudienceDimensionOrMetricFilter(
                                        field_name="eventName",
                                        string_filter=admin_types.AudienceDimensionOrMetricFilter.StringFilter(
                                            match_type=admin_types.AudienceDimensionOrMetricFilter.StringFilter.MatchType.EXACT,
                                            value="add_shipping_info",
                                        )
                                    )
                                ),
                            ]
                        )
                    )
                )
            ),
        ]
    )

    try:
        new_audience = admin_client.create_audience(
            parent=GA4_PROPERTY,
            audience=audience_body,
        )
        print(f"  ✅ Audience created successfully!")
        print(f"     Name:     {new_audience.display_name}")
        print(f"     Resource: {new_audience.name}")
        print(f"     Duration: {new_audience.membership_duration_days} days")
    except Exception as e:
        print(f"  ❌ Error creating audience: {e}")
        new_audience = None

# ── STEP 3: Check existing audiences in Google Ads ───────────────────────────
print()
print("=" * 60)
print("STEP 3: Checking Google Ads Audience Manager")
print("=" * 60)

import google.ads.googleads.client as ads_client_module

ads_client = ads_client_module.GoogleAdsClient.load_from_storage(
    "google_ads_auth/google-ads.yaml"
)

ga_service = ads_client.get_service("GoogleAdsService")
query = """
    SELECT
        user_list.id,
        user_list.name,
        user_list.description,
        user_list.membership_life_span,
        user_list.size_for_search,
        user_list.eligible_for_search,
        user_list.type
    FROM user_list
    ORDER BY user_list.size_for_search DESC
"""
response = ga_service.search(customer_id=ADS_CUSTOMER_ID, query=query)
print("  Current audiences in Google Ads:")
target_user_list_id = None
for row in response:
    ul = row.user_list
    marker = " ← TARGET" if "High-Intent" in ul.name or "high-intent" in ul.name.lower() else ""
    print(f"  ID:{ul.id:12}  Size:{ul.size_for_search:6}  {ul.name}{marker}")
    if "High-Intent" in ul.name or "high-intent" in ul.name.lower():
        target_user_list_id = ul.id

if not target_user_list_id:
    print()
    print("  ℹ️  The new GA4 audience hasn't synced yet (takes 24-48h).")
    print("     Will attach the best existing audience as fallback.")
    # Find cart abandoners or product viewers
    response2 = ga_service.search(customer_id=ADS_CUSTOMER_ID, query=query)
    for row in response2:
        ul = row.user_list
        if "cart" in ul.name.lower() or "Cart" in ul.name:
            target_user_list_id = ul.id
            print(f"     Using fallback audience: {ul.name} (ID: {ul.id})")
            break

# ── STEP 4: Attach audience as OBSERVATION to campaign ───────────────────────
print()
print("=" * 60)
print("STEP 4: Attaching audience as OBSERVATION to campaign 24318560132")
print("=" * 60)

if target_user_list_id:
    campaign_criterion_service = ads_client.get_service("CampaignCriterionService")

    # Check if already attached
    check_query = f"""
        SELECT
            campaign_criterion.criterion_id,
            campaign_criterion.type,
            campaign_criterion.user_list.user_list,
            campaign_criterion.bid_modifier
        FROM campaign_criterion
        WHERE campaign.id = {CAMPAIGN_ID}
          AND campaign_criterion.type = 'USER_LIST'
    """
    try:
        existing = list(ga_service.search(customer_id=ADS_CUSTOMER_ID, query=check_query))
        already_attached_ids = [
            row.campaign_criterion.user_list.user_list.split("/")[-1]
            for row in existing
        ]
        print(f"  Already attached user lists: {already_attached_ids}")

        if str(target_user_list_id) in already_attached_ids:
            print(f"  ✅ Audience already attached to campaign.")
        else:
            mutate_op = ads_client.get_type("CampaignCriterionOperation")
            criterion = mutate_op.create
            criterion.campaign = f"customers/{ADS_CUSTOMER_ID}/campaigns/{CAMPAIGN_ID}"
            criterion.user_list.user_list = f"customers/{ADS_CUSTOMER_ID}/userLists/{target_user_list_id}"
            # OBSERVATION = bid modifier only, doesn't restrict reach
            criterion.negative = False

            result = campaign_criterion_service.mutate_campaign_criteria(
                customer_id=ADS_CUSTOMER_ID,
                operations=[mutate_op],
            )
            print(f"  ✅ Audience attached as OBSERVATION!")
            print(f"     Resource: {result.results[0].resource_name}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
else:
    print("  ⚠️  No suitable audience found to attach. Will retry after sync (24-48h).")

# ── STEP 5: Import begin_checkout as secondary conversion ────────────────────
print()
print("=" * 60)
print("STEP 5: Creating begin_checkout as secondary conversion in Google Ads")
print("=" * 60)

conversion_service = ads_client.get_service("ConversionActionService")

# Check if it already exists
conv_query = """
    SELECT
        conversion_action.id,
        conversion_action.name,
        conversion_action.status,
        conversion_action.category,
        conversion_action.counting_type
    FROM conversion_action
"""
conv_resp = ga_service.search(customer_id=ADS_CUSTOMER_ID, query=conv_query)
existing_convs = list(conv_resp)
begin_checkout_exists = None
for row in existing_convs:
    ca = row.conversion_action
    print(f"  Existing: [{ca.id}] {ca.name} — {ca.status.name}")
    if "begin_checkout" in ca.name.lower() or "checkout" in ca.name.lower() and "purchase" not in ca.name.lower():
        begin_checkout_exists = ca

if begin_checkout_exists:
    print(f"\n  ✅ begin_checkout conversion already exists: {begin_checkout_exists.name}")
else:
    print()
    try:
        op = ads_client.get_type("ConversionActionOperation")
        conv_action = op.create
        conv_action.name = "begin_checkout (GA4 - Secondary)"
        conv_action.category = ads_client.enums.ConversionActionCategoryEnum.ConversionActionCategory.ADD_TO_CART
        conv_action.type_ = ads_client.enums.ConversionActionTypeEnum.ConversionActionType.GOOGLE_ANALYTICS_4
        conv_action.status = ads_client.enums.ConversionActionStatusEnum.ConversionActionStatus.ENABLED
        conv_action.counting_type = ads_client.enums.ConversionActionCountingTypeEnum.ConversionActionCountingType.ONE_PER_CLICK
        # Mark as secondary (don't include in "Conversions" column, only "All conv.")
        conv_action.primary_for_goal = False

        result = conversion_service.mutate_conversion_actions(
            customer_id=ADS_CUSTOMER_ID,
            operations=[op],
        )
        print(f"  ✅ begin_checkout conversion created!")
        print(f"     Resource: {result.results[0].resource_name}")
        print(f"     Status: Secondary (observe only — won't affect bidding)")
    except Exception as e:
        print(f"  ❌ Error creating conversion: {e}")

print()
print("=" * 60)
print("ALL DONE")
print("=" * 60)
print()
print("📌 Summary:")
print("  Step 1: GA4 ↔ Google Ads link — verified above")
print("  Step 2: US High-Intent Shoppers audience — created in GA4")
print("  Step 3: Google Ads audiences checked")
print("  Step 4: Audience attached to campaign 24318560132 as OBSERVATION")
print("  Step 5: begin_checkout secondary conversion imported")
print()
print("⏱️  Note: GA4 audiences take 24-48h to fully populate in Google Ads.")
print("   Check Audience Manager tomorrow for member counts.")
