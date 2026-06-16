# SA Fleet &amp; Logistics by SA Systems (Odoo 18 / 19)

AI-native **3PL, fleet and transport management** for Odoo — for any country,
with **multi-currency as standard** and **region-aware** configuration. One
self-contained app runs the entire chain, from order capture to cash.

## Features

### Transport Operations

- **Transport Orders & Shipments** — Multi-leg, multi-stop orders with a clean
  state machine (Draft → Confirmed → Dispatched → In Transit → POD → Billed →
  Settled).
- **Fleet & Drivers** — Vehicles, trailers, drivers and compliance assets built
  on Odoo core `fleet`.
- **Dispatch & Trips** — Trip planning, manifests and one-click assignment of
  shipments to vehicles and drivers.
- **Route Optimization** — OSRM / heuristic optimization that sequences stops
  and feeds the plan straight to the trip.
- **Live GPS & Geofencing** — High-volume position ingestion with a per-vehicle
  latest snapshot and geofence crossing events.
- **Proof of Delivery** — Mobile-friendly PODs with exceptions, signatures and
  photo capture, plus a JSON driver API for app integration.
- **Warehouse & Cross-Dock** — Docks, bays, waves and pick tasks on top of Odoo
  `stock`.
- **Maintenance** — Preventive-maintenance plans, work orders and defect
  escalation that can ground a vehicle automatically.

### Billing, Settlement & Intelligence

- **Customer Billing** — Rate cards and charges that post directly to Odoo
  `account` invoices.
- **Carrier Settlement** — Pay rules, accruals, settlement runs and driver /
  owner pay statements.
- **Multi-Currency by Design** — Every monetary value carries its own currency
  field and defaults to the company currency.
- **AI** — Predictive ETA & delay risk, price suggestions and shipment scoring
  through a pluggable provider layer (heuristic offline by default; OpenAI /
  Azure OpenAI optional). Includes an AI assistant endpoint. Never hard-fails —
  it degrades gracefully to the built-in heuristic when no API key is set.

### Global, Advanced & Integration

- **Region Profiles** — Bundle market-specific choices in one place: measurement
  system (metric / imperial), distance units, currency, language, timezone,
  compliance regime (HOS / ELD / tachograph), tax regime and provider overrides.
- **Advanced Industry Features** — Hazmat, cold-chain temperature monitoring,
  customs (incoterm / HS code / customs value), CO₂ emissions, reverse
  logistics, detention and insurance on every shipment, plus a public tracking
  portal and dock appointment booking.
- **Integration Hub** — A connector registry for telematics, EDI, e-commerce,
  payment, accounting, customs, maps and visibility providers, with HMAC-signed
  webhooks and EDI document generation (X12 204 / 214 / 210 / 990).

## What's inside

**`sa_fleet_logistics`** is a single installable application. The full platform
ships inside it as internal capability packages (under `parts/`), so there is
nothing else to install and no inter-app dependency to manage:

| Layer | Capabilities |
| --- | --- |
| Core | Base infrastructure, TMS shipment lifecycle |
| Operations | Fleet, dispatch, route optimization, GPS, POD, driver API, warehouse, maintenance |
| Commerce | Customer billing, carrier &amp; driver settlement |
| Intelligence &amp; Global | AI, region profiles, advanced industry features, integration hub |

## Compatibility

- Odoo **18.0** and **19.0** (Community & Enterprise)
- License: **LGPL-3**
- Core dependencies: `base`, `mail`, `fleet`, `stock`, `account`, and the OCA
  `queue_job` for reliable asynchronous processing.

> The modules use modern Odoo view syntax (`<list>`, `<chatter/>`, `invisible`
> domains), which requires **Odoo 18.0 as the minimum** supported series. They
> are verified to install on both Odoo 18 and Odoo 19.

## Installation (Local Testing)

1. Copy the repository folders into your Odoo `addons` directory (or any path
   declared in `--addons-path`).
2. Install from the UI: **Apps → Update Apps List → search "SA Fleet &
   Logistics" → Install**. This single app installs the entire platform.
3. Or from the command line:
   ```bash
   ./odoo-bin -c odoo.conf -d fleet_db -i sa_fleet_logistics --stop-after-init
   ```

A ready-to-run Docker setup is included at the repository root — see the
top-level `README.md` and `start-test.sh`.

## Quick Tour

1. Open the **SA Fleet & Logistics** app from the main menu.
2. Create a **Transport Order**, add stops and confirm it.
3. Let the **AI** suggest a price and ETA, then **Dispatch** to a trip/driver.
4. Track the shipment via **GPS**, capture **Proof of Delivery**, and watch it
   flow into **Billing** and carrier **Settlement** — in any currency.

## License

LGPL-3. See the `LICENSE` file.

— **SA Systems** · info@sasystems.solutions · https://sasystems.solutions
