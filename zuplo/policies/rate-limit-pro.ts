import { RateLimitInboundPolicy } from "@zuplo/runtime";

/**
 * rate-limit-pro.ts
 * Enforces the Pro plan limit: 300 requests per minute.
 */
export default RateLimitInboundPolicy({
  rateLimitBy: "consumer",
  requestsAllowed: 300,
  timeWindowMinutes: 1,
});
