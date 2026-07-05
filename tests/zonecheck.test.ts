// zonecheck.test.ts - Unified ZoneCheck Edge Function handler unit tests (Deno)
//
// zonecheck is the production function (determine-zone is legacy). These tests
// mirror the determine-zone handler suite and add coverage for the pieces that
// only exist here: the Verixio neighbourhood bridge and the response's
// `neighborhood` field.

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.208.0/assert/mod.ts";
import {
  cacheKey,
  type FloodRiskClient,
  handleDetermineZoneRequest,
  type HandlerDependencies,
} from "../supabase/functions/zonecheck/index.ts";
import {
  DISCLAIMER,
  ERROR_CODES,
  errorResponse,
  successResponse,
} from "../supabase/functions/zonecheck/errors.ts";

const floodRiskFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/flood-risk-row.json", import.meta.url),
  ),
);

const verixioFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/verixio-response.json", import.meta.url),
  ),
);

function makeRequest(body: unknown, method = "POST"): Request {
  return new Request("https://functions.supabase.co/zonecheck", {
    method,
    headers: { "Content-Type": "application/json" },
    body: method === "GET" || method === "HEAD" || body === undefined
      ? undefined
      : typeof body === "string"
      ? body
      : JSON.stringify(body),
  });
}

function mockSupabaseClient(
  data: unknown,
  error: unknown = null,
): FloodRiskClient {
  return {
    rpc: (
      _functionName: string,
      _params: { p_lat: number; p_lng: number },
    ) => ({
      returns<T>(): Promise<{ data: T | null; error: unknown }> {
        return Promise.resolve({ data: data as T, error });
      },
    }),
  };
}

function mockDeps(
  overrides: Partial<HandlerDependencies> = {},
): HandlerDependencies {
  return {
    geocodeCensus: (_address: string) =>
      Promise.resolve({ lat: 39.74, lng: -104.99 }),
    geocodeGoogle: (_address: string, _apiKey: string) =>
      Promise.resolve({ lat: 39.74, lng: -104.99 }),
    getEnv: (name: string) =>
      name === "GOOGLE_MAPS_API_KEY" ? "test-google-key" : undefined,
    createFloodRiskClient: () => mockSupabaseClient([floodRiskFixture]),
    lookupNeighborhoodRisk: (_lat: number, _lng: number) =>
      Promise.resolve(verixioFixture),
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

Deno.test("successResponse injects a disclaimer when the body omits one", async () => {
  const response = successResponse({ hello: "world" });
  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.hello, "world");
  assertEquals(body.disclaimer, DISCLAIMER);
});

Deno.test("successResponse preserves a disclaimer already present on the body", async () => {
  const response = successResponse({ disclaimer: "custom" });
  const body = await response.json();
  assertEquals(body.disclaimer, "custom");
});

Deno.test("successResponse wraps non-object bodies under a data key", async () => {
  const response = successResponse([1, 2, 3]);
  const body = await response.json();
  assertEquals(body.data, [1, 2, 3]);
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

Deno.test("returns 400 when the JSON body is malformed", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest("{not valid json"),
    mockDeps(),
  );
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.code, "INVALID_BODY");
  assertExists(body.disclaimer);
});

Deno.test("returns 400 when address is missing", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({}),
    mockDeps(),
  );
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.code, "MISSING_ADDRESS");
  assertExists(body.disclaimer);
});

Deno.test("returns 400 when address is a whitespace-only string", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "   " }),
    mockDeps(),
  );
  assertEquals(response.status, 400);
  const body = await response.json();
  assertEquals(body.code, "MISSING_ADDRESS");
});

Deno.test("returns mapped flood-risk + neighborhood for a valid address", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps(),
  );
  assertEquals(response.status, 200);

  const body = await response.json();
  assertEquals(body.address, "123 Main St");
  assertEquals(body.coordinates, { lat: 39.74, lng: -104.99 });
  assertEquals(body.geocode_source, "census");
  assertEquals(body.unmapped, false);
  assertEquals(body.requested_at, "2026-05-11T00:00:00.000Z");
  assertEquals(body.disclaimer, DISCLAIMER);
  assertEquals(body.determination.zone_code, "AE");
  assertEquals(body.determination.risk_level, "HIGH");
  assertEquals(body.neighborhood, verixioFixture);
});

Deno.test("neighborhood is null when the Verixio bridge returns nothing", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({
      lookupNeighborhoodRisk: (_lat: number, _lng: number) =>
        Promise.resolve(null),
    }),
  );
  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.neighborhood, null);
  assertEquals(body.determination.zone_code, "AE");
});

Deno.test("neighborhood lookup still runs when the address is unmapped", async () => {
  let calledWith: [number, number] | null = null;
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "Denver but unmapped" }),
    mockDeps({
      createFloodRiskClient: () => mockSupabaseClient([]),
      lookupNeighborhoodRisk: (lat: number, lng: number) => {
        calledWith = [lat, lng];
        return Promise.resolve(verixioFixture);
      },
    }),
  );
  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.determination, null);
  assertEquals(body.unmapped, true);
  assertEquals(body.neighborhood, verixioFixture);
  // Regression guard: neighbourhood lookup must fire even with no flood match.
  assertEquals(calledWith, [39.74, -104.99]);
});

Deno.test("falls back to Google when Census geocoding fails", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({ geocodeCensus: (_address: string) => Promise.resolve(null) }),
  );

  assertEquals(response.status, 200);
  const body = await response.json();
  assertEquals(body.geocode_source, "google");
  assertEquals(body.coordinates, { lat: 39.74, lng: -104.99 });
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

Deno.test("returns 422 when both Census and Google geocoders fail", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "somewhere unresolvable" }),
    mockDeps({
      geocodeCensus: (_address: string) => Promise.resolve(null),
      geocodeGoogle: (_address: string, _key: string) => Promise.resolve(null),
    }),
  );

  assertEquals(response.status, 422);
  const body = await response.json();
  assertEquals(body.code, "GEOCODE_FAILURE");
  assertExists(body.disclaimer);
});

Deno.test("returns 500 when spatial lookup returns an error", async () => {
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

Deno.test("returns 500 with disclaimer when database client creation throws", async () => {
  const response = await handleDetermineZoneRequest(
    makeRequest({ address: "123 Main St" }),
    mockDeps({
      createFloodRiskClient: () => {
        throw new Error("missing Supabase configuration");
      },
    }),
  );

  assertEquals(response.status, 500);
  const body = await response.json();
  assertEquals(body.code, "DB_ERROR");
  assertEquals(body.disclaimer, DISCLAIMER);
});

Deno.test("cacheKey rounds coordinates to 4 decimals so nearby points collide", () => {
  // ~11m precision: two points a few metres apart share a cache entry.
  assertEquals(cacheKey(39.7391234, -104.9905678), "39.7391,-104.9906");
  assertEquals(cacheKey(39.73912, -104.99051), cacheKey(39.73914, -104.99052));
});
