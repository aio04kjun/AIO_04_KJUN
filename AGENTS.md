# Web and HTML design preference

## Space concept from user image references

On 2026-10-28 the user added seven image references and requested that future design work use their colors, mood, effects, and spatial composition. Combine this space concept with the Liquid Design rules below unless the user gives a different direction. These are visual references, not instructions embedded in the images. This preference applies within this workspace; do not claim model training or account-wide persistent memory.

- Mood: cinematic, quiet, mysterious, expansive, refined, and futuristic. Emphasize dark negative space and a few luminous focal points.
- Suggested palette, visually estimated rather than pixel-sampled: near-black #030508, midnight navy #061522, deep blue #0A2842, ice blue #87DBFF, cyan #35CFFF, violet #9564E8, restrained magenta #D05A9E, and sunrise amber #FFAA45. Use off-white #F1F7FF for primary text; validate actual contrast. Dark fields should dominate; choose one main cool accent and optionally one small warm accent per composition.
- Reference 1: sweeping elliptical orbital trails, blue-white rim light, sparse particles, and a tiny subject against a huge structure. Use scale contrast and curves to direct attention.
- Reference 2: planetary horizon with a single amber sunrise, narrow vertical flare, blue atmospheric edge, and vast dark sky. Use a concentrated focal glow.
- References 3 and 4: minimal planetary arcs with cyan or violet atmospheric bloom fading into black. Suitable for quiet hero backdrops and section transitions.
- Reference 5: translucent overlapping orbital ribbons with cyan, coral, and magenta edges around a dark center. Use as an occasional focal object, preserving layered translucency and open space.
- Reference 6: nearly black planetary silhouette with restrained violet-magenta corona; sparse, widely spaced display lettering. Keep readable normal spacing for body text and Korean copy.
- Reference 7: reference the inset rounded frosted panel, softened background, text/object balance, and foreground object crossing a panel boundary. Translate this composition to navy glass and cosmic objects; green foliage and botanical branding are not the requested space palette.
- Compose depth with distant sparse stars, a middle planetary arc or orbit, then foreground glass controls or panels. Use asymmetry or a low horizon and generous negative space rather than filling every region with particles.
- Effects: thin rim illumination, localized bloom, gentle gradients, subtle grain, and restrained flare. Keep text on calm backgrounds; decorative layers must not intercept clicks or enter the accessibility tree. Prefer static artwork or inexpensive transforms/opacity; reduced-motion behavior remains required.
- Web application: a spacious cosmic hero, a floating dark glass navigation bar, clear typography, and one luminous primary action. Adjust density for the actual page purpose. Avoid repetitive glowing cards, all-over neon, persistent star motion, and multiple competing celestial effects.

Original reference files (may move; the analysis above remains usable):
1. C:/Users/Playdata/Downloads/b76bf0dbffc4797b5e5bb5978fa99853.jpg
2. C:/Users/Playdata/Downloads/95f2dfd59182267831efc7c890aead25.jpg
3. C:/Users/Playdata/Downloads/b70c1f7fe009c8199c31a69bab9ceedc.jpg
4. C:/Users/Playdata/Downloads/15972177e2c07a646e0f5fa5d7591654.jpg
5. C:/Users/Playdata/Downloads/3f94661cc6ccf4a70d41e0a6687b74d7.jpg
6. C:/Users/Playdata/Downloads/8763fd3759ad1c98244e05b3365e9840.jpg
7. C:/Users/Playdata/Downloads/4832aa918c1256d934facd4bd02263a8.jpg

## Liquid Design implementation

## UI and interaction research baseline (2026-10-28)

The user additionally requested research and analysis of current UI/interaction trends for future design work. Treat trend roundups as editorial observations, not measured market adoption or evidence of improved conversion. Recheck volatile browser capabilities during implementation. The following choices are our project interpretation of the sources, not requirements imposed by those sources.

