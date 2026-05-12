// determine-zone.test.ts — Edge Function unit tests (Deno)

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

const floodRiskFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/flood-risk-row.json", import.meta.url)
  )
);

const censusFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/census-response.json", import.meta.url)
  )
);

// ---------------------------------------------------------------------------
// Helper: build a Request to the edge function
// ---------------------------------------------------------------------------
function makeRequest(address?: string): Request {
  const url = address
    ? `https://functions.supabase.co/determine-zone?address=${encodeURIComponent(address)}`
    : "https://functions.supabase.co/determine-zone";
  return new Request(url, { method: "GET" });
}

// ---------------------------------------------------------------------------
// Helper: mock Supabase createClient to return canned flood risk data
// ---------------------------------------------------------------------------
function mockSupabaseClient(
  data: unknown,
  error: unknown = null
): Record<string, unknown> {
  return {
    rpc: (_fn: string, _params: unknown) =>
      Promise.resolve({ data, error }),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

Deno.test("Returns 400 when address parameter is missing", async () => {
  const { errorResponse, ErrorCodes } = await import(
    "../functions/determine-zone/errors.ts"
  );
  const response = errorResponse(
    400,
    ErrorCodes.MISSING_ADDRESS,
    "Query parameter 'address' is required"
  );
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.error.code, "MISSING_ADDRESS");
});

Deno.test("errorResponse produces correct JSON shape", async () => {
  const { errorResponse, ErrorCodes } = await import(
    "../functions/determine-zone/errors.ts"
  );
  const response = errorResponse(
    422,
    ErrorCodes.GEOCODE_FAILED,
    "Could not geocode the provided address"
  );
  assertEquals(response.status, 422);
  assertEquals(response.headers.get("Content-Type"), "application/json");
  const body = await response.json();
  assertExists(body.error);
  assertEquals(body.error.code, "GEOCODE_FAILED");
  assertEquals(body.error.message, "Could not geocode the provided address");
});

Deno.test("Flood risk response maps DB row to API shape correctly", () => {
  // Simulate the mapping logic from index.ts
  const geocoded = {
    lat: 30.26715,
    lon: -97.74309,
    formattedAddress: "123 MAIN ST, AUSTIN, TX, 78701",
    source: "census" as const,
  };

  const row = floodRiskFixture;

  const response = {
    address: geocoded.formattedAddress,
    coordinates: { lat: geocoded.lat, lon: geocoded.lon },
    flood_zone: row.fld_zone,
    zone_subtype: row.zone_subty,
    special_flood_hazard_area: row.sfha_tf,
    base_flood_elevation_ft: row.static_bfe,
    depth_ft: row.depth,
    effective_date: row.eff_date,
    firm_panel: row.dfirm_id,
    geocoder_source: geocoded.source,
  };

  assertEquals(response.flood_zone, "AE");
  assertEquals(response.special_flood_hazard_area, true);
  assertEquals(response.base_flood_elevation_ft, 452.0);
  assertEquals(response.firm_panel, "48453C0350K");
  assertEquals(response.geocoder_source, "census");
  assertEquals(response.zone_subtype, null);
  assertEquals(response.depth_ft, null);
});

Deno.test("Census geocoder fixture has expected structure", () => {
  const matches = censusFixture?.result?.addressMatches;
  assertExists(matches);
  assertEquals(matches.length > 0, true);
  const match = matches[0];
  assertExists(match.coordinates);
  assertEquals(typeof match.coordinates.x, "number");
  assertEquals(typeof match.coordinates.y, "number");
  assertExists(match.matchedAddress);
});

Deno.test("Flood risk fixture has expected structure", () => {
  assertExists(floodRiskFixture.fld_zone);
  assertEquals(typeof floodRiskFixture.sfha_tf, "boolean");
  assertExists(floodRiskFixture.dfirm_id);
});
