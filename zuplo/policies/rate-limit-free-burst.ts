import { RateLimitPolicy } from "@zuplo/runtime";

export default new RateLimitPolicy({
  requestsAllowed: 10,
  timeWindowMinutes: 1,
  rateLimitBy: "api-key",
});
