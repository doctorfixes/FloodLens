// stripe-billing.test.ts - Stripe metered-billing core logic (Deno)
//
// Tests the dependency-free core (no "@zuplo/runtime" import) so the billing
// decision and the Stripe call are covered without a live gateway or Stripe.

import {
  assertEquals,
  assertStringIncludes,
} from "https://deno.land/std@0.208.0/assert/mod.ts";
import {
  billMeterEvent,
  METER_EVENT_NAME,
  meterEventBody,
  shouldBill,
  STRIPE_METER_EVENTS_URL,
} from "../zuplo/policies/stripe-metered-billing-core.ts";

// ── shouldBill ──────────────────────────────────────────────────────────────

Deno.test("shouldBill only bills a 200 with a customer id and a key", () => {
  assertEquals(shouldBill(200, "cus_123", "sk_live_x"), true);
});

Deno.test("shouldBill skips non-200 responses", () => {
  assertEquals(shouldBill(502, "cus_123", "sk_live_x"), false);
  assertEquals(shouldBill(400, "cus_123", "sk_live_x"), false);
});

Deno.test("shouldBill skips free-tier callers (no customer id)", () => {
  assertEquals(shouldBill(200, undefined, "sk_live_x"), false);
  assertEquals(shouldBill(200, "", "sk_live_x"), false);
});

Deno.test("shouldBill skips when no Stripe key is configured", () => {
  assertEquals(shouldBill(200, "cus_123", undefined), false);
  assertEquals(shouldBill(200, "cus_123", ""), false);
});

// ── meterEventBody ────────────────────────────────────────────────────────────

Deno.test("meterEventBody encodes the metered event for one unit", () => {
  const body = meterEventBody("cus_123");
  assertEquals(body.get("event_name"), METER_EVENT_NAME);
  assertEquals(body.get("payload[stripe_customer_id]"), "cus_123");
  assertEquals(body.get("payload[value]"), "1");
});

// ── billMeterEvent ────────────────────────────────────────────────────────────

function recordingLog() {
  const calls: Array<{ message: string; data: Record<string, unknown> }> = [];
  return {
    calls,
    logError(message: string, data: Record<string, unknown>) {
      calls.push({ message, data });
    },
  };
}

Deno.test("billMeterEvent posts the meter event to Stripe on success", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const log = recordingLog();
  const fetchFn = ((input: string | URL | Request, init?: RequestInit) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Promise.resolve(new Response("{}", { status: 200 }));
  }) as typeof fetch;

  await billMeterEvent("sk_live_x", "cus_123", { fetch: fetchFn, logError: log.logError });

  assertEquals(capturedUrl, STRIPE_METER_EVENTS_URL);
  assertEquals(capturedInit?.method, "POST");
  const headers = capturedInit?.headers as Record<string, string>;
  assertEquals(headers.Authorization, "Bearer sk_live_x");
  assertStringIncludes(String(capturedInit?.body), "cus_123");
  assertEquals(log.calls.length, 0);
});

Deno.test("billMeterEvent logs (but does not throw) on a non-OK Stripe response", async () => {
  const log = recordingLog();
  const fetchFn = (() =>
    Promise.resolve(new Response("bad request", { status: 400 }))) as typeof fetch;

  await billMeterEvent("sk_live_x", "cus_123", { fetch: fetchFn, logError: log.logError });

  assertEquals(log.calls.length, 1);
  assertEquals(log.calls[0].data.status, 400);
  assertEquals(log.calls[0].data.customerId, "cus_123");
});

Deno.test("billMeterEvent swallows fetch errors so billing never blocks the caller", async () => {
  const log = recordingLog();
  const fetchFn = (() => Promise.reject(new Error("network down"))) as typeof fetch;

  // Must not throw.
  await billMeterEvent("sk_live_x", "cus_123", { fetch: fetchFn, logError: log.logError });

  assertEquals(log.calls.length, 1);
  assertEquals(log.calls[0].data.customerId, "cus_123");
});
