/**
 * Leafanoo — ChatGPT Ads / OpenAI Measurement Pixel
 * Shopify Web Pixel (Customer Events)
 *
 * SDK URL: https://bzrcdn.openai.com/sdk/oaiq.min.js
 * Events tracked:
 *  - page_viewed
 *  - product_viewed (contents_viewed)
 *  - product_added_to_cart (items_added)
 *  - checkout_started
 *  - checkout_completed (order_created)
 */

// 1. Install & Load OpenAI Ads Measurement Pixel SDK
(function (w, d, s, u) {
  if (w.oaiq) return;
  var q = function () {
    q.q.push(arguments);
  };
  q.q = [];
  w.oaiq = q;
  var js = d.createElement(s);
  js.async = true;
  js.src = u;
  var f = d.getElementsByTagName(s)[0];
  if (f && f.parentNode) {
    f.parentNode.insertBefore(js, f);
  } else {
    (d.head || d.body).appendChild(js);
  }
})(window, document, "script", "https://bzrcdn.openai.com/sdk/oaiq.min.js");

// 2. Initialize Pixel with Pixel ID
// Replace <YOUR-PIXEL-ID> with your Pixel ID from OpenAI Ads Manager
const PIXEL_ID = "<YOUR-PIXEL-ID>";

oaiq("init", {
  pixelId: PIXEL_ID,
  debug: false
});

// Helper: Convert price float to cents integer (OpenAI expects integer values)
function toCents(amount) {
  return Math.round((parseFloat(amount) || 0) * 100);
}

// ----------------------------------------------------
// Event: checkout_started
// ----------------------------------------------------
analytics.subscribe("checkout_started", (event) => {
  const checkout = event.data?.checkout;
  if (!checkout) return;

  const totalAmount = toCents(checkout.subtotalPrice?.amount || checkout.totalPrice?.amount || 0);
  const currency = checkout.currencyCode || "USD";

  const contents = (checkout.lineItems || []).map((item) => ({
    id: item.variant?.sku || item.variant?.id?.toString() || "",
    name: item.title || "",
    content_type: "product",
    quantity: item.quantity || 1
  }));

  oaiq("measure", "checkout_started", {
    type: "contents",
    amount: totalAmount,
    currency: currency,
    contents: contents
  });
});

// ----------------------------------------------------
// Event: checkout_completed (order_created)
// ----------------------------------------------------
analytics.subscribe("checkout_completed", (event) => {
  const checkout = event.data?.checkout;
  if (!checkout) return;

  const totalAmount = toCents(checkout.subtotalPrice?.amount || checkout.totalPrice?.amount || 0);
  const currency = checkout.currencyCode || "USD";
  const orderId = checkout.order?.id?.toString() || event.id || "";

  const contents = (checkout.lineItems || []).map((item) => ({
    id: item.variant?.sku || item.variant?.id?.toString() || "",
    name: item.title || "",
    content_type: "product",
    quantity: item.quantity || 1
  }));

  oaiq("measure", "order_created", {
    type: "contents",
    amount: totalAmount,
    currency: currency,
    contents: contents
  }, {
    event_id: orderId
  });
});

// ----------------------------------------------------
// Event: product_added_to_cart (items_added)
// ----------------------------------------------------
analytics.subscribe("product_added_to_cart", (event) => {
  const cartLine = event.data?.cartLine;
  if (!cartLine) return;

  const price = toCents(cartLine.merchandise?.price?.amount || 0);
  const currency = cartLine.merchandise?.price?.currencyCode || "USD";

  oaiq("measure", "items_added", {
    type: "contents",
    amount: price,
    currency: currency,
    contents: [
      {
        id: cartLine.merchandise?.sku || cartLine.merchandise?.id?.toString() || "",
        name: cartLine.merchandise?.product?.title || "",
        content_type: "product",
        quantity: cartLine.quantity || 1,
        amount: price,
        currency: currency
      }
    ]
  });
});
