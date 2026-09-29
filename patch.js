const fs = require('fs');
let content = fs.readFileSync('frontend/assets/js/shared.js', 'utf8');

// 1. Disable mobile top search form
content = content.replace('initMobileTopSearch();', '// initMobileTopSearch();');

// 2. Change initSiteSearch to bind to both triggers
content = content.replace(
  'const trigger = document.getElementById("search-trigger");',
  'const triggers = [document.getElementById("search-trigger"), document.getElementById("mobile-search-trigger")];'
);
content = content.replace(
  'if (!trigger) return; // page doesn\'t have a search trigger in its header',
  'if (!triggers[0] && !triggers[1]) return;'
);
content = content.replace(
  'trigger.addEventListener("click", openOverlay);',
  'triggers.forEach(t => t && t.addEventListener("click", openOverlay));'
);

fs.writeFileSync('frontend/assets/js/shared.js', content);
