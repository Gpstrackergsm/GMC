# Shopify Theme Deployment & Operations Guide

This guide details how to deploy the Leafanoo OS 2.0 theme to your Shopify store using the official Shopify CLI and configure essential store settings.

---

## 🛠️ Step 1: Install Shopify CLI

If you haven't already installed the Shopify CLI:

### macOS (via Homebrew)
```bash
brew tap shopify/shopify
brew install shopify-cli
```

### Windows / Linux (via npm)
```bash
npm install -g @shopify/cli @shopify/theme
```

---

## 🔐 Step 2: Authenticate with Your Store

Log into your Shopify account:
```bash
shopify auth login
```

---

## 🚀 Step 3: Push Theme to Development Theme

Always push to an unpublished development theme first to preview changes safely without affecting live traffic:

```bash
cd /path/to/GMC/theme
shopify theme push --development --store=YOUR-STORE.myshopify.com
```

The CLI will output a live **Theme Preview URL** and a direct link to the **Shopify Theme Editor**.

---

## 🎨 Step 4: Configure Theme Settings in Shopify Admin

In **Online Store → Themes → Customize**:

1. **Logo & Favicon:** Upload your logo (SVG or high-res PNG) and set width to `140px`.
2. **Colors:** The theme defaults to Leafanoo Forest Green (`#2D6A4F`), Gold Accent (`#D4A853`), and Clean Warm Surface (`#FAFAF7`). Customize palette if desired.
3. **Navigation Menus:**
   - Under **Navigation**, ensure your `main-menu` contains links to your main departments (`/collections/home-kitchen`, `/collections/home-organization`, etc.).
   - Configure your `footer` menu with links to legal policy pages.

---

## 📦 Step 5: Import the Catalog

1. Run the local validator first:
   ```bash
   python3 scripts/validate_catalog.py catalog/shopify_import.csv
   ```
2. In Shopify Admin, navigate to **Products → Import**.
3. Select `catalog/shopify_import.csv`.
4. Leave *"Overwrite any current products that have the same handle"* unchecked unless updating existing items.
5. Click **Upload and preview**, then confirm **Import products**.

---

## 🚢 Step 6: Publish Theme

When you are ready to make the Leafanoo theme live:

```bash
shopify theme publish --store=YOUR-STORE.myshopify.com
```

Or click **Publish** directly in **Online Store → Themes**.
