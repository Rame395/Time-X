/* TIME-X storefront — shared header/menu behavior. Loaded on every page, after api.js. */

document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.getElementById("menu-toggle");
  const mobileMenu = document.getElementById("mobile-menu");
  if (menuToggle && mobileMenu) {
    const closeMenu = () => {
      mobileMenu.classList.add('translate-x-full'); setTimeout(() => mobileMenu.classList.add('hidden'), 500);
      document.body.classList.remove("mobile-menu-open");
      menuToggle.setAttribute("aria-expanded", "false");
    };
    const openMenu = () => {
      mobileMenu.classList.remove('hidden'); void mobileMenu.offsetWidth; mobileMenu.classList.remove('translate-x-full');
      document.body.classList.add("mobile-menu-open");
      menuToggle.setAttribute("aria-expanded", "true");
    };
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.addEventListener("click", () => {
      if (mobileMenu.classList.contains("translate-x-full")) openMenu(); else closeMenu();
    });
    document.getElementById("mobile-menu-close")?.addEventListener("click", closeMenu);
    document.querySelectorAll(".mobile-link").forEach((link) => link.addEventListener("click", closeMenu));
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMenu(); });
    mobileMenu.addEventListener("click", (event) => { if (event.target === mobileMenu) closeMenu(); });
  }

  refreshCartBadge();
  initSiteSearch();
  applySiteSettingsToPage();
  showAdminReturnLinkIfLoggedIn();
  // initMobileTopSearch();
});

/* ---------------- Shared pricing helper ---------------- */
function getDiscountPercent(price, compareAtPrice) {
  const current = Number(price || 0);
  const original = Number(compareAtPrice || 0);
  if (!(current > 0 && original > current)) return 0;
  return Math.round(((original - current) / original) * 100);
}

/* ---------------- Mobile top search ---------------- */
function initMobileTopSearch() {
  if (document.getElementById('mobile-top-search')) return;
  const header = document.getElementById('site-header');
  if (!header) return;
  const form = document.createElement('form');
  form.id = 'mobile-top-search';
  form.action = 'shop.html';
  form.method = 'get';
  form.innerHTML = `
    <div class="mobile-top-search-inner">
      <svg fill="none" height="15" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24" width="15"><circle cx="11" cy="11" r="7"></circle><line x1="21" x2="16.65" y1="21" y2="16.65"></line></svg>
      <input name="search" type="search" placeholder="Search watches, brands, collections…" autocomplete="off">
    </div>`;
  header.insertAdjacentElement('afterend', form);
}

/* ---------------- "Back to Admin" badge (storefront pages only, admins only) ---------------- */

async function showAdminReturnLinkIfLoggedIn() {
  // This file is only loaded by storefront pages (the admin pages have their own
  // scripts), so this never runs while actually inside /admin/ — exactly where a
  // "back to admin" link would be redundant anyway.
  try {
    const res = await fetch("/api/admin/me", { credentials: "same-origin" });
    if (!res.ok) return; // not an admin session — show nothing, silently

    const badge = document.createElement("a");
    badge.href = "/admin/dashboard.html";
    badge.className =
      "fixed bottom-6 right-6 z-[80] bg-timexBlack text-timexWhite text-[11px] font-semibold uppercase tracking-widest px-4 py-3 shadow-lg hover:bg-timexTextGrey transition-colors flex items-center gap-2";
    badge.innerHTML = `<span>⚙</span><span>Back to Admin</span>`;
    document.body.appendChild(badge);
  } catch (e) {
    // Settings/network hiccup — fail silently, this is a convenience affordance only.
  }
}

/* ---------------- Search overlay ---------------- */

