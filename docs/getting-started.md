# Getting Started

FloodLens converts a US address into a structured FEMA flood zone determination.

## 1. Get an API Key

Create an API key in your FloodLens dashboard. API keys are managed by Zuplo and
carry tier metadata for rate limiting and Stripe metering.

## 2. Make Your First Request

```bash
curl -X POST "https://YOUR_ZUPLO_GATEWAY/v1/determine-zone" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, Miami, FL 33101"}'
```

## 3. Read the Result

The main response fields are:

- `coordinates`: WGS 84 latitude and longitude used for the lookup.
- `geocode_source`: `census` or `google`.
- `determination.zone_code`: FEMA zone code such as `AE`, `VE`, `X`, or `D`.
- `determination.risk_level`: `HIGH`, `MODERATE`, `MINIMAL`, `UNDETERMINED`, or `UNKNOWN`.
- `unmapped`: `true` when no ingested polygon covers the coordinate.
- `disclaimer`: present on every success and error response.

## 4. Handle Errors

Errors use this shape:

```json
{
  "error": "address is required",
  "code": "MISSING_ADDRESS",
  "disclaimer": "This result is derived from FEMA National Flood Hazard Layer (NFHL) data..."
}
```

See [API Reference](api-reference.md) for all error codes and response fields.
