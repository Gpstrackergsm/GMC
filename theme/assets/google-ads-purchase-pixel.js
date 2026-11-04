/**
 * Leafanoo — Google Ads Purchase Conversion Pixel
 * Conversion Action: Purchase (3)
 * send_to: AW-18488363853/V3orCLDeuJQdEM2W-O9E
 *
 * Installed via Shopify Customer Events (Custom Pixel).
 * Fires ONLY on checkout_completed events.
 */

analytics.subscribe('checkout_completed', (event) => {
  const checkout = event.data.checkout;
  if (!checkout) return;

  // Use totalPrice (includes tax/shipping) for revenue — fallback chain
  const orderValue = parseFloat(
    checkout.totalPrice?.amount ||
    checkout.subtotalPrice?.amount ||
    0
  );

  const currency = checkout.currencyCode || 'USD';

  // Extract order ID — Shopify may provide it in different fields
  const orderId = (
    checkout.order?.id ||
    checkout.order?.name ||
    event.data?.checkout?.token ||
    event.id ||
    ''
  ).toString().replace('gid://shopify/Order/', '');

  // ── 1. Google Ads Purchase conversion ──────────────────────────────────────
  gtag('event', 'conversion', {
    'send_to':        'AW-18488363853/V3orCLDeuJQdEM2W-O9E',
    'value':          orderValue,
    'currency':       currency,
    'transaction_id': orderId
  });

  // ── 2. GA4 purchase event (fixes $0 revenue in GA4 reports) ────────────────
  gtag('event', 'purchase', {
    'transaction_id': orderId,
    'value':          orderValue,
    'currency':       currency,
    'items': (checkout.lineItems || []).map(item => ({
      item_id:   item.variant?.sku || item.variant?.id || item.id,
      item_name: item.title,
      quantity:  item.quantity,
      price:     parseFloat(item.variant?.price?.amount || item.finalLinePrice?.amount || 0) / (item.quantity || 1),
    }))
  });
});