function initSiteSearch() {
  const triggers = [document.getElementById("search-trigger"), document.getElementById("mobile-search-trigger")];
  if (!triggers[0] && !triggers[1]) return;

  const overlay = document.createElement("div");
  overlay.id = "site-search-overlay";
  overlay.className = "fixed inset-0 bg-timexBlack/95 z-[70] hidden flex flex-col items-center px-6 pt-28";
  overlay.innerHTML = `
    <button id="site-search-close" aria-label="Close search" class="absolute top-6 right-8 text-timexWhite text-xl font-mono uppercase tracking-widest hover:opacity-70">✕ Close</button>
    <div class="w-full max-w-xl">
      <div class="flex gap-3 items-center border-b border-white/30 focus-within:border-white">
        <input id="site-search-input" type="text" placeholder="SEARCH PRODUCTS…"
          class="flex-1 bg-transparent text-timexWhite placeholder-white/40 text-lg tracking-wide py-3 focus:outline-none border-0">
        <select id="site-search-scope" class="bg-transparent text-white/60 text-[11px] uppercase tracking-widest py-3 focus:outline-none border-0 cursor-pointer">
          <option value="" class="text-black">All</option>
          <option value="men" class="text-black">Men</option>
          <option value="women" class="text-black">Women</option>
          <option value="Shoes" class="text-black">Shoes</option>
          <option value="Clothing" class="text-black">Clothing</option>
          <option value="Accessories" class="text-black">Accessories</option>
          <option value="Sports" class="text-black">Sports</option>
        </select>
      </div>
      <div id="site-search-results" class="mt-6 space-y-1 max-h-[60vh] overflow-y-auto"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  const input = overlay.querySelector("#site-search-input");
  const scope = overlay.querySelector("#site-search-scope");
  const results = overlay.querySelector("#site-search-results");
  const closeBtn = overlay.querySelector("#site-search-close");

  function openOverlay() {
    overlay.classList.remove("hidden");
    setTimeout(() => input.focus(), 50);
  }
  function closeOverlay() {
    overlay.classList.add("hidden");
    input.value = "";
    scope.value = "";
    results.innerHTML = "";
  }

  triggers.forEach(t => t && t.addEventListener("click", openOverlay));
  closeBtn.addEventListener("click", closeOverlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeOverlay(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeOverlay(); });

  let debounceTimer;
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q && !scope.value) { results.innerHTML = ""; return; }
    debounceTimer = setTimeout(() => runSearch(q), 250);
  });
  scope.addEventListener("change", () => {
    const q = input.value.trim();
    if (!q && !scope.value) { results.innerHTML = ""; return; }
    runSearch(q);
  });

  const GENDER_SCOPES = new Set(["men", "women"]);

  async function runSearch(q) {
    results.innerHTML = `<p class="text-white/40 text-xs uppercase tracking-widest py-4">Searching…</p>`;
    try {
      const params = new URLSearchParams();
      if (q) params.set("search", q);
      const scopeValue = scope.value;
      if (scopeValue) {
        if (GENDER_SCOPES.has(scopeValue)) params.set("category", scopeValue);
        else params.set("department", scopeValue);
      }
      const products = await apiGet(`/api/products?${params.toString()}`);
      if (!products.length) {
        const what = q ? `"${q}"` : (scope.options[scope.selectedIndex]?.textContent || "this category");
        results.innerHTML = `<p class="text-white/40 text-xs uppercase tracking-widest py-4">No products match ${what}.</p>`;
        return;
      }
      const cardHtml = (p) => `
        <a href="product.html?slug=${p.slug}" class="flex items-center gap-4 py-3 border-b border-white/10 hover:bg-white/5 px-2 -mx-2 transition-colors">
          <div class="w-12 h-16 bg-white/10 overflow-hidden flex-shrink-0">
            ${p.primary_image ? `<img src="${p.primary_image}" class="w-full h-full object-cover">` : ""}
          </div>
          <div class="flex-1 text-left">
            <p class="text-timexWhite text-sm uppercase tracking-wide">${p.title}</p>
            <p class="text-white/40 text-[11px] uppercase">${p.subcategory || ""}</p>
          </div>
          <span class="text-timexWhite text-xs font-semibold">${formatNPR(p.price)}</span>
        </a>`;
      // Browsing a scope with no text query: show every matching item (that's the
      // whole point of picking "Men"/"Shoes" etc). An active text search still caps
      // at a shortlist, since it's meant as a quick jump-to-product, not a full browse.
      const shown = q ? products.slice(0, 8) : products;
      results.innerHTML = shown.map(cardHtml).join("");
    } catch (e) {
      results.innerHTML = `<p class="text-white/40 text-xs uppercase tracking-widest py-4">Search unavailable right now.</p>`;
    }
  }
}

/* ---------------- Settings-driven footer / contact / social ---------------- */

async function applySiteSettingsToPage() {
  const contactEls = document.querySelectorAll("[data-contact-phone]");
  const igEls = document.querySelectorAll("[data-social='instagram']");
  const ttEls = document.querySelectorAll("[data-social='tiktok']");
  const fbEls = document.querySelectorAll("[data-social='facebook']");
  const logoImgs = document.querySelectorAll("[data-site-logo]");
  const logoTexts = document.querySelectorAll("[data-site-logo-text]");
  const brandNameEls = document.querySelectorAll("[data-site-brand-name]");
  const taglineEls = document.querySelectorAll("[data-site-tagline]");
  const brandShowcase = document.getElementById("brand-showcase-img");
  if (!contactEls.length && !igEls.length && !ttEls.length && !fbEls.length && !logoImgs.length && !brandNameEls.length && !taglineEls.length && !brandShowcase) return;

  try {
    const settings = await apiGet("/api/settings");

    if (settings.site_logo_url && logoImgs.length) {
      logoImgs.forEach((el) => {
        el.src = settings.site_logo_url;
        el.classList.remove("hidden");
      });
      logoTexts.forEach((el) => el.classList.add("hidden"));
    }

    if (settings.site_brand_name) {
      brandNameEls.forEach((el) => { el.textContent = settings.site_brand_name; });
      if (!settings.site_logo_url) {
        logoTexts.forEach((el) => {
          el.textContent = settings.site_brand_name;
          el.classList.remove("hidden");
        });
      }
    }

    if (settings.site_tagline) {
      taglineEls.forEach((el) => { el.textContent = settings.site_tagline; });
    }

    if (settings.brand_showcase_url && brandShowcase) {
      brandShowcase.src = settings.brand_showcase_url;
      brandShowcase.classList.remove("hidden");
    }

    contactEls.forEach((el) => {
      if (settings.contact_phone) {
        el.textContent = `Contact — ${settings.contact_phone}`;
        el.href = `https://wa.me/${settings.contact_phone.replace(/\D/g, "")}`;
        el.target = "_blank";
      }
    });

    igEls.forEach((el) => {
      if (settings.instagram_url) {
        el.href = settings.instagram_url;
        el.target = "_blank";
        el.rel = "noopener";
      } else {
        el.classList.add("opacity-40", "pointer-events-none");
      }
    });

    ttEls.forEach((el) => {
      if (settings.tiktok_url) {
        el.href = settings.tiktok_url;
        el.target = "_blank";
        el.rel = "noopener";
      } else {
        el.classList.add("opacity-40", "pointer-events-none");
      }
    });

    fbEls.forEach((el) => {
      if (settings.facebook_url) {
        el.href = settings.facebook_url;
        el.target = "_blank";
        el.rel = "noopener";
      } else {
        el.classList.add("opacity-40", "pointer-events-none");
      }
    });
  } catch (e) {
    // Settings unavailable — leave the placeholder links/text logo as-is rather than break the page.
  }
}

