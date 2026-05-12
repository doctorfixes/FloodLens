import { RateLimitInboundPolicy } from "@zuplo/runtime";

/**
 * rate-limit-free.ts
 * Enforces the Free plan limit: 50 requests per rolling 30-day window.
 * Uses Zuplo's built-in rate limiting keyed on the API consumer identifier.
 */
export default RateLimitInboundPolicy({
  rateLimitBy: "consumer",
  requestsAllowed: 50,
  timeWindowMinutes: 60 * 24 * 30, // 43,200 minutes = 30 days
});
