# API Reference

## Endpoint

```
GET /v1/determine-zone
```

Returns the FEMA flood zone determination for a US address.

---

## Request

### Query Parameters

| Parameter | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| `address` | string | Yes      | Full US street address (URL-encoded)     |

### Authentication

All requests must include an API key in the `Authorization` header:

```
Authorization: Bearer <YOUR_API_KEY>
```

### Example Request

```bash
curl -G "https://api.floodlens.io/v1/determine-zone" \
  --data-urlencode "address=1600 Pennsylvania Ave NW, Washington DC 20500" \
  -H "Authorization: Bearer fl_live_xxxxxxxxxxxx"
```

---

## Response

### 200 OK

```json
{
  "address": "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC 20500",
  "coordinates": {
    "lat": 38.8977,
    "lon": -77.0366
  },
  "flood_zone": "X",
  "zone_subtype": "AREA OF MINIMAL FLOOD HAZARD",
  "special_flood_hazard_area": false,
  "base_flood_elevation_ft": null,
  "depth_ft": null,
  "effective_date": "2010-09-27",
  "firm_panel": "11001C0071E",
  "geocoder_source": "census"
}
```

### Response Fields

| Field                       | Type            | Description                                               |
|-----------------------------|-----------------|-----------------------------------------------------------|
| `address`                   | string          | Standardized address returned by the geocoder             |
| `coordinates.lat`           | number          | Latitude (WGS84)                                          |
| `coordinates.lon`           | number          | Longitude (WGS84)                                         |
| `flood_zone`                | string          | FEMA flood zone designation (e.g., `AE`, `X`, `VE`)      |
| `zone_subtype`              | string \| null  | Additional zone classification detail                     |
| `special_flood_hazard_area` | boolean         | Whether the location is in a SFHA (mandatory insurance)   |
| `base_flood_elevation_ft`   | number \| null  | Base flood elevation in feet above datum (if applicable)  |
| `depth_ft`                  | number \| null  | Flood depth in feet (Zone AO/AH only)                     |
| `effective_date`            | string \| null  | FIRM panel effective date (`YYYY-MM-DD`)                  |
| `firm_panel`                | string          | FIRM panel identifier                                     |
| `geocoder_source`           | `census`/`google` | Which geocoder was used to resolve the address          |

---

## Error Responses

All errors follow a consistent shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

### Error Codes

| HTTP Status | Code               | Description                                        |
|-------------|--------------------|----------------------------------------------------|
| 400         | `MISSING_ADDRESS`  | The `address` query parameter was not provided     |
| 422         | `GEOCODE_FAILED`   | The address could not be geocoded                  |
| 404         | `NO_FLOOD_DATA`    | No NFHL data available for this location           |
| 500         | `INTERNAL_ERROR`   | Unexpected server-side error                       |

---

## Rate Limits

| Plan        | Limit              |
|-------------|-------------------|
| Free        | 50 requests/month  |
| Developer   | 60 requests/minute |
| Pro         | 300 requests/minute|
