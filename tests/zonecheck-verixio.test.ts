// zonecheck-verixio.test.ts - Verixio neighbourhood bridge internals (Deno)
//
// Exercises lookupNeighborhoodRisk's cache and network paths directly, with an
// in-memory KV, a stubbed fetch, and a fake environment. The handler-level
// wiring is covered separately in zonecheck.test.ts.

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.208.0/assert/mod.ts";
import {
  cacheKey,
  type KvLike,
  lookupNeighborhoodRisk,
  type NeighborhoodDeps,
} from "../supabase/functions/zonecheck/index.ts";

function jsonKey(lat: number, lng: number): string {
  return JSON.stringify(["verixio", cacheKey(lat, lng)]);
}

function makeKv(
  seed: Record<string, unknown> = {},
): KvLike & { store: Map<string, unknown> } {
  const store = new Map<string, unknown>(Object.entries(seed));
  return {
    store,
    get<T = unknown>(key: unknown[]) {
      const k = JSON.stringify(key);
      if (store.has(k)) {
        return Promise.resolve({ value: store.get(k) as T, versionstamp: "v1" });
      }
      return Promise.resolve({ value: null as T, versionstamp: null });
    },
    set(key: unknown[], value: unknown) {
      store.set(JSON.stringify(key), value);
      return Promise.resolve({ ok: true });
    },
  };
}

function okFetch(body: unknown, status = 200): {
  fetch: typeof fetch;
  calls: { n: number };
} {
  const calls = { n: 0 };
  const fetchFn = ((_input: string | URL | Request, _init?: RequestInit) => {
    calls.n++;
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }) as typeof fetch;
  return { fetch: fetchFn, calls };
}

function deps(over: Partial<NeighborhoodDeps>): NeighborhoodDeps {
  return {
    openKv: () => Promise.resolve(makeKv()),
    fetch: okFetch({}).fetch,
    getEnv: (name: string) => (name === "VERIXIO_URL" ? "https://verixio.test/parcel" : undefined),
    ...over,
  };
}

Deno.test("cache hit returns the cached value without calling fetch", async () => {
  const kv = makeKv({ [jsonKey(39.7, -104.9)]: { nts: 42 } });
  const f = okFetch({ nts: 999 });
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(kv), fetch: f.fetch }),
  );
  assertEquals(result, { nts: 42 });
  assertEquals(f.calls.n, 0);
});

Deno.test("cached null (a stored miss) short-circuits without fetching", async () => {
  const kv = makeKv({ [jsonKey(39.7, -104.9)]: null });
  const f = okFetch({ nts: 1 });
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(kv), fetch: f.fetch }),
  );
  assertEquals(result, null);
  assertEquals(f.calls.n, 0);
});

Deno.test("cache miss fetches Verixio and caches the result", async () => {
  const kv = makeKv();
  const f = okFetch({ nts: 72, tcs: 64 });
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(kv), fetch: f.fetch }),
  );
  assertEquals(result, { nts: 72, tcs: 64 });
  assertEquals(f.calls.n, 1);
  // The value must be written back to the cache.
  assertEquals(kv.store.get(jsonKey(39.7, -104.9)), { nts: 72, tcs: 64 });
});

Deno.test("returns null and never fetches when VERIXIO_URL is unset", async () => {
  const f = okFetch({ nts: 1 });
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ getEnv: () => undefined, fetch: f.fetch }),
  );
  assertEquals(result, null);
  assertEquals(f.calls.n, 0);
});

Deno.test("caches a null result when Verixio responds non-OK", async () => {
  const kv = makeKv();
  const f = okFetch({ error: "boom" }, 502);
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(kv), fetch: f.fetch }),
  );
  assertEquals(result, null);
  // A cached miss must be recorded so we don't hammer Verixio.
  assertEquals(kv.store.has(jsonKey(39.7, -104.9)), true);
  assertEquals(kv.store.get(jsonKey(39.7, -104.9)), null);
});

Deno.test("degrades to null when the fetch throws", async () => {
  const kv = makeKv();
  const throwingFetch = (() => Promise.reject(new Error("network down"))) as typeof fetch;
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(kv), fetch: throwingFetch }),
  );
  assertEquals(result, null);
  assertEquals(kv.store.get(jsonKey(39.7, -104.9)), null);
});

Deno.test("works without a cache (KV unavailable) — fetches every time", async () => {
  const f = okFetch({ nts: 5 });
  const result = await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(null), fetch: f.fetch }),
  );
  assertEquals(result, { nts: 5 });
  assertEquals(f.calls.n, 1);
});

Deno.test("passes lat/lon/radius as query params to Verixio", async () => {
  let capturedUrl = "";
  const capturingFetch = ((input: string | URL | Request) => {
    capturedUrl = String(input);
    return Promise.resolve(new Response("{}", { status: 200 }));
  }) as typeof fetch;
  await lookupNeighborhoodRisk(
    39.7,
    -104.9,
    deps({ openKv: () => Promise.resolve(null), fetch: capturingFetch }),
  );
  const url = new URL(capturedUrl);
  assertEquals(url.searchParams.get("lat"), "39.7");
  assertEquals(url.searchParams.get("lon"), "-104.9");
  assertExists(url.searchParams.get("radius_meters"));
});
