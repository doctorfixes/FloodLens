import { RateLimitPolicy } from "@zuplo/runtime";

export default new RateLimitPolicy({
  requestsAllowed: 50,
  timeWindowMinutes: 43200, // 30 days
  rateLimitBy: "api-key",
});