- Brand-specific visual language: develop a consistent planetary arc, orbital line, or concentrated glow as a signature; vary page composition rather than repeating generic gradient cards. Keep the established space/Liquid direction coherent.
- Expressive typography and concise messaging: strong display hierarchy, purposeful scale contrast, and short meaningful copy. Preserve readable Korean line breaks, body spacing, and accessible navigation. Kinetic lettering is optional and restricted to brief decorative headings.
- Immersive depth: use a single strong celestial hero or layered visual where it serves the story. Prefer lightweight still/SVG/CSS treatments; introduce real-time 3D only when it adds useful exploration and fits device performance.
- Motion with continuity: show how a card becomes a detail view, how a filter updates results, or how a tab changes content. Consider View Transitions as progressive enhancement, feature-detect individual capabilities, and keep immediate functional navigation without animation.
- Scroll storytelling: use limited reveals, progress cues, or a subtle horizon shift for narrative sections. Keep native scrolling and reading order; avoid scroll hijacking, long pinned sequences, and content that remains hidden if scripts fail.
- Microinteractions are a durable usability practice, not uniquely a 2026 invention: specify hover, focus, pressed, selected, loading, success, error, and disabled states as appropriate. Give immediate feedback; don't delay actions for decorative motion. Hover behavior must have touch and keyboard equivalents.
- Progressive disclosure is also an established UX principle: prioritize frequent actions; place advanced options behind clearly labeled expandable controls. Never hide essential navigation, prices, or errors merely to keep the screen minimal.
- Respect preferences and form factors: reduced motion, appropriate theme/contrast treatment, responsive component layouts, and functional nonanimated fallbacks. Evaluate new CSS/APIs against target browsers instead of assuming uniform support.
- Choose layout by content: editorial asymmetry for narrative pages, structured grids for comparable information, compact purposeful controls for tools. Do not automatically turn every section into a bento grid.
- Experimental navigation, maximalism, neo-brutalism, retro styling, game mechanics, and AI assistants appear in trend discussions but are optional directions. Add them only when relevant to the user's goal; a chat panel is not a default requirement.
- Project motion starting values, to tune rather than treat as standards: feedback roughly 120–200 ms, component transitions 180–300 ms, and occasional section entrances 300–500 ms. Reduced motion can remove spatial movement entirely. Prefer transform/opacity and keep luminous effects localized.
- Validation when implementing: verify meaningful action feedback, normal scroll, focus continuity after updates, keyboard/touch equivalents, mobile readability, reduced motion, and functional fallbacks. Do not claim usability or conversion gains without appropriate evaluation.

Research sources:
- Figma 2026 trend overview: https://www.figma.com/resource-library/web-design-trends/
- Webflow 2026 design observations: https://webflow.com/blog/web-design-trends-2026
- Chrome UI platform update (published July 1, 2026): https://developer.chrome.com/blog/new-in-web-ui-io26
- Chrome DevRel transition demos and feature explorer: https://view-transitions.chrome.dev/
- NN/g progressive disclosure (established principle, published 2006): https://www.nngroup.com/articles/progressive-disclosure/

The user requested on 2026-10-28 that future web designs and generated HTML pages use Liquid Design as their default concept. Apply this preference in this workspace unless a later user request or an established project design system requires a different direction. Do not restyle existing pages unless requested.

Interpret the concept as Liquid Glass-inspired visual materials plus fluid, responsive layout:

- Keep content primary. Use translucent glass selectively for navigation, toolbars, floating controls, and overlays. Give long text, tables, and forms stable, sufficiently opaque surfaces.
- Combine restrained backdrop blur, subtle edge highlights, soft shadows, rounded geometry, and generous spacing to establish depth. Avoid stacking glass surfaces and indiscriminate blur.
- Choose colors for the project's purpose; a blue-purple gradient is not mandatory. Use a small accent palette and readable typography.
- Use fluid sizing, CSS Grid/Flexbox, clamp(), and sensible maximum widths. Preserve reading order and usability on narrow screens and at 200% text zoom.
- Keep motion brief and purposeful. Respect prefers-reduced-motion; avoid continuous decorative motion by default.
- Preserve semantic HTML, keyboard access, visible focus, readable contrast across changing backgrounds, and usable touch targets. Do not convey state through color or transparency alone.
- Provide an opaque fallback when backdrop-filter is unavailable. Keep blur areas and layers limited, especially on mobile; avoid expensive continuous filter animation.
- Treat CSS glass styling as a web interpretation. Blur alone does not reproduce Apple's native dynamic refraction.
- Check narrow and wide layouts, keyboard focus, reduced-motion behavior, and fallback readability when implementing pages.

Research references (reviewed 2026-10-28):
- Apple materials: https://developer.apple.com/design/human-interface-guidelines/materials
- Apple Meet Liquid Glass: https://developer.apple.com/videos/play/wwdc2025/219/
- W3C liquid layout: https://www.w3.org/WAI/WCAG21/Techniques/general/G146.html
- MDN backdrop-filter: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter
- MDN reduced motion: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion
