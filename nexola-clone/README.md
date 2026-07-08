# MERIDIAN® — editorial studio landing (original recreation)

An **original** single-page + case-study site built to study and reproduce the *interaction and
layout language* of a high-end editorial studio landing (dark/light editorial, oversized
neo-grotesque type, cinematic hero, scroll reveals). See [`ANALYSIS.md`](./ANALYSIS.md) for the
full design breakdown that informed it.

> This is not a copy of any template. All copy, imagery, code and the brand (**MERIDIAN®**) are new.
> Fonts use a license-free system neo-grotesque stack; imagery uses CSS duotone placeholders you can
> swap for real photography.

## Run
No build step — it's static. Open `index.html`, or serve locally:
```bash
python3 -m http.server 8080   # then visit http://localhost:8080
```

## Structure
```
nexola-clone/
├─ index.html            Home (hero → studio → work → stats → quote → FAQ → contact → footer)
├─ projects/velora.html  Case-study detail template
├─ assets/
│  ├─ css/styles.css     Design tokens + all components
│  ├─ js/main.js         All interactions (no dependencies)
│  └─ img/               Image slot (replace placeholders here)
├─ ANALYSIS.md           Expert design/UX analysis
└─ README.md
```

## Interactions (`assets/js/main.js`)
- Sticky header (hide on scroll-down, solid after hero) · full-screen menu overlay with staggered links
- Scroll reveal (IntersectionObserver) · hero brightness/scale reveal on load
- FAQ accordion · magnetic buttons · project hover image-reveal · custom cursor
- All motion respects `prefers-reduced-motion`; pointer effects gated to fine pointers

## Replace placeholders with real images
Swap any `.ph` element for an `<img>`:
```html
<!-- from -->
<div class="ph warm"></div>
<!-- to -->
<img src="assets/img/velora-hero.jpg" alt="Velora campaign" style="width:100%;height:100%;object-fit:cover">
```

## Customize the brand
- Colors/type live in `:root` at the top of `styles.css` (`--bg`, `--ink`, `--dark`, `--disp`, …).
- Rename `MERIDIAN` in the two HTML files and the footer wordmark.
