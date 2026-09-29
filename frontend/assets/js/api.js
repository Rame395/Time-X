/* TIME-X storefront — shared API + cart helpers. Loaded on every page. */

async function apiGet(path) {
  const res = await fetch(path, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`);
  return res.json();
}

async function apiJSON(method, path, body) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${method} ${path} failed (${res.status})`);
  }
  return res.json();
}

async function apiForm(method, path, formData) {
  const res = await fetch(path, { method, credentials: "same-origin", body: formData });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${method} ${path} failed (${res.status})`);
  }
  return res.json();
}

function formatNPR(amount) {
  return `NPR ${Number(amount).toLocaleString("en-IN")}`;
}

/* ---------------- Cart ---------------- */

async function getCart() {
  return apiGet("/api/cart");
}

async function addToCart(productId, color, size, quantity = 1) {
  return apiJSON("POST", "/api/cart/items", { product_id: productId, color, size, quantity });
}

async function updateCartItem(itemId, quantity) {
  return apiJSON("PATCH", `/api/cart/items/${itemId}`, { quantity });
}

async function removeCartItem(itemId) {
  const res = await fetch(`/api/cart/items/${itemId}`, { method: "DELETE", credentials: "same-origin" });
  if (!res.ok) throw new Error("Failed to remove item");
  return res.json();
}

async function refreshCartBadge() {
  try {
    const cart = await getCart();
    document.querySelectorAll("#cart-counter").forEach((el) => {
      el.textContent = `(${cart.item_count})`;
    });
    return cart;
  } catch (e) {
    return null;
  }
}

/* Toast notifications are defined in shared.js (loaded after this file) —
   that version supports the isError parameter used by cart/wishlist feedback. */

/* ---------------- WhatsApp ordering ---------------- */

async function whatsAppOrderFromCart(cart, settings, orderNumber) {
  const phone = settings.whatsapp_number;
  let lines = [`Hello TIME-X, I would like to place an order:`, ""];
  if (orderNumber) lines.push(`*Order:* #${orderNumber}`, "");
  cart.items.forEach((i) => {
    lines.push(`*${i.title}*`);
    lines.push(`Color: ${i.color} / Size: ${i.size} / Qty: ${i.quantity}`);
    lines.push(`Price: ${formatNPR(i.line_total)}`);
    lines.push("");
  });
  lines.push(`*Total:* ${formatNPR(cart.total)}`);
  lines.push("");
  lines.push("Please confirm availability and shipping details.");
  const message = encodeURIComponent(lines.join("\n"));
  window.open(`https://wa.me/${phone}?text=${message}`, "_blank");
}
