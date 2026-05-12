import { RateLimitPolicy } from "@zuplo/runtime";

export default new RateLimitPolicy({
  requestsAllowed: 300,
  timeWindowMinutes: 1,
  rateLimitBy: "api-key",
});
