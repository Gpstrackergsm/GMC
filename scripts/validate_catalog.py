#!/usr/bin/env python3
"""
Catalog Validation Script for Leafanoo Shopify & Google Merchant Center
Validates CSV catalog structure, checks required Shopify & GMC fields,
detects duplicate handles/SKUs, verifies price validity, and outputs a summary report.
"""

import sys
import os
import csv
import re

REQUIRED_SHOPIFY_COLUMNS = [
    'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Type', 'Tags', 'Published',
    'Option1 Name', 'Option1 Value', 'Variant SKU', 'Variant Price',
    'Variant Requires Shipping', 'Variant Taxable', 'Status'
]

def validate_shopify_csv(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    print(f"\n=======================================================")
    print(f"Validating Shopify Catalog CSV: {file_path}")
    print(f"=======================================================\n")

    handles = set()
    skus = set()
    errors = []
    warnings = []
    total_rows = 0

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Check required columns
        missing_cols = [c for c in REQUIRED_SHOPIFY_COLUMNS if c not in headers]
        if missing_cols:
            errors.append(f"Missing required columns in CSV: {', '.join(missing_cols)}")

        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            handle = row.get('Handle', '').strip()
            title = row.get('Title', '').strip()
            vendor = row.get('Vendor', '').strip()
            price_str = row.get('Variant Price', '').strip()
            compare_str = row.get('Variant Compare At Price', '').strip()
            sku = row.get('Variant SKU', '').strip()
            gpc = row.get('Google Shopping / Google Product Category', '').strip()

            # Handle checks
            if not handle:
                errors.append(f"Row {row_idx}: Handle is missing.")
            elif not re.match(r'^[a-z0-9-]+$', handle):
                errors.append(f"Row {row_idx}: Handle '{handle}' contains invalid characters (must be lowercase alphanumeric + hyphens only).")
            elif handle in handles:
                warnings.append(f"Row {row_idx}: Duplicate handle '{handle}' (variant row or duplicate).")
            handles.add(handle)

            # Title checks
            if not title:
                errors.append(f"Row {row_idx}: Title is empty.")
            elif len(title) > 150:
                warnings.append(f"Row {row_idx}: Title exceeds 150 characters ({len(title)} chars) - may be truncated in GMC.")

            # Vendor checks
            if not vendor:
                warnings.append(f"Row {row_idx}: Vendor / Brand is empty.")

            # Price validation
            if not price_str:
                errors.append(f"Row {row_idx}: Variant Price is missing.")
            else:
                try:
                    price = float(price_str.replace('$', '').replace(',', ''))
                    if price <= 0:
                        errors.append(f"Row {row_idx}: Price must be greater than 0.")
                    
                    if compare_str:
                        compare_price = float(compare_str.replace('$', '').replace(',', ''))
                        if compare_price <= price:
                            warnings.append(f"Row {row_idx}: Compare-at price (${compare_price}) should be strictly greater than retail price (${price}).")
                except ValueError:
                    errors.append(f"Row {row_idx}: Invalid price format '{price_str}'.")

            # SKU check
            if sku:
                if sku in skus:
                    warnings.append(f"Row {row_idx}: Duplicate SKU '{sku}'.")
                skus.add(sku)
            else:
                warnings.append(f"Row {row_idx}: SKU is missing.")

            # Google Category
            if not gpc:
                warnings.append(f"Row {row_idx}: Google Shopping / Google Product Category is missing.")

    print(f"Total Products / Rows Processed: {total_rows}")
    print(f"Unique Handles: {len(handles)}")
    print(f"Unique SKUs: {len(skus)}")
    print(f"Errors Found: {len(errors)}")
    print(f"Warnings Found: {len(warnings)}\n")

    if errors:
        print("ERRORS (must fix before import):")
        for err in errors[:15]:
            print(f"  ❌ {err}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more errors.")
        print()

    if warnings:
        print("WARNINGS (review recommended):")
        for warn in warnings[:10]:
            print(f"  ⚠️  {warn}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings.")
        print()

    if not errors:
        print("✅ Validation PASSED! Catalog is ready for Shopify import.")
        return True
    else:
        print("❌ Validation FAILED. Please resolve errors.")
        return False

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'catalog/shopify_import.csv'
    success = validate_shopify_csv(target)
    sys.exit(0 if success else 1)
