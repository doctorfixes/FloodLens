// Dependency-free core of the Stripe metered-billing policy.
//
// Kept separate from stripe-metered-billing.ts so the billing decision and the
// Stripe call can be unit-tested without importing "@zuplo/runtime" (a bare
// specifier Deno cannot resolve in tests).

export const STRIPE_METER_EVENTS_URL =
  "https://api.stripe.com/v1/billing/meter_events";
export const METER_EVENT_NAME = "flood_zone_determination";

/**
 * Bill only successful (200) determinations that carry both a Stripe customer
 * id and a configured secret key. Free-tier keys (no customer id) are not
 * billed — quota enforcement lives in the rate-limit policy.
 */
export function shouldBill(
  status: number,
  customerId: unknown,
  stripeKey: unknown,
): boolean {
  return (
    status === 200 &&
    typeof customerId === "string" &&
    customerId.length > 0 &&
    typeof stripeKey === "string" &&
    stripeKey.length > 0
  );
}

/** Build the form-encoded meter-event body for one billable determination. */
export function meterEventBody(customerId: string): URLSearchParams {
  return new URLSearchParams({
    event_name: METER_EVENT_NAME,
    "payload[stripe_customer_id]": customerId,
    "payload[value]": "1",
  });
}

export interface BillMeterEventDeps {
  fetch: typeof fetch;
  logError(message: string, data: Record<string, unknown>): void;
}

/**
 * Send one meter event to Stripe. Never throws: a failed billing call is
 * logged but must not degrade the API caller's response.
 */
export async function billMeterEvent(
  stripeKey: string,
  customerId: string,
  deps: BillMeterEventDeps,
): Promise<void> {
  try {
    const res = await deps.fetch(STRIPE_METER_EVENTS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${stripeKey}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: meterEventBody(customerId),
    });

    if (!res.ok) {
      deps.logError("Stripe meter event failed", {
        customerId,
        status: res.status,
        body: await res.text(),
      });
    }
  } catch (err) {
    deps.logError("Stripe meter event failed", { error: err, customerId });
  }
}
