# API Reference

## Endpoint

```http
POST /v1/determine-zone
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

Returns a FEMA flood zone determination for a US street address.

## Request Body

```json
{
  "address": "1600 Pennsylvania Avenue NW, Washington, DC 20500"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `address` | string | Yes | Full US address to geocode and evaluate. |

## 200 Response

```json
{
  "address": "1600 Pennsylvania Avenue NW, Washington, DC 20500",
  "coordinates": { "lat": 38.8977, "lng": -77.0366 },
  "geocode_source": "census",
  "determination": {
    "zone_code": "X",
    "zone_label": "Minimal Flood Hazard Area",
    "risk_level": "MINIMAL",
    "insurance_note": "Minimal Risk. Outside the 500-Year floodplain. Flood insurance is optional.",
    "bfe": null,
    "depth": null,
    "panel_number": null,
    "dfirm_id": "11001C",
    "eff_date": "2010-09-27",
    "disclaimer": "This result is derived from FEMA National Flood Hazard Layer (NFHL) data..."
  },
  "unmapped": false,
  "requested_at": "2026-05-11T00:00:00.000Z",
  "disclaimer": "This result is derived from FEMA National Flood Hazard Layer (NFHL) data..."
}
```

If the coordinate is outside all ingested polygons, `determination` is `null`
and `unmapped` is `true`. The top-level `disclaimer` is still present.

`determination.panel_number` can be `null` when the current ingestion source
does not include a panel identifier on the matched flood hazard polygon.

## Error Response

Every error response includes a disclaimer.

```json
{
  "error": "address is required",
  "code": "MISSING_ADDRESS",
  "disclaimer": "This result is derived from FEMA National Flood Hazard Layer (NFHL) data..."
}
```

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_BODY` | Request body is not valid JSON. |
| 400 | `MISSING_ADDRESS` | `address` is absent or blank. |
| 405 | `METHOD_NOT_ALLOWED` | Only `POST` is supported. |
| 422 | `GEOCODE_FAILURE` | Census and Google could not geocode the address. |
| 502 | `GEOCODE_NO_FALLBACK` | Census failed and no Google fallback key is configured. |
| 500 | `DB_ERROR` | PostGIS flood-risk lookup failed. |

## Rate Limits and Billing

Rate limits, API keys, tiers, and Stripe metering are enforced in Zuplo. The
Supabase Edge Function has no billing or tier awareness. Free-tier keys should
apply both the monthly quota policy and the one-minute burst policy.

| Tier | Included | Overage | Rate Limit |
| --- | --- | --- | --- |
| Free | 50 req/month | None - hard block | 10 req/min |
| Developer | None | $0.50 / request | 60 req/min |
| Pro | None | $1.50 / request | 300 req/min |
