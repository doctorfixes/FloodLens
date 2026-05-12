import { ZuploContext, ZuploRequest } from "@zuplo/runtime";

// Fires on every outbound response.
// Bills one unit to Stripe only on successful 200 OK determinations.
// All tier and customer logic belongs here - never in the Edge Function.

export default async function policy(
  response: Response,
  request: ZuploRequest,
  context: ZuploContext
): Promise<Response> {
  if (response.status !== 200) return response;

  const stripeKey = context.environment.STRIPE_SECRET_KEY;
  const customerId = request.user?.data?.stripeCustomerId as string | undefined;

  // Free-tier keys without a Stripe customer ID are not billed.
  // Free-tier enforcement is handled by the rate-limit-free policy.
  if (!customerId || !stripeKey) return response;

  try {
    await fetch("https://api.stripe.com/v1/billing/meter_events", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${stripeKey}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        event_name: "flood_zone_determination",
        "payload[stripe_customer_id]": customerId,
        "payload[value]": "1",
      }),
    });
  } catch (err) {
    // Log billing failures without blocking the response.
    // A failed billing event should not degrade the API caller's experience.
    context.log.error("Stripe meter event failed", { error: err, customerId });
  }

  return response;
}
