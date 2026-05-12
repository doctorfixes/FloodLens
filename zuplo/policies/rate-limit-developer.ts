import { RateLimitInboundPolicy } from "@zuplo/runtime";

/**
 * rate-limit-developer.ts
 * Enforces the Developer plan limit: 60 requests per minute.
 */
export default RateLimitInboundPolicy({
  rateLimitBy: "consumer",
  requestsAllowed: 60,
  timeWindowMinutes: 1,
});
