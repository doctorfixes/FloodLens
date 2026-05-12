# Getting Started

## Overview

FloodLens is a serverless API that converts any US address into a structured FEMA flood zone determination. This guide walks you through getting your API key and making your first request.

---

## 1. Sign Up and Get Your API Key

1. Visit [floodlens.io](https://floodlens.io) and create an account.
2. Navigate to **API Keys** in your dashboard.
3. Click **Create Key** and copy your key — it starts with `fl_live_`.

> **Keep your key secret.** Do not commit it to source control.

---

## 2. Make Your First API Call

Replace `<YOUR_API_KEY>` with your actual key and `<ADDRESS>` with any US address:

```bash
curl -G "https://api.floodlens.io/v1/determine-zone" \
  --data-urlencode "address=123 Main St, Austin TX 78701" \
  -H "Authorization: Bearer <YOUR_API_KEY>"
```

### Example Response

```json
{
  "address": "123 MAIN ST, AUSTIN, TX 78701",
  "coordinates": {
    "lat": 30.2672,
    "lon": -97.7431
  },
  "flood_zone": "AE",
  "zone_subtype": null,
  "special_flood_hazard_area": true,
  "base_flood_elevation_ft": 452.0,
  "depth_ft": null,
  "effective_date": "2010-03-01",
  "firm_panel": "48453C0350K",
  "geocoder_source": "census"
}
```

---

## 3. Interpret the Result

The two most important fields are:

- **`flood_zone`** — The FEMA designation. See [Zone Codes](zone-codes.md) for a full reference.
- **`special_flood_hazard_area`** — If `true`, federal mortgage lenders typically require flood insurance.

---

## 4. Handle Errors

Check the HTTP status code. Errors return a JSON body with `error.code` and `error.message`. See [API Reference](api-reference.md#error-codes) for the complete list.

---

## 5. Rate Limits

| Plan      | Limit               |
|-----------|---------------------|
| Free      | 50 requests / month |
| Developer | 60 requests / minute|
| Pro       | 300 requests / minute|

Upgrade your plan in the dashboard at any time.

---

## Next Steps

- Read the full [API Reference](api-reference.md)
- Understand [Data Sources](data-sources.md) and coverage gaps
- Browse [Zone Codes](zone-codes.md) for plain-language explanations
