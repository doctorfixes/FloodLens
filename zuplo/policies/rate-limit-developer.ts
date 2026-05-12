import { RateLimitPolicy } from "@zuplo/runtime";

export default new RateLimitPolicy({
  requestsAllowed: 60,
  timeWindowMinutes: 1,
  rateLimitBy: "api-key",
});
