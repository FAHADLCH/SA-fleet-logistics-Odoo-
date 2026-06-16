# ODOTRANS — Branding Assets (SA Systems)

Drop your high-resolution SA Systems / ODOTRANS logo files here.

## Required files (you add these)

| File | Where | Size | Used for |
|------|-------|------|----------|
| `icon.png` | `odotrans_tms/static/description/icon.png` | 140×140 (square, transparent PNG) | The app tile shown in **Apps** and the Odoo App Store. Odoo auto-detects this path — no manifest change needed. |
| `banner.png` | `odotrans_tms/static/description/banner.png` | ~1200×600 | Hero banner referenced by the `images` key in the manifest. |

## Per-module icons (optional but recommended)

Each module shows its own tile in **Apps**. To brand them all, add an
`icon.png` to every module's `static/description/` folder:

```
odotrans_base/static/description/icon.png
odotrans_fleet/static/description/icon.png
odotrans_dispatch/static/description/icon.png
odotrans_route/static/description/icon.png
odotrans_gps/static/description/icon.png
odotrans_pod/static/description/icon.png
odotrans_warehouse/static/description/icon.png
odotrans_billing/static/description/icon.png
odotrans_settlement/static/description/icon.png
odotrans_maintenance/static/description/icon.png
odotrans_driver_api/static/description/icon.png
```

If a module has no `icon.png`, Odoo falls back to a default tile — the app
still installs and works.

## Brand palette used in `index.html`

These are intentional, professional defaults (adjust to match the exact SA
Systems brand guide if it differs):

- Deep navy `#0B1F3A` — primary
- Cyan-teal `#16C2C2` — accent
- Ink `#0F172A` — body text

Update the `:root`-style values at the top of `index.html` if your brand
guide specifies different hex codes.
