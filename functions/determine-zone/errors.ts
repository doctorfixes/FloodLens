export const ErrorCodes = {
  MISSING_ADDRESS: "MISSING_ADDRESS",
  GEOCODE_FAILED: "GEOCODE_FAILED",
  NO_FLOOD_DATA: "NO_FLOOD_DATA",
  INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];

export function errorResponse(
  status: number,
  code: ErrorCode,
  message: string
): Response {
  return new Response(
    JSON.stringify({ error: { code, message } }),
    {
      status,
      headers: { "Content-Type": "application/json" },
    }
  );
}
