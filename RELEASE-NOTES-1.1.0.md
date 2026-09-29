# TIME-X Nepal — Production Release 1.1.0

## Storefront redesign

- Replaced the previous TIME-X wordmark presentation with the supplied TIME-X Nepal logo, rendered in a premium gold treatment.
- Introduced a black / ivory / champagne-gold visual system across storefront pages.
- Switched storefront headings to an editorial serif treatment with refined spacing and gold accents.
- Redesigned the desktop header into a luxury multi-level navigation treatment with promotional strip, centered logo, utility actions, and category navigation.
- Redesigned the mobile navigation overlay to match the premium reference direction.
- Preserved separate navigation destinations for Men, Women, New Arrivals, Collections, Blogs, Gallery, Account, and Cart.
- Kept New Arrivals as its own dedicated page and product query.
- Preserved product video behavior, cart, checkout, account, order, admin, and API connections.
- The supplied logo is bundled as a default asset and fresh database seeding now uses it as the default site logo.

## Production deployment

The existing production Docker/PostgreSQL/Caddy deployment configuration remains in place. Configure `.env` with real production credentials before launch.