/* ---------------- WhatsApp order -> real trackable order ---------------- */

function promptWhatsAppContact() {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "fixed inset-0 bg-timexBlack/90 z-[90] flex items-center justify-center px-6";
    overlay.innerHTML = `
      <div class="bg-timexWhite text-timexBlack w-full max-w-sm p-7 space-y-4">
        <h3 class="text-sm font-black uppercase tracking-widest">Before we open WhatsApp</h3>
        <p class="text-[11px] text-timexTextGrey uppercase tracking-wider leading-relaxed">
          Just your name and number, so we can find this order when you message us — everything else gets sorted over chat.
        </p>
        <div>
          <label class="block text-[10px] font-mono uppercase tracking-widest text-timexTextGrey mb-1">Full Name</label>
          <input id="wa-contact-name" type="text" required placeholder="YOUR NAME" class="w-full bg-transparent border border-timexLightGrey px-4 py-3 text-xs tracking-widest focus:outline-none focus:border-timexBlack">
        </div>
        <div>
          <label class="block text-[10px] font-mono uppercase tracking-widest text-timexTextGrey mb-1">Phone Number</label>
          <input id="wa-contact-phone" type="tel" required placeholder="98XXXXXXXX" class="w-full bg-transparent border border-timexLightGrey px-4 py-3 text-xs tracking-widest focus:outline-none focus:border-timexBlack">
        </div>
        <p id="wa-contact-error" class="hidden text-[11px] text-red-600 uppercase tracking-wider"></p>
        <div class="flex gap-2 pt-1">
          <button id="wa-contact-cancel" class="flex-1 border border-timexLightGrey text-timexBlack py-3 text-[11px] font-semibold uppercase tracking-widest hover:bg-timexLightGrey transition-colors">Cancel</button>
          <button id="wa-contact-continue" class="flex-1 bg-[#25D366] text-white py-3 text-[11px] font-semibold uppercase tracking-widest hover:opacity-90 transition-opacity">Continue</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const cleanup = (result) => { overlay.remove(); resolve(result); };
    overlay.querySelector("#wa-contact-cancel").addEventListener("click", () => cleanup(null));
    overlay.addEventListener("click", (e) => { if (e.target === overlay) cleanup(null); });
    overlay.querySelector("#wa-contact-continue").addEventListener("click", () => {
      const name = overlay.querySelector("#wa-contact-name").value.trim();
      const phone = overlay.querySelector("#wa-contact-phone").value.trim();
      const errorEl = overlay.querySelector("#wa-contact-error");
      if (!name || !phone) {
        errorEl.textContent = "Please fill in both your name and phone number.";
        errorEl.classList.remove("hidden");
        return;
      }
      const parts = name.split(" ");
      cleanup({ first_name: parts[0], last_name: parts.slice(1).join(" ") || parts[0], phone });
    });
  });
}

async function createWhatsAppOrder(contact) {
  const fd = new FormData();
  fd.append("first_name", contact.first_name);
  fd.append("last_name", contact.last_name);
  fd.append("phone", contact.phone);
  fd.append("payment_method", "whatsapp");
  return apiForm("POST", "/api/orders", fd);
}

/* ---------------- Mega menu (Men / Women category dropdown) ---------------- */

function injectMegaMenuStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .mega-menu-panel {
      position: fixed; top: 96px; left: 0; right: 0; z-index: 45;
      background: #FFFFFF; color: #111111;
      border-bottom: 1px solid #EAEAEA;
      box-shadow: 0 12px 24px -8px rgba(0,0,0,0.15);
      opacity: 0; visibility: hidden; transform: translateY(-8px);
      transition: opacity .2s ease, transform .2s ease, visibility .2s;
    }
    .mega-menu-panel.open { opacity: 1; visibility: visible; transform: translateY(0); }
    @media (max-width: 1023px) {
      /* Desktop-only feature — triggered by hover nav links that are themselves
         lg:hidden on mobile. display:none (not just hidden/closed) keeps it out
         of layout entirely so it can never affect mobile viewport width. */
      .mega-menu-panel { display: none !important; }
    }
  `;
  document.head.appendChild(style);
}

