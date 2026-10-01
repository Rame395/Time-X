with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Featured section
html = html.replace('class="py-24 bg-timexOffWhite hidden" id="featured-section"', 'class="py-14 bg-timexOffWhite hidden" id="featured-section"')

# On Sale
html = html.replace('class="hidden py-24 bg-white text-black" id="on-sale"', 'class="hidden py-14 bg-white text-black" id="on-sale"')

# Best Sellers
html = html.replace('class="hidden py-24 bg-gray-100 text-black" id="best-sellers"', 'class="hidden py-14 bg-gray-100 text-black" id="best-sellers"')

# Editorial 01 section
html = html.replace('class="relative py-24 min-h-[50vh]', 'class="relative py-14 min-h-[40vh]')

# Category tiles
html = html.replace('class="py-24 bg-white text-black">', 'class="py-14 bg-white text-black">')

# Story / Philosophy
html = html.replace('class="py-24 bg-white text-black" id="story"', 'class="py-14 bg-white text-black" id="story"')

# Pre-footer (newsletter + social)
html = html.replace('class="py-24 bg-[#faf9f7] text-black"', 'class="py-14 bg-[#faf9f7] text-black"')

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Reduced all section spacing from py-24 (96px) to py-14 (56px).")
