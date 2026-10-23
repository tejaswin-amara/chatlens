# ChatLens v2.0 Design System
Based on `open-design`, `motion-anything`, and `ui-ux-pro-max` principles.

## 1. Intent
ChatLens should feel like a premium, privacy-focused dashboard. It is an analytical tool, but it shouldn't feel like a sterile spreadsheet. It should feel responsive, empathetic, and "alive" through subtle motion.

## 2. Colors
- **Background**: Deep Space (`#0a0a0f`). Avoid pure black.
- **Surface/Card**: Glassmorphic dark layers (`rgba(255, 255, 255, 0.03)` with `backdrop-filter: blur(16px)`).
- **Primary Accent**: Bio-Teal (`#00d4aa`). Used for primary actions, active states, and AI highlights.
- **Secondary Accent**: Deep Ocean (`#00b4d8`). Used for gradients and secondary visual weight.
- **Text**: `zinc-100` (`#f4f4f5`) for primary, `zinc-400` (`#a1a1aa`) for secondary.

## 3. Typography
- **Font Family**: Inter (sans-serif) for ultimate readability.
- **Weights**: Regular (400) for body, Medium (500) for controls/labels, SemiBold (600) for headings.
- **Scale**: Fluid scaling where possible. Base size 15px.

## 4. Spacing
- Use a 4px/8px baseline grid.
- **Gaps**: Use `gap-4` (16px) or `gap-6` (24px) for distinct visual blocks.
- **Padding**: Generous padding inside glass cards (`p-6`).

## 5. Motion (motion-anything)
- **Constraint**: Tasteful, hardware-accelerated only (`transform`, `opacity`). Avoid animating `height` or `margin` if possible.
- **Avoid When**: Do not trigger entrance animations on every single scroll. Only trigger once per view.
- **Recipe: Spring Scale**: Buttons scale to `0.98` on click (active state).
- **Recipe: Fade-up Stagger**: List items enter with a slight `translate-y-4` and fade in over `300ms`, staggered by `50ms`.
- **Accessibility**: All animations MUST respect `@media (prefers-reduced-motion: reduce)`.

## 6. Shapes & Borders
- **Radius**: Soft radii. `rounded-xl` (12px) for cards, `rounded-lg` (8px) for inputs/buttons.
- **Borders**: Hairline borders `border-white/10` to define glass edges.

## 7. Human-Centric Principles
- **Empty States**: Never show a blank screen. Always guide the user to the next action with an icon and friendly text.
- **Loading**: Use shimmering skeleton screens that match the final content structure, not just generic spinners.
- **Anti-AI Slop**: Do not render massive, unformatted walls of text from AI. Parse AI output into structured cards (e.g., "TL;DR", "Sentiment", "Key Topics").

## 8. Icons
- Lucide React icons. Stroke width: `1.5` or `2`.

## 9. Accessibility
- Minimum contrast ratio of 4.5:1 for text.
- Clear `:focus-visible` rings (`ring-2 ring-teal-500 ring-offset-2 ring-offset-background`).
