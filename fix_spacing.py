import re

with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Replace py-32 on on-sale
html = html.replace('class="hidden py-32 bg-white text-black" id="on-sale"', 'class="hidden py-24 bg-white text-black" id="on-sale"')

# Replace py-32 on best-sellers
html = html.replace('class="hidden py-32 bg-gray-100 text-black" id="best-sellers"', 'class="hidden py-24 bg-gray-100 text-black" id="best-sellers"')

# Replace py-24 md:py-32 on Editorial 01
html = html.replace('class="relative py-24 md:py-32 min-h-[50vh]', 'class="relative py-24 min-h-[50vh]')

# Replace py-36 on story
html = html.replace('class="py-36 bg-white text-black" id="story"', 'class="py-24 bg-white text-black" id="story"')

# Replace py-16 md:py-24 on pre-footer
html = html.replace('class="py-16 md:py-24 bg-[#faf9f7] text-black"', 'class="py-24 bg-[#faf9f7] text-black"')

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Standardized all section spacing to py-24.")