function initMegaMenu() {
  injectMegaMenuStyles();
  const taxonomyCache = {};

  async function getTaxonomy(gender) {
    if (!taxonomyCache[gender]) {
      try {
        taxonomyCache[gender] = await apiGet(`/api/products/taxonomy?category=${gender}`);
      } catch (e) {
        taxonomyCache[gender] = {};
      }
    }
    return taxonomyCache[gender];
  }

  function panelHtml(gender, taxonomy) {
    const departments = Object.keys(taxonomy);
    if (!departments.length) {
      return `<p class="text-xs text-timexTextGrey uppercase tracking-widest py-8 text-center">No products yet.</p>`;
    }
    const columns = departments.map((dept) => `
      <div>
        <a href="${gender}.html?department=${encodeURIComponent(dept)}" class="block text-xs font-bold uppercase tracking-widest text-timexBlack hover:opacity-60 mb-3">${dept}</a>
        <ul class="space-y-2">
          ${taxonomy[dept].map((sub) => `
            <li><a href="${gender}.html?department=${encodeURIComponent(dept)}&subcategory=${encodeURIComponent(sub)}" class="text-xs font-medium text-timexBlack hover:opacity-60 transition-opacity">${sub}</a></li>
          `).join('')}
        </ul>
      </div>`).join('');
    return `<div class="grid grid-cols-2 sm:grid-cols-4 gap-8">${columns}</div>`;
  }

  function buildPanel(gender) {
    const panel = document.createElement('div');
    panel.className = 'mega-menu-panel';
    panel.dataset.gender = gender;
    panel.innerHTML = `<div class="max-w-[1440px] mx-auto px-6 lg:px-12 py-10 overflow-y-auto" style="max-height: 50vh;">
      <p class="text-xs text-timexTextGrey uppercase tracking-widest py-8 text-center">Loading…</p>
    </div>`;
    document.body.appendChild(panel);
    return panel;
  }

  function closeAllPanels() {
    document.querySelectorAll('.mega-menu-panel').forEach((p) => p.classList.remove('open'));
  }

  async function openPanel(gender, panel) {
    closeAllPanels();
    panel.classList.add('open');
    const taxonomy = await getTaxonomy(gender);
    panel.querySelector('div').innerHTML = panelHtml(gender, taxonomy);
  }

  ['men', 'women'].forEach((gender) => {
    const trigger = document.querySelector(`header nav a[href="${gender}.html"]`);
    if (!trigger) return; // this page's header doesn't have this link (e.g. gallery's "The Story" variant) — skip quietly

    const panel = buildPanel(gender);
    let closeTimer;
    const cancelClose = () => clearTimeout(closeTimer);
    const scheduleClose = () => { closeTimer = setTimeout(() => panel.classList.remove('open'), 200); };

    trigger.addEventListener('mouseenter', () => { cancelClose(); openPanel(gender, panel); });
    trigger.addEventListener('click', () => {
      // Clicking Men/Women always navigates to the full page. The mega menu is
      // a hover preview only, so it never hijacks navigation or leaves the page
      // looking partially covered.
    });
    trigger.addEventListener('mouseleave', scheduleClose);
    panel.addEventListener('mouseenter', cancelClose);
    panel.addEventListener('mouseleave', scheduleClose);
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.mega-menu-panel') && !e.target.closest('header nav a[href="men.html"]') && !e.target.closest('header nav a[href="women.html"]')) {
      closeAllPanels();
    }
  });
}

