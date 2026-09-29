
        const CATEGORY = 'men';
        const SIZES = ['36mm', '38mm', '40mm', '42mm', '44mm'];
        const PRICE_BRACKETS = [
            { label: 'Under NPR 5,000', min: null, max: 4999 },
            { label: 'NPR 5,000 — NPR 10,000', min: 5000, max: 10000 },
            { label: 'NPR 10,000+', min: 10001, max: null },
        ];

        const params = new URLSearchParams(window.location.search);
        const state = {
            department: params.get('department') || null,
            subcategory: params.get('subcategory') || null,
            size: params.get('size') || null,
            priceIndex: params.has('price') ? Number(params.get('price')) : null,
            collection: params.get('collection') || null,
            is_new_arrival: params.get('new') === 'true' ? true : null,
            sort: params.get('sort') || 'latest',
        };

        let allProductsUnfiltered = [];

        function productCardHTML(p) {
            const secondary = p.secondary_image || p.primary_image;
            const discount = getDiscountPercent(p.price, p.compare_at_price);
            const priceHTML = p.compare_at_price && discount
                ? `<span class="sm:whitespace-nowrap"><span class="text-xs font-semibold tracking-tight">${formatNPR(p.price)}</span> <span class="text-[10px] text-timexLightGrey line-through">${formatNPR(p.compare_at_price)}</span></span>`
                : `<span class="text-xs font-semibold tracking-tight">${formatNPR(p.price)}</span>`;
            return `
            <a href="product.html?slug=${p.slug}" class="group cursor-pointer block">
                <div class="relative w-full aspect-[3/4] bg-timexCharcoal overflow-hidden mb-3"${p.video_url ? ` onmouseenter="this.querySelector('.product-card-video').play()" onmouseleave="this.querySelector('.product-card-video').pause()" ontouchstart="this.querySelector('.product-card-video')?.play().catch(()=>{})"` : ''}>
                    <img src="${p.primary_image || ''}" alt="${p.title}" class="product-primary-img absolute inset-0 w-full h-full object-cover object-center">
                    <img src="${secondary}" alt="${p.title}" class="product-secondary-img absolute inset-0 w-full h-full object-cover object-center opacity-0">
                    ${p.video_url ? `<video class="product-card-video absolute inset-0 w-full h-full object-cover object-center opacity-0" muted loop playsinline preload="metadata" src="${p.video_url}"></video>` : ''}
                    ${discount ? `<span class="absolute top-3 left-3 discount-badge text-[10px] font-semibold uppercase tracking-widest px-2 py-1 z-10">${discount}% OFF</span>` : ''}
                    <div class="absolute inset-x-0 bottom-0 p-3 product-quick-action bg-gradient-to-t from-black/60 to-transparent">
                        <button onclick="event.preventDefault(); quickAdd(${p.id}, '${p.slug}', '${p.title.replace(/'/g, "\'")}')" class="w-full bg-timexWhite text-timexBlack py-2.5 text-[10px] font-semibold uppercase tracking-widest hover:bg-timexSilver transition-colors">
                            Add To Cart +
                        </button>
                    </div>
                </div>
                <div class="flex flex-col text-left gap-1">
                    <h3 class="text-xs font-bold uppercase tracking-widest text-timexBlack leading-relaxed">${p.title}</h3>
                    <p class="text-[9px] text-gray-500 uppercase tracking-widest font-mono">${p.subcategory || p.department || 'TIME-X'}</p>
                    <div class="mt-1">${priceHTML}</div>
                </div>
            </a>`;
        }

        async function quickAdd(productId, slug, title) {
            try {
                await addToCart(productId, '', '');
                await refreshCartBadge();
                showToast(`Added to Cart: ${title}`);
            } catch (e) {
                showToast('Please pick a size on the product page', true);
                window.location.href = `product.html?slug=${slug}`;
            }
        }

        function renderDepartmentFacets() {
            const counts = {};
            allProductsUnfiltered.forEach((p) => {
                const d = p.department || 'Classic';
                counts[d] = (counts[d] || 0) + 1;
            });
            const list = document.getElementById('department-list');
            const allActive = !state.department ? 'filter-active' : 'text-timexLightGrey';
            let html = `<li><a href="#" onclick="setDepartment(null); return false;" class="${allActive} flex justify-between items-center hover:text-timexWhite transition-colors">All <span>(${allProductsUnfiltered.length})</span></a></li>`;
            Object.keys(counts).sort().forEach((d) => {
                if (!d || d === 'null' || !counts[d]) return;
                const active = state.department === d ? 'filter-active' : 'text-timexLightGrey';
                html += `<li><a href="#" onclick="setDepartment('${d}'); return false;" class="${active} flex justify-between items-center hover:text-timexWhite transition-colors">${d} <span>(${counts[d]})</span></a></li>`;
            });
            list.innerHTML = html;
        }

        function renderSubcategoryFacets() {
            const scoped = state.department
                ? allProductsUnfiltered.filter((p) => (p.department || 'Classic') === state.department)
                : allProductsUnfiltered;
            const counts = {};
            scoped.forEach((p) => {
                counts[p.subcategory] = (counts[p.subcategory] || 0) + 1;
            });
            const list = document.getElementById('subcategory-list');
            const allActive = !state.subcategory ? 'filter-active' : 'text-timexLightGrey';
            let html = `<li><a href="#" onclick="setSubcategory(null); return false;" class="${allActive} flex justify-between items-center hover:text-timexWhite transition-colors">All <span>(${scoped.length})</span></a></li>`;
            Object.keys(counts).sort().forEach((sub) => {
                  if (!sub || sub === 'null') return;
                const active = state.subcategory === sub ? 'filter-active' : 'text-timexLightGrey';
                html += `<li><a href="#" onclick="setSubcategory('${sub}'); return false;" class="${active} flex justify-between items-center hover:text-timexWhite transition-colors">${sub} <span>(${counts[sub]})</span></a></li>`;
            });
            list.innerHTML = html;
        }

        function renderSizeFacet() {
            const el = document.getElementById('size-filter');
            el.innerHTML = SIZES.map((s) => {
                const active = state.size === s ? 'size-btn-active' : 'border-timexDarkBorder hover:border-timexWhite';
                return `<button onclick="toggleSize('${s}')" class="border ${active} py-2 text-xs font-medium uppercase transition-colors">${s}</button>`;
            }).join('');
        }

        function renderPriceFacet() {
            const el = document.getElementById('price-filter');
            el.innerHTML = PRICE_BRACKETS.map((b, i) => {
                const checked = state.priceIndex === i ? 'checked' : '';
                return `<label class="flex items-center space-x-3 cursor-pointer">
                    <input type="checkbox" ${checked} onclick="togglePrice(${i})" class="accent-timexWhite price-active">
                    <span class="text-timexLightGrey">${b.label}</span>
                </label>`;
            }).join('');
        }

        function setDepartment(dept) { state.department = dept; state.subcategory = null; loadProducts(); }
        function setSubcategory(sub) { state.subcategory = sub; loadProducts(); }
        function toggleSize(s) { state.size = state.size === s ? null : s; loadProducts(); }
        function togglePrice(i) { state.priceIndex = state.priceIndex === i ? null : i; loadProducts(); }

        function buildQuery() {
            const qs = new URLSearchParams();
            qs.set('category', CATEGORY);
            if (state.size) qs.set('size', state.size);
            if (state.collection) qs.set('collection', state.collection);
            if (state.is_new_arrival) qs.set('is_new_arrival', 'true');
            if (state.priceIndex !== null) {
                const b = PRICE_BRACKETS[state.priceIndex];
                if (b.min !== null) qs.set('min_price', b.min);
                if (b.max !== null) qs.set('max_price', b.max);
            }
            qs.set('sort', state.sort);
            return qs.toString();
        }

        
        function updateURL() {
            const qs = new URLSearchParams();
            if (state.department) qs.set('department', state.department);
            if (state.subcategory) qs.set('subcategory', state.subcategory);
            if (state.size) qs.set('size', state.size);
            if (state.priceIndex !== null) qs.set('price', state.priceIndex);
            if (state.collection) qs.set('collection', state.collection);
            if (state.is_new_arrival) qs.set('new', 'true');
            if (state.sort && state.sort !== 'latest') qs.set('sort', state.sort);
            
            const newUrl = window.location.pathname + (qs.toString() ? '?' + qs.toString() : '');
            window.history.replaceState(null, '', newUrl);
        }

        async function loadProducts() {
            const grid = document.getElementById('product-grid');
            try {
                // Fetched broad (no department/subcategory) so facet counts for BOTH stay
                // accurate; department and subcategory are then applied together client-side.
                allProductsUnfiltered = await apiGet(`/api/products?${buildQuery()}`);
                renderDepartmentFacets();
                renderSubcategoryFacets();
                renderSizeFacet();
                renderPriceFacet();
                updateURL();

                const filtered = allProductsUnfiltered.filter((p) => {
                    if (state.department && (p.department || 'Classic') !== state.department) return false;
                    if (state.subcategory && p.subcategory !== state.subcategory) return false;
                    return true;
                });

                document.getElementById('results-count').textContent = `Showing ${filtered.length} Product${filtered.length === 1 ? '' : 's'}`;
                grid.innerHTML = filtered.length
                    ? filtered.map(productCardHTML).join('')
                    : '<p class="col-span-full text-center text-xs uppercase tracking-widest text-timexLightGrey py-16">No products match these filters.</p>';
            } catch (e) {
                grid.innerHTML = '<p class="col-span-full text-center text-xs uppercase tracking-widest text-timexLightGrey py-16">Could not load products right now.</p>';
            }
        }

        document.getElementById('sort-select').value = state.sort;
        document.getElementById('sort-select').addEventListener('change', (e) => {
            state.sort = e.target.value;
            loadProducts();
        });

        (async function loadHeroOverride() {
            try {
                const images = await apiGet('/api/site-images/men_hero');
                if (images.length) document.getElementById('hero-bg-img').src = images[0].url;
            } catch (e) { /* keep the default */ }
        })();
        loadProducts();
    
