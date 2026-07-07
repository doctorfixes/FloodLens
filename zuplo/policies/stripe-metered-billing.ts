import type { ZuploContext, ZuploRequest } from "@zuplo/runtime";
import { billMeterEvent, shouldBill } from "./stripe-metered-billing-core.ts";

// Fires on every outbound response.
// Bills one unit to Stripe only on successful 200 OK determinations.
// All tier and customer logic belongs here - never in the Edge Function.

export default async function policy(
  response: Response,
  request: ZuploRequest,
  context: ZuploContext,
): Promise<Response> {
  const stripeKey = context.environment.STRIPE_SECRET_KEY;
  const customerId = request.user?.data?.stripeCustomerId;

  // Free-tier keys without a Stripe customer ID are not billed.
  // Free-tier enforcement is handled by the rate-limit-free policy.
  if (!shouldBill(response.status, customerId, stripeKey)) {
    return response;
  }

  await billMeterEvent(stripeKey as string, customerId as string, {
    fetch: globalThis.fetch.bind(globalThis),
    logError: (message, data) => context.log.error(message, data),
  });

  return response;
}
