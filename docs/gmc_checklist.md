# Google Merchant Center & Free Listings: 40-Point Checklist

Comprehensive readiness checklist for Google Merchant Center (GMC) compliance, Free Shopping Listings, and Google Ads product feed integrity.

---

## 🏛️ Section 1: Merchant Center Account & Store Level (Store Owner Action)

| # | Requirement | Status | Responsible | Notes |
|---|---|---|---|---|
| 1 | Create Google Merchant Center Account | 🔲 Pending | You | Visit merchants.google.com |
| 2 | Claim & Verify Domain in Search Console | 🔲 Pending | You | Add TXT record or HTML meta tag |
| 3 | Add Real Business Physical Address | 🔲 Pending | You | Must match address on store Contact page |
| 4 | Add Customer Support Phone Number | 🔲 Pending | You | Must be a working phone number |
| 5 | Add Support Email Address | 🔲 Pending | You | E.g., support@leafanoo.com |
| 6 | Configure Exact Shipping Rates in GMC | 🔲 Pending | You | Shipping table in GMC must match checkout |
| 7 | Configure Return Policy in GMC | 🔲 Pending | You | Match 30-day policy on website |
| 8 | Link Google Analytics 4 (`G-...`) | 🔲 Pending | You | For conversion tracking |
| 9 | Enable "Free Product Listings" Add-on | 🔲 Pending | You | In GMC Settings → Growth → Manage programs |
| 10 | Connect Shopify Google & YouTube App | 🔲 Pending | You | Official Shopify app from App Store |

---

## 💻 Section 2: Theme & Storefront Compliance (Implemented in Theme)

| # | Requirement | Status | Responsible | Notes |
|---|---|---|---|---|
| 11 | HTTPS Canonical URLs | ✅ Implemented | Theme | Rendered in `snippets/meta-tags.liquid` |
| 12 | Server-Rendered Product Prices | ✅ Implemented | Theme | Rendered in initial HTML in `price.liquid` |
| 13 | Structured Data (Product JSON-LD) | ✅ Implemented | Theme | Server-rendered in `structured-data-product.liquid` |
| 14 | Structured Data (BreadcrumbList) | ✅ Implemented | Theme | Schema included in `structured-data-breadcrumb.liquid` |
| 15 | Structured Data (Organization) | ✅ Implemented | Theme | Rendered on all pages in `theme.liquid` |
| 16 | Structured Data (FAQPage) | ✅ Implemented | Theme | Validated FAQ JSON-LD on FAQ pages |
| 17 | Working Add-to-Cart & Checkout | ✅ Implemented | Theme | Standard Shopify `/checkout` flow |
| 18 | Working Search & Filter Functionality | ✅ Implemented | Theme | Accessible predictive search & filters |
| 19 | Responsive Mobile-First Layout | ✅ Implemented | Theme | Passes Google Mobile-Friendly standards |
| 20 | Fast Page Speed & Lazy Loading | ✅ Implemented | Theme | Native `loading="lazy"` on all images |

---

## 🏷️ Section 3: Product Feed & Catalog Data Quality

| # | Requirement | Status | Responsible | Notes |
|---|---|---|---|---|
| 21 | Unique Product SKU / ID | ✅ Implemented | Catalog | Every product has unique SKU |
| 22 | Descriptive Title (under 150 chars) | ✅ Implemented | Catalog | Clean formatting: Title + Brand |
| 23 | Detailed Description (over 70 chars) | ✅ Implemented | Catalog | Features, specifications, and materials |
| 24 | High-Resolution Images (min 500x500px) | 🔲 User Action | You | Add licensed product photography |
| 25 | Brand / Vendor Attribute | ✅ Implemented | Catalog | Real brands mapped (OXO, Rubbermaid, etc.) |
| 26 | Google Product Category Mapped | ✅ Implemented | Catalog | Exact taxonomy paths configured |
| 27 | Item Condition = 'new' | ✅ Implemented | Catalog | Explicitly declared 'new' |
| 28 | MPN (Manufacturer Part Number) | ✅ Implemented | Catalog | Real MPNs assigned per product |
| 29 | GTIN / Barcode (where verified) | ✅ Implemented | Catalog | Included in master database |
| 30 | Stock Availability Indicator | ✅ Implemented | Catalog | `in_stock` status declared |

---

## 📜 Section 4: Mandatory Legal Policies & Customer Trust

| # | Requirement | Status | Responsible | Notes |
|---|---|---|---|---|
| 31 | Shipping Policy Page | ✅ Template Ready | You | Fill in carrier delivery windows & rates |
| 32 | Refund & Return Policy Page | ✅ Template Ready | You | Include return timeframe, conditions, address |
| 33 | Privacy Policy Page | ✅ Template Ready | You | Compliant with GDPR/CCPA |
| 34 | Terms of Service Page | ✅ Template Ready | You | Standard terms of service |
| 35 | Contact Us Page with Live Form | ✅ Implemented | Theme | Template `page.contact.json` |
| 36 | Transparent Pricing (No Hidden Fees) | ✅ Implemented | Theme | All taxes/shipping noted before checkout |
| 37 | No Fake Countdowns / Fake Scarcity | ✅ Implemented | Theme | Zero fake urgency widgets |
| 38 | No Fabricated Testimonials | ✅ Implemented | Theme | No fake reviews injected |
| 39 | Clear Payment Methods Displayed | ✅ Implemented | Theme | Real payment icons in footer |
| 40 | 256-Bit SSL Encrypted Checkout | ✅ Implemented | Shopify | Managed natively by Shopify Checkout |
