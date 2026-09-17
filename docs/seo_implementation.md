# Technical & Content SEO Implementation Summary

Summary of architectural, structured data, and on-page SEO implementations for Leafanoo.

---

## 1. Technical SEO Architecture

### Canonicalization
- Every page outputs a strict `<link rel="canonical" href="...">` in `<head>` via `snippets/meta-tags.liquid`.
- Variant URLs (`?variant=...`) and paginated URLs (`?page=...`) are canonicalized appropriately to prevent index bloat.

### Semantic Heading Hierarchy
- **Homepage:** Single `<h1>` embedded in `hero-banner.liquid`, followed by `<h2>` for section titles (`featured-collections`, `featured-products`, `trust-bar`).
- **Collection Pages:** Single `<h1>` for collection title, `<h2>` for filter section, `<h3>` for product titles in cards.
- **Product Pages:** Single `<h1>` for product title, `<h2>` for description and related products.
- **Articles:** Single `<h1>` for article headline, `<h2>`/`<h3>` for body subheadings.

### Crawl Control (`robots.txt.liquid`)
- Standard Shopify admin, checkout, cart, and internal scripts are cleanly disallowed.
- Googlebot, Googlebot-Image, and Storebot-Google are explicitly supported with directives.
- Auto-linked to `{{ shop.url }}/sitemap.xml`.

---

## 2. Structured Data (Schema.org JSON-LD)

All structured data is **server-rendered** in initial HTML (not injected via client-side DOM manipulation), ensuring search engine crawlers and Google Merchant Center bots capture full metadata instantly.

1. **`Product` Schema (`snippets/structured-data-product.liquid`):**
   - `@type: "Product"`
   - `name`, `description`, `image`, `brand`
   - `offers`: `price`, `priceCurrency`, `availability`, `url`, `priceValidUntil`
   - `sku`, `mpn`, `gtin` (when present)

2. **`BreadcrumbList` Schema (`snippets/structured-data-breadcrumb.liquid`):**
   - Dynamically builds hierarchical breadcrumb navigation for Products, Collections, Articles, and Pages.

3. **`Organization` Schema (`snippets/structured-data-organization.liquid`):**
   - Brand name, official URL, logo asset URL, and customer support contact point.

4. **`FAQPage` Schema (`sections/faq-accordion.liquid`):**
   - Validated Schema.org markup for rich FAQ snippets in search results.

5. **`BlogPosting` Schema (`sections/main-article.liquid`):**
   - Article headline, author, datePublished, dateModified, and publisher data.

---

## 3. On-Page Metadata & OpenGraph

- Optimized default SEO title template: `[Page Title] | [Shop Name]`
- OpenGraph tags (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`)
- Twitter Card tags (`summary_large_image`)
- Fast, asynchronous stylesheet loading with `<noscript>` fallback.
