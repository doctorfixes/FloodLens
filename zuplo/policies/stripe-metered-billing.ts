import { ZuploContext, ZuploRequest } from "@zuplo/runtime";

/**
 * stripe-metered-billing.ts
 * Outbound policy: records a metered billing event in Stripe for every
 * successful API response (2xx). Skips billing for error responses.
 */

const STRIPE_API_URL = "https://api.stripe.com/v1";

export default async function policy(
  response: Response,
  request: ZuploRequest,
  context: ZuploContext
): Promise<Response> {
  // Only bill on successful responses
  if (!response.ok) {
    return response;
  }

  const stripeApiKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeApiKey) {
    context.log.warn("STRIPE_SECRET_KEY not set; skipping metered billing");
    return response;
  }

  // Retrieve the Stripe subscription item ID attached to the consumer
  const subscriptionItemId = request.user?.data?.stripeSubscriptionItemId as
    | string
    | undefined;

  if (!subscriptionItemId) {
    context.log.warn("No stripeSubscriptionItemId on consumer; skipping billing");
    return response;
  }

  try {
    const body = new URLSearchParams({
      quantity: "1",
      action: "increment",
      timestamp: String(Math.floor(Date.now() / 1000)),
    });

    const billingRes = await fetch(
      `${STRIPE_API_URL}/subscription_items/${subscriptionItemId}/usage_records`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${stripeApiKey}`,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      }
    );

    if (!billingRes.ok) {
      const err = await billingRes.text();
      context.log.error("Stripe billing error", { status: billingRes.status, err });
    }
  } catch (err) {
    context.log.error("Stripe billing exception", { err });
  }

  return response;
}
