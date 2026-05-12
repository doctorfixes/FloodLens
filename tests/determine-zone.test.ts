// determine-zone.test.ts - Edge Function handler unit tests (Deno)

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.208.0/assert/mod.ts";
import {
  type FloodRiskClient,
  type HandlerDependencies,
  handleDetermineZoneRequest,
} from "../supabase/functions/determine-zone/index.ts";
import {
  DISCLAIMER,
  ERROR_CODES,
  errorResponse,
} from "../supabase/functions/determine-zone/errors.ts";

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

function makeRequest(body: unknown, method = "POST"): Request {
  return new Request("https://functions.supabase.co/determine-zone", {
    method,
    headers: { "Content-Type": "application/json" },
    body: method === "GET" || method === "HEAD" || body === undefined
      ? undefined
      : JSON.stringify(body),
  });
}

function mockSupabaseClient(data: unknown, error: unknown = null): FloodRiskClient {
  return {
    rpc: (_functionName: string, _params: { p_lat: number; p_lng: number }) => ({
      returns<T>(): Promise<{ data: T | null; error: unknown }> {
        return Promise.resolve({ data: data as T, error });
      },
    }),
  };
}

function mockDeps(overrides: Partial<HandlerDependencies> = {}): HandlerDependencies {
  return {
    geocodeCensus: (_address: string) =>
      Promise.resolve({ lat: 30.26715, lng: -97.74309 }),
    geocodeGoogle: (_address: string, _apiKey: string) =>
      Promise.resolve({ lat: 30.26715, lng: -97.74309 }),
    getEnv: (name: string) =>
      name === "GOOGLE_MAPS_API_KEY" ? "test-google-key" : undefined,
    createFloodRiskClient: () => mockSupabaseClient([floodRiskFixture]),
    now: () => new Date("2026-05-11T00:00:00.000Z"),
    ...overrides,
  };
}

Deno.test("errorResponse produces correct JSON shape with disclaimer", async () => {
  const response = errorResponse(
    "address is required",
    ERROR_CODES.MISSING_ADDRESS,
    400,
  );
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.error, "address is required");
  assertEquals(body.code, "MISSING_ADDRESS");
  assertEquals(body.disclaimer, DISCLAIMER);
});

Deno.test("returns 405 when method is not POST", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }, "GET"),
    mockDeps(),
  );
  assertEquals(response.status, 405);
  const body = await response.json();
  assertEquals(body.code, "METHOD_NOT_ALLOWED");
  assertExists(body.disclaimer);
});

Deno.test("returns 400 when address is missing", async () => {
  const response = await handleDetermineZoneRequest(makeRequest({}), mockDeps());
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.code, "MISSING_ADDRESS");
  assertExists(body.disclaimer);
});

Deno.test("returns mapped flood-risk response for a valid address", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps(),
  );
  assertEquals(response.status, 200);

  const body = await response.json();
  assertEquals(body.address, "123 Main St");
  assertEquals(body.coordinates, { lat: 30.26715, lng: -97.74309 });
  assertEquals(body.geocode_source, "census");
  assertEquals(body.unmapped, false);
  assertEquals(body.requested_at, "2026-05-11T00:00:00.000Z");
  assertEquals(body.disclaimer, DISCLAIMER);
  assertEquals(body.determination.zone_code, "AE");
  assertEquals(body.determination.risk_level, "HIGH");
  assertEquals(body.determination.disclaimer, DISCLAIMER);
});

Deno.test("returns unmapped true when spatial lookup returns no rows", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "Point Nemo" }),
    mockDeps({ createFloodRiskClient: () => mockSupabaseClient([]) }),
  );

  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.determination, null);
  assertEquals(body.unmapped, true);
  assertExists(body.disclaimer);
});

Deno.test("falls back to Google when Census geocoding fails", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({ geocodeCensus: (_address: string) => Promise.resolve(null) }),
  );

  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.geocode_source, "google");
  assertEquals(body.coordinates, { lat: 30.26715, lng: -97.74309 });
});

Deno.test("returns 502 when Census fails and Google key is not configured", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({
      geocodeCensus: (_address: string) => Promise.resolve(null),
      getEnv: (_name: string) => undefined,
    }),
  );

  assertEquals(response.status, 502);
  const body = await response.json();
  assertEquals(body.code, "GEOCODE_NO_FALLBACK");
  assertExists(body.disclaimer);
});

Deno.test("returns 500 when spatial lookup fails", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({
      createFloodRiskClient: () =>
        mockSupabaseClient(null, { message: "boom" }),
    }),
  );

  assertEquals(response.status, 500);
  const body = await response.json();
  assertEquals(body.code, "DB_ERROR");
  assertExists(body.disclaimer);
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
  assertExists(floodRiskFixture.zone_code);
  assertEquals(floodRiskFixture.risk_level, "HIGH");
  assertExists(floodRiskFixture.dfirm_id);
  assertExists(floodRiskFixture.disclaimer);
});
