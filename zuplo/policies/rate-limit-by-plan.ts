import {
  ZuploContext,
  ZuploRequest,
  HttpProblems,
} from "@zuplo/runtime";

/**
 * rate-limit-by-plan.ts
 * Routes incoming requests to the correct rate-limit policy based on the
 * API consumer's plan tier (free | developer | pro).
 *
 * Plan tier is read from the consumer metadata field `plan`.
 * Falls back to the free-tier limits when no plan is set.
 */

const PLAN_LIMITS: Record<string, { requestsAllowed: number; windowMinutes: number }> = {
  free: { requestsAllowed: 50, windowMinutes: 60 * 24 * 30 }, // 30-day rolling
  developer: { requestsAllowed: 60, windowMinutes: 1 },
  pro: { requestsAllowed: 300, windowMinutes: 1 },
};

export default async function policy(
  request: ZuploRequest,
  context: ZuploContext
): Promise<ZuploRequest | Response> {
  const plan =
    ((request.user?.data as Record<string, unknown> | undefined)?.plan as string | undefined) ??
    "free";
  const limits = PLAN_LIMITS[plan] ?? PLAN_LIMITS["free"];

  const { requestsAllowed, windowMinutes } = limits;
  const consumerKey = request.user?.sub ?? request.headers.get("x-forwarded-for") ?? "anonymous";
  const windowKey = `rl:${consumerKey}:${plan}`;

  // Use Zuplo's built-in KV-backed counter
  const counter = await context.kvStore?.increment(windowKey, {
    expirationTtl: windowMinutes * 60,
  });

  if (counter !== undefined && counter > requestsAllowed) {
    context.log.warn("Rate limit exceeded", { consumerKey, plan, counter });
    return HttpProblems.tooManyRequests(request, context, {
      detail: `Rate limit exceeded for plan '${plan}'. Allowed: ${requestsAllowed} requests per ${windowMinutes} minutes.`,
    });
  }

  return request;
}
