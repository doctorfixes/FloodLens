// geocoder.test.ts — Census and Google fallback geocoder tests (Deno)

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

const censusFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/census-response.json", import.meta.url)
  )
);

const googleFixture = JSON.parse(
  await Deno.readTextFile(
    new URL("./fixtures/google-response.json", import.meta.url)
  )
);

// ---------------------------------------------------------------------------
// Helpers to mock fetch for each geocoder response
// ---------------------------------------------------------------------------

function mockFetch(body: unknown, ok = true): typeof fetch {
  return (_input: string | URL | Request, _init?: RequestInit) =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status: ok ? 200 : 502,
        headers: { "Content-Type": "application/json" },
      })
    );
}

// ---------------------------------------------------------------------------
// Census geocoder tests
// ---------------------------------------------------------------------------

Deno.test("Census geocoder returns result on success", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch(censusFixture);

  try {
    const { geocodeAddress } = await import(
      "../functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeAddress("123 Main St, Austin TX 78701");

    assertExists(result);
    assertEquals(result.source, "census");
    assertEquals(result.lat, 30.26715);
    assertEquals(result.lon, -97.74309);
    assertEquals(result.formattedAddress, "123 MAIN ST, AUSTIN, TX, 78701");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("Census geocoder returns null when no matches", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({ result: { addressMatches: [] } });

  try {
    const { geocodeAddress } = await import(
      "../functions/determine-zone/geocoder.ts"
    );
    // Mock Deno.env to ensure no Google fallback triggers
    const originalEnvGet = Deno.env.get;
    Deno.env.get = (_key: string) => undefined;

    try {
      const result = await geocodeAddress("999 Nonexistent Blvd, Nowhere USA");
      assertEquals(result, null);
    } finally {
      Deno.env.get = originalEnvGet;
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// ---------------------------------------------------------------------------
// Google fallback tests
// ---------------------------------------------------------------------------

Deno.test("Falls back to Google when Census returns no matches", async () => {
  let callCount = 0;
  const originalFetch = globalThis.fetch;

  // First call → Census empty; second call → Google success
  globalThis.fetch = (
    input: string | URL | Request,
    _init?: RequestInit
  ) => {
    callCount++;
    const url = typeof input === "string" ? input : input.toString();
    const parsedUrl = new URL(url);
    if (parsedUrl.hostname === "geocoding.geo.census.gov") {
      return Promise.resolve(
        new Response(
          JSON.stringify({ result: { addressMatches: [] } }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );
    }
    // Google
    return Promise.resolve(
      new Response(JSON.stringify(googleFixture), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  };

  const originalEnvGet = Deno.env.get;
  Deno.env.get = (key: string) => {
    if (key === "GOOGLE_MAPS_API_KEY") return "test-google-key";
    return undefined;
  };

  try {
    const { geocodeAddress } = await import(
      "../functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeAddress("123 Main St, Austin TX 78701");

    assertExists(result);
    assertEquals(result.source, "google");
    assertEquals(result.lat, 30.26715);
    assertEquals(result.lon, -97.74309);
    assertEquals(callCount, 2);
  } finally {
    globalThis.fetch = originalFetch;
    Deno.env.get = originalEnvGet;
  }
});

Deno.test("Returns null when both Census and Google fail", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({}, false); // Both return 502

  const originalEnvGet = Deno.env.get;
  Deno.env.get = (key: string) => {
    if (key === "GOOGLE_MAPS_API_KEY") return "test-google-key";
    return undefined;
  };

  try {
    const { geocodeAddress } = await import(
      "../functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeAddress("123 Main St, Austin TX 78701");
    assertEquals(result, null);
  } finally {
    globalThis.fetch = originalFetch;
    Deno.env.get = originalEnvGet;
  }
});
