// geocoder.test.ts - Census and Google geocoder tests (Deno)

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

function mockFetch(body: unknown, ok = true): typeof fetch {
  return (_input: string | URL | Request, _init?: RequestInit) =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status: ok ? 200 : 502,
        headers: { "Content-Type": "application/json" },
      })
    );
}

Deno.test("Census geocoder returns result on success", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch(censusFixture);

  try {
    const { geocodeCensus } = await import(
      "../supabase/functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeCensus("123 Main St, Austin TX 78701");

    assertExists(result);
    assertEquals(result.lat, 30.26715);
    assertEquals(result.lng, -97.74309);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("Census geocoder returns null when no matches", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({ result: { addressMatches: [] } });

  try {
    const { geocodeCensus } = await import(
      "../supabase/functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeCensus("999 Nonexistent Blvd, Nowhere USA");
    assertEquals(result, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("Google geocoder returns result on success", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch(googleFixture);

  try {
    const { geocodeGoogle } = await import(
      "../supabase/functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeGoogle(
      "123 Main St, Austin TX 78701",
      "test-google-key",
    );

    assertExists(result);
    assertEquals(result.lat, 30.26715);
    assertEquals(result.lng, -97.74309);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("Google geocoder returns null on non-OK status", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({}, false);

  try {
    const { geocodeGoogle } = await import(
      "../supabase/functions/determine-zone/geocoder.ts"
    );
    const result = await geocodeGoogle(
      "123 Main St, Austin TX 78701",
      "test-google-key",
    );
    assertEquals(result, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