document.addEventListener('DOMContentLoaded', initMegaMenu);

/* ---------------- Toast notifications (cart/wishlist success feedback) ---------------- */

function showToast(message, isError = false) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    container.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:center;pointer-events:none;';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.cssText = `
    background:${isError ? '#fff7f5' : '#ffffff'};
    color:${isError ? '#9f2d20' : '#141311'};
    border:1px solid ${isError ? '#c86c5d' : '#b08a45'};
    padding:12px 24px;
    font-size:11px;
    font-weight:600;
    letter-spacing:0.05em;
    text-transform:uppercase;
    box-shadow:0 10px 30px rgba(20,19,17,0.16);
    opacity:0;
    transform:translateY(10px);
    transition:opacity 0.25s ease, transform 0.25s ease;
    white-space:nowrap;
  `;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 2600);
}

/* ---------------- Atelier motion: touch-friendly product video ---------------- */
function atelierTouchVideos() {
  const videos = document.querySelectorAll(".product-card-video");
  if (!videos.length) return;
  videos.forEach((video) => {
    const card = video.closest("[class*='aspect-']");
    if (!card) return;
    const play = () => {
      video.muted = true;
      const p = video.play();
      if (p && p.catch) p.catch(() => {});
      card.classList.add("video-active");
    };
    const pause = () => {
      video.pause();
      card.classList.remove("video-active");
    };
    card.addEventListener("touchstart", play, { passive: true });
    card.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "touch") play();
    }, { passive: true });
  });
}
document.addEventListener("DOMContentLoaded", () => {
  atelierTouchVideos();
  document.body.classList.add("page-fade");
});


/* ---------------- Autocomplete Search ---------------- */
function initAutocompleteSearch() {
  const fmtNPR = (v) => v ? 'NPR ' + Number(v).toLocaleString('en-IN') : '';
  const searchInputs = document.querySelectorAll('input[name="search"]');
  
  searchInputs.forEach(input => {
    const wrapper = input.closest('.relative') || input.parentElement;
    wrapper.style.position = 'relative';
    
    const dropdown = document.createElement('div');
    dropdown.style.cssText = 'position:absolute;top:calc(100% + 8px);left:0;right:0;background:#fff;color:#111;border:1px solid rgba(0,0,0,0.1);border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,0.15);z-index:9999;overflow:hidden;display:none;flex-direction:column;max-height:70vh;overflow-y:auto;';
    wrapper.appendChild(dropdown);
    
    let debounceTimer;
    
    input.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      clearTimeout(debounceTimer);
      
      if (query.length < 1) {
        dropdown.style.display = 'none';
        return;
      }
      
      debounceTimer = setTimeout(async () => {
        try {
          dropdown.style.display = 'flex';
          dropdown.innerHTML = '<div style="padding:16px;text-align:center;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#999;">Searching...</div>';
          
          const results = await apiGet('/api/products?search=' + encodeURIComponent(query));
          
          if (!results || results.length === 0) {
            dropdown.innerHTML = '<div style="padding:20px;text-align:center;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#999;">No results for &ldquo;' + query + '&rdquo;</div>';
            return;
          }
          
          const topResults = results.slice(0, 6);
          
          let html = '<div style="padding:10px 16px 8px;border-bottom:1px solid #f0f0f0;"><span style="font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:#aaa;font-family:monospace;">' + results.length + ' results found</span></div>';
          
          html += topResults.map(p => `
            <a href="product.html?slug=${p.slug}" style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #f5f5f5;text-decoration:none;color:inherit;transition:background .15s;" onmouseover="this.style.background='#fafafa'" onmouseout="this.style.background=''">
              <div style="width:44px;height:44px;background:#f5f5f5;border-radius:6px;overflow:hidden;flex-shrink:0;">
                <img src="${p.primary_image || ''}" style="width:100%;height:100%;object-fit:contain;" alt="">
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#111;">${p.title}</div>
                <div style="font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#aaa;margin-top:2px;font-family:monospace;">${p.brand_name || 'TIME-X'}</div>
              </div>
              <div style="font-size:11px;font-weight:700;color:#111;flex-shrink:0;">${fmtNPR(p.price)}</div>
            </a>
          `).join('');
          
          html += `<a href="shop.html?search=${encodeURIComponent(query)}" style="display:flex;align-items:center;justify-content:center;gap:6px;padding:12px 16px;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#666;text-decoration:none;background:#fafafa;border-top:1px solid #f0f0f0;transition:all .15s;" onmouseover="this.style.color='#111';this.style.background='#f0f0f0'" onmouseout="this.style.color='#666';this.style.background='#fafafa'">
            View All ${results.length} Results &rarr;
          </a>`;
          
          dropdown.innerHTML = html;
          
        } catch (err) {
          dropdown.style.display = 'none';
        }
      }, 180);
    });
    
    document.addEventListener('click', (e) => {
      if (!wrapper.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    });
    
    input.addEventListener('focus', () => {
      if (input.value.trim().length >= 1 && dropdown.innerHTML.length > 50) {
        dropdown.style.display = 'flex';
      }
    });
  });
}
document.addEventListener("DOMContentLoaded", initAutocompleteSearch);






