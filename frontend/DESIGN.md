# BIRGE — Campus noticeboard

Approved direction: retain the green BIRGE identity, `b.` mark, Noto Sans,
existing sections and their order. Improve the interface without changing the
backend, API endpoints, ownership model or business rules.

## Direction

- Product: everyday campus services for SDU students.
- Character: friendly, composed, practical.
- World: a university noticeboard, with light neutral surfaces and green ink.
- Moments: real menu photographs/prices and students' own announcements.
- Signature: a small pair of vertical strokes, repeated in the active navigation
  and the community introduction.

## Nine passes

1. **Spacing:** one 4 px rhythm, 20–24 px card padding, 32 px desktop page edges,
   consistent gaps and controls. A mobile drawer replaces the narrow icon rail.
2. **Color:** retained green accent and lime brand mark; neutral card surfaces,
   three text roles, subdued borders. Verified text contrast includes 4.63:1 for
   muted text on the soft light surface and 9.47:1 for the primary light button.
3. **Icons:** local Lucide SVG symbols, consistent 18 px size and 1.5 stroke.
   Removed decorative emoji, orbit art and notification indicators without data.
4. **Copy:** Kazakh service descriptions and clear action labels. The hero CTA
   explicitly opens the canteen menu; the lost-item action explicitly marks it
   completed. Profile/report notices describe current limitations honestly.
5. **Type:** local Noto Sans retained for Kazakh/Russian/English; 12–16 px reading
   text, 18–24 px card/section headings, 28–48 px page/hero headings, mostly
   400/500 weights. Removed uppercase tracked labels and padded statistic zeros.
6. **Layout:** existing section order, sidebar and responsive grids retained.
   The main banner now previews actual menu records. It uses the existing food
   response; no additional catalog requests or invented dishes are introduced.
7. **Details:** coherent radii, visible focus, active-page/filter semantics,
   labels, honest empty states and persistent inline form errors. The publication
   dialog locks background interaction. Mobile navigation supports Escape and
   keyboard focus containment.
8. **Visuals:** richness comes from the existing food photos and user images.
   Representatives remain labeled; missing photos retain their placeholders.
   No generated image, generation prompt or new food photograph was needed.
9. **Motion:** removed looping skeleton shimmer, moving cards and broad
   transitions. Feedback uses short named color/opacity transitions; reduced
   motion preferences remain supported.

## Interaction changes

Browser prompts were replaced with native HTML dialogs styled to match BIRGE.
Publishing offers the same three destinations. Skill requests send the same
message payload to the same endpoint. Owner decisions explicitly offer Accept,
Reject and Later; dismissing a dialog does not send a decision. Destructive
actions retain confirmation before the existing deletion request.

Only frontend presentation files changed. API transport helpers were compared
with the original and are unchanged; all 19 literal API call sites retain their
original URLs. Hash comparison verified that backend Python files were unchanged.

## Verification

- Existing pytest suite: **44 passed** (one pre-existing Starlette/httpx
  deprecation warning).
- **23 DOM checks** passed using LinkeDOM with mocked transport and actual menu
  response data: startup, ten food cards, real hero content, navigation,
  publication/upload controls, confirmation/cancellation, skill payload,
  multipart headers and API-backed detail rendering.
- JavaScript syntax checked for all frontend scripts.
- Verified unique HTML IDs, icon references, UTF-8, transport helper equality and
  contrast tokens. Frontend assets, `/docs` and `/openapi.json` returned HTTP 200.
- Browser screenshots and device-layout validation remain unverified: browser
  access was unavailable and the native browser preview window was minimized.
  DOM checks do not validate CSS layout, native focus behavior or image loading.

Open http://127.0.0.1:8000/app/ and refresh without cache after updating.
Manually inspect 390 px, 760 px and desktop layouts in both themes, then exercise
search/filter/sort, posting, image previews, request decisions and cancellation.
Swagger remains at http://127.0.0.1:8000/docs.

## Credits

Design process informed by **unslop by Damir Sokolovsky
([@heydamir](https://x.com/heydamir))**, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Icons: [Lucide](https://lucide.dev/), ISC/MIT; original notices are retained in
`LICENSE.icons.txt`. Food image/font licenses are unchanged.
