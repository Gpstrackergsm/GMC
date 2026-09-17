# Leafanoo — Shopify OS 2.0 General Merchandise Store & GMC Architecture

Production-ready Shopify Online Store 2.0 theme, curated physical product catalog, Google Merchant Center feed integration, and technical SEO architecture built for **Leafanoo** ([https://leafanoo.com/](https://leafanoo.com/)).

---

## 📁 Repository Structure

```
GMC/
├── theme/                             # Complete Shopify OS 2.0 Theme
│   ├── assets/                        # CSS, JS, responsive logic
│   │   ├── theme.css                  # Modern design system & styles
│   │   ├── theme.js                   # Core JS (sticky nav, AJAX ATC, steppers)
│   │   ├── cart-drawer.js             # AJAX slide-out cart drawer
│   │   └── predictive-search.js       # Live search suggestions
│   ├── config/                        # Theme settings & schema
│   │   ├── settings_schema.json       # Visual customizer options
│   │   └── settings_data.json         # Default typography & color palette
│   ├── layout/                        # Global layouts
│   │   ├── theme.liquid               # Master layout with JSON-LD & meta tags
│   │   └── password.liquid            # Password / Pre-launch page
│   ├── locales/                       # Translations & text strings
│   │   └── en.default.json            # English locale definitions
│   ├── sections/                      # Liquid sections (OS 2.0)
│   │   ├── header.liquid              # Sticky header with megamenu & search
│   │   ├── footer.liquid              # Multi-column footer & policy links
│   │   ├── announcement-bar.liquid    # Dismissible top announcement bar
│   │   ├── hero-banner.liquid         # Hero banner with CTA
│   │   ├── featured-collections.liquid# Department showcase grid
│   │   ├── featured-products.liquid   # Trending products grid
│   │   ├── main-product.liquid        # Product page (media, variants, GMC data)
│   │   ├── main-collection-product-grid.liquid # Filterable collection catalog
│   │   ├── main-search.liquid         # Search results
│   │   ├── main-cart.liquid           # Dedicated cart page
│   │   ├── cart-drawer.liquid         # Slide-out cart drawer
│   │   ├── main-page.liquid           # Standard static page layout
│   │   ├── main-blog.liquid           # Blog index grid
│   │   ├── main-article.liquid        # Blog article with schema
│   │   ├── main-404.liquid            # 404 error page
│   │   ├── related-products.liquid    # Related recommendations
│   │   ├── faq-accordion.liquid       # Accordion FAQ with Schema.org
│   │   ├── trust-bar.liquid           # Factual shipping/security badges
│   │   ├── newsletter.liquid          # Email capture section
│   │   └── recently-viewed.liquid     # LocalStorage recently viewed products
│   ├── snippets/                      # Reusable components
│   │   ├── product-card.liquid        # Reusable product grid card
│   │   ├── price.liquid               # Server-rendered price & sale markup
│   │   ├── image-srcset.liquid        # Responsive image helper
│   │   ├── structured-data-product.liquid # Google Product Schema (JSON-LD)
│   │   ├── structured-data-breadcrumb.liquid # BreadcrumbList (JSON-LD)
│   │   ├── structured-data-organization.liquid # Organization (JSON-LD)
│   │   ├── meta-tags.liquid           # OpenGraph & SEO meta tags
│   │   ├── filters.liquid             # Storefront collection filters
│   │   ├── variant-picker.liquid      # Accessible variant selector
│   │   ├── quantity-input.liquid      # Accessible quantity stepper
│   │   └── icon-*.liquid              # Inline SVG icons set
│   └── templates/                     # OS 2.0 JSON templates & customer Liquid
├── catalog/                           # Product Data & Validation
│   ├── products_master.csv            # Master research catalog (all metadata)
│   ├── shopify_import.csv             # Shopify-ready direct import CSV
│   └── gmc_feed_report.csv            # Google Merchant Center audit report
├── scripts/                           # Tooling & Validation
│   ├── generate_catalog.py            # Generates master and Shopify CSVs
│   ├── validate_catalog.py            # Schema, handle, price, and duplicate validator
│   └── check_images.py                # Image HTTP status & MIME checker
└── docs/                              # Documentation
    ├── deployment.md                  # Step-by-step Shopify CLI deploy guide
    ├── gmc_checklist.md               # 40-point Google Merchant Center audit
    ├── seo_implementation.md          # Technical & On-Page SEO summary
    └── test_report.md                 # Complete verification report
```

---

## 🚀 Quick Start: Deploying the Theme

### 1. Prerequisites
- **Node.js 18+** & **Shopify CLI v3+** installed (`npm install -g @shopify/cli`)
- Active Shopify store and admin access

### 2. Push to Shopify Development Theme
```bash
cd theme/
shopify theme push --development --store=YOUR-STORE.myshopify.com
```

### 3. Import the Product Catalog
1. Validate the catalog:
   ```bash
   python3 scripts/validate_catalog.py catalog/shopify_import.csv
   ```
2. Navigate to **Shopify Admin → Products → Import**.
3. Upload `catalog/shopify_import.csv`.
4. The products will import with complete pricing, vendors, SKUs, and Google taxonomy mapped.

---

## 🛡️ Google Merchant Center Setup
See [`docs/gmc_checklist.md`](docs/gmc_checklist.md) for the complete 40-point account and feed readiness checklist.
