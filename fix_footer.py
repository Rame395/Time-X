import re

with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

pattern = r'<section class="py-24 bg-white text-black">\s*<div class="max-w-\[1440px\] mx-auto px-6 lg:px-12">\s*<div class="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4">\s*<div>\s*<h2 class="text-2xl sm:text-3xl font-black uppercase tracking-tight">Follow The Craft</h2>.*?id="newsletter-message"></p>\s*</div>\s*</section>'

replacement = """<section class="py-16 md:py-24 bg-[#faf9f7] text-black">
<div class="max-w-[1440px] mx-auto px-6 lg:px-12 flex flex-col lg:flex-row justify-between items-center gap-12 lg:gap-24">
  <div class="w-full lg:w-1/2">
    <h2 class="text-3xl font-black tracking-tight uppercase mb-4 text-center lg:text-left">Stay In The Loop.</h2>
    <p class="text-[11px] font-mono text-gray-500 uppercase tracking-widest mb-8 text-center lg:text-left">Be the first to know about new drops, collections and TIME-X stories.</p>
    <form class="flex flex-col sm:flex-row gap-3" id="newsletter-form" onsubmit="handleNewsletterSubmit(event)">
      <input class="flex-1 bg-transparent border border-black/20 px-4 h-14 text-[11px] tracking-widest text-black placeholder-black/40 focus:outline-none focus:border-black" name="email" placeholder="YOUR EMAIL" required="" type="email"/>
      <select class="bg-transparent border border-black/20 px-4 h-14 text-[11px] tracking-widest text-black focus:outline-none focus:border-black uppercase w-full sm:w-auto" name="category">
        <option class="text-timexBlack" value="all">I'm Interested In...</option>
        <option class="text-timexBlack" value="men">Men's Drops</option>
        <option class="text-timexBlack" value="women">Women's Drops</option>
        <option class="text-timexBlack" value="other">Everything Else</option>
      </select>
      <button class="bg-timexWhite text-timexBlack px-8 h-14 text-[11px] font-semibold tracking-widest uppercase hover:bg-timexLightGrey transition-colors w-full sm:w-auto" type="submit">Subscribe</button>
    </form>
    <p class="hidden text-[11px] uppercase tracking-widest mt-4 text-center lg:text-left" id="newsletter-message"></p>
  </div>
  <div class="w-full lg:w-auto flex flex-col items-center lg:items-end border-t lg:border-t-0 border-black/10 pt-12 lg:pt-0 text-center lg:text-right">
    <h2 class="text-2xl font-black uppercase tracking-tight mb-2">Follow The Craft</h2>
    <p class="text-[11px] font-mono text-gray-600 uppercase tracking-widest mb-6">@timex.official</p>
    <div class="flex gap-4">
      <a class="inline-flex items-center justify-center border border-black/20 px-8 h-14 text-[11px] font-semibold uppercase tracking-widest hover:border-black transition-colors" href="https://instagram.com" target="_blank">Instagram</a>
      <a class="inline-flex items-center justify-center border border-black/20 px-8 h-14 text-[11px] font-semibold uppercase tracking-widest hover:border-black transition-colors" href="https://facebook.com" target="_blank">Facebook</a>
    </div>
  </div>
</div>
</section>"""

new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)

if new_html != html:
    with open("frontend/index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print("Replaced successfully!")
else:
    print("Regex did not match.")
