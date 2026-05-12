import { GeocodeResult } from "./types.ts";

const CENSUS_GEOCODER_URL =
  "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";

const GOOGLE_GEOCODER_URL =
  "https://maps.googleapis.com/maps/api/geocode/json";

/**
 * Geocode an address using the US Census Geocoder.
 * Returns null on failure so the caller can fall back to Google.
 */
async function geocodeCensus(address: string): Promise<GeocodeResult | null> {
  const params = new URLSearchParams({
    address,
    benchmark: "Public_AR_Current",
    format: "json",
  });

  const res = await fetch(`${CENSUS_GEOCODER_URL}?${params}`);
  if (!res.ok) return null;

  const data = await res.json();
  const matches: unknown[] =
    data?.result?.addressMatches ?? [];

  if (matches.length === 0) return null;

  const match = matches[0] as {
    matchedAddress: string;
    coordinates: { x: number; y: number };
  };

  return {
    lat: match.coordinates.y,
    lon: match.coordinates.x,
    formattedAddress: match.matchedAddress,
    source: "census",
  };
}

/**
 * Geocode an address using the Google Maps Geocoding API.
 * Requires GOOGLE_MAPS_API_KEY environment variable.
 */
async function geocodeGoogle(address: string): Promise<GeocodeResult | null> {
  const apiKey = Deno.env.get("GOOGLE_MAPS_API_KEY");
  if (!apiKey) return null;

  const params = new URLSearchParams({ address, key: apiKey });
  const res = await fetch(`${GOOGLE_GEOCODER_URL}?${params}`);
  if (!res.ok) return null;

  const data = await res.json();
  if (data.status !== "OK" || !data.results?.length) return null;

  const result = data.results[0];
  const loc = result.geometry.location;

  return {
    lat: loc.lat,
    lon: loc.lng,
    formattedAddress: result.formatted_address,
    source: "google",
  };
}

/**
 * Geocode an address, trying Census first and falling back to Google.
 * Returns null if both sources fail.
 */
export async function geocodeAddress(
  address: string
): Promise<GeocodeResult | null> {
  const censusResult = await geocodeCensus(address);
  if (censusResult) return censusResult;

  return geocodeGoogle(address);
}
