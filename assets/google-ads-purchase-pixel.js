/**
 * Leafanoo — Google Ads Purchase Conversion Pixel
 * Conversion Action: Purchase
 * send_to: AW-18473205895/tqRdCOuSxIUdEIeB2-hE
 *
 * Installed via Shopify Customer Events (Custom Pixel).
 * This pixel fires ONLY on successful checkout_completed events,
 * passing real order value, currency, and unique transaction ID
 * to prevent duplicate conversion counting.
 *
 * The base Google tag (AW-18473205895) is already present
 * in theme/layout/theme.liquid on every page.
 */

analytics.subscribe('checkout_completed', (event) => {
  const checkout = event.data.checkout;

  if (!checkout) return;

  const orderValue = parseFloat(
    checkout.subtotalPrice?.amount ||
    checkout.totalPrice?.amount ||
    0
  );

  const currency  = checkout.currencyCode || 'USD';
  const orderId   = checkout.order?.id?.toString() || event.id || '';

  // Fire Google Ads Purchase conversion
  gtag('event', 'conversion', {
    'send_to':        'AW-18473205895/tqRdCOuSxIUdEIeB2-hE',
    'value':          orderValue,
    'currency':       currency,
    'transaction_id': orderId
  });
});
