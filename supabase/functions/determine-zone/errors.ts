import type { ErrorResponse } from "./types.ts";

export const DISCLAIMER =
  "This result is derived from FEMA National Flood Hazard Layer (NFHL) data and is provided for informational purposes only. It does not constitute an official flood zone determination, a Letter of Map Amendment (LOMA), or legal advice. Official determinations must be obtained through a licensed flood determination company or FEMA directly. Data currency depends on NFHL update cadence and may not reflect the most recent map revisions.";

export const ERROR_CODES = {
  METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
  INVALID_BODY: "INVALID_BODY",
  MISSING_ADDRESS: "MISSING_ADDRESS",
  GEOCODE_FAILURE: "GEOCODE_FAILURE",
  GEOCODE_NO_FALLBACK: "GEOCODE_NO_FALLBACK",
  DB_ERROR: "DB_ERROR",
} as const;

export type ErrorCode = typeof ERROR_CODES[keyof typeof ERROR_CODES];

export function errorResponse(
  message: string,
  code: ErrorCode,
  status: number,
): Response {
  const body: ErrorResponse = { error: message, code, disclaimer: DISCLAIMER };
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function successResponse(body: unknown): Response {
  const responseBody =
    typeof body === "object" && body !== null && !Array.isArray(body)
      ? {
        ...body,
        disclaimer: (body as { disclaimer?: unknown }).disclaimer ?? DISCLAIMER,
      }
      : { data: body, disclaimer: DISCLAIMER };

  return new Response(JSON.stringify(responseBody), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
