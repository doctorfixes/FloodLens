import type { Coordinates } from "./types.ts";

const CENSUS_TIMEOUT_MS = 5000;
const GOOGLE_TIMEOUT_MS = 5000;

/**
 * Geocodes an address using the US Census Geocoder.
 * Free. No API key required.
 * Known limitations: rural addresses, multi-unit buildings, PO boxes.
 * Returns null on any failure - caller decides whether to fall back.
 */
export async function geocodeCensus(
  address: string,
): Promise<Coordinates | null> {
  const url = new URL(
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
  );
  url.searchParams.set("address", address);
  url.searchParams.set("benchmark", "2020");
  url.searchParams.set("format", "json");

  try {
    const res = await fetch(url.toString(), {
      signal: AbortSignal.timeout(CENSUS_TIMEOUT_MS),
    });

    if (!res.ok) return null;

    const data = await res.json();
    const matches = data?.result?.addressMatches;

    if (!Array.isArray(matches) || matches.length === 0) return null;

    const coords = matches[0]?.coordinates;
    if (typeof coords?.x !== "number" || typeof coords?.y !== "number") {
      return null;
    }

    // Census returns x = longitude, y = latitude.
    return { lat: coords.y, lng: coords.x };
  } catch {
    return null;
  }
}

/**
 * Geocodes an address using the Google Maps Geocoding API.
 * Requires GOOGLE_MAPS_API_KEY environment variable.
 * Only called when Census geocoder fails or returns no matches.
 * Returns null on any failure.
 */
export async function geocodeGoogle(
  address: string,
  apiKey: string,
): Promise<Coordinates | null> {
  const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
  url.searchParams.set("address", address);
  url.searchParams.set("key", apiKey);

  try {
    const res = await fetch(url.toString(), {
      signal: AbortSignal.timeout(GOOGLE_TIMEOUT_MS),
    });

    if (!res.ok) return null;

    const data = await res.json();
    if (
      data.status !== "OK" || !Array.isArray(data.results) ||
      data.results.length === 0
    ) {
      return null;
    }

    const loc = data.results[0]?.geometry?.location;
    if (typeof loc?.lat !== "number" || typeof loc?.lng !== "number") {
      return null;
    }

    return { lat: loc.lat, lng: loc.lng };
  } catch {
    return null;
  }
}
