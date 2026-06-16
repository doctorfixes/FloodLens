import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { geocodeCensus, geocodeGoogle } from "./geocoder.ts";
import {
  DISCLAIMER,
  ERROR_CODES,
  errorResponse,
  successResponse,
} from "./errors.ts";
import type {
  Coordinates,
  DetermineZoneResponse,
  FloodRiskRow,
} from "./types.ts";

export interface RpcResult<T> {
  data: T | null;
  error: unknown;
}

export interface RpcBuilder {
  returns<T>(): Promise<RpcResult<T>>;
}

export interface FloodRiskClient {
  rpc(functionName: string, args: { p_lat: number; p_lng: number }): RpcBuilder;
}

// ── Verixio neighbourhood risk bridge ──────────────────────────────────────
//
// Called as part of the unified ZoneCheck response. If the geocoded address
// falls within Denver, the nearest parcel's NTS/TCS/VGD scores are included.
// For addresses outside Denver this endpoint gracefully returns null.

const VERIXIO_TIMEOUT_MS = 8000;
const VERIXIO_SEARCH_RADIUS_M = 500;

async function lookupNeighborhoodRisk(
  lat: number,
  lng: number,
): Promise<Record<string, unknown> | null> {
  const verixioUrl = Deno.env.get("VERIXIO_URL");
  if (!verixioUrl) return null; // Verixio not configured — silently skip

  // Verixio /parcel/by-coordinates is a GET endpoint with query parameters
  const url = new URL(verixioUrl);
  url.searchParams.set("lat", String(lat));
  url.searchParams.set("lon", String(lng));
  url.searchParams.set("radius_meters", String(VERIXIO_SEARCH_RADIUS_M));

  try {
    const res = await fetch(url.toString(), {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(VERIXIO_TIMEOUT_MS),
    });
    if (!res.ok) return null;
    return await res.json() as Record<string, unknown>;
  } catch {
    return null; // Verixio unavailable — degrade gracefully
  }
}

// ── Handler dependencies ──────────────────────────────────────────────────

export interface HandlerDependencies {
  geocodeCensus(address: string): Promise<Coordinates | null>;
  geocodeGoogle(address: string, apiKey: string): Promise<Coordinates | null>;
  getEnv(name: string): string | undefined;
  createFloodRiskClient(): FloodRiskClient;
  lookupNeighborhoodRisk(lat: number, lng: number): Promise<Record<string, unknown> | null>;
  now(): Date;
}

function defaultDependencies(): HandlerDependencies {
  return {
    geocodeCensus,
    geocodeGoogle,
    getEnv(name: string): string | undefined {
      return Deno.env.get(name);
    },
    createFloodRiskClient(): FloodRiskClient {
      return createClient(
        Deno.env.get("SUPABASE_URL") ?? "",
        Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
      ) as unknown as FloodRiskClient;
    },
    lookupNeighborhoodRisk,
    now(): Date {
      return new Date();
    },
  };
}

function readAddress(body: unknown): string | null {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return null;
  }

  const address = (body as { address?: unknown }).address;
  return typeof address === "string" ? address.trim() || null : null;
}

export async function handleDetermineZoneRequest(
  req: Request,
  deps: HandlerDependencies = defaultDependencies(),
): Promise<Response> {
  if (req.method !== "POST") {
    return errorResponse(
      "Method not allowed",
      ERROR_CODES.METHOD_NOT_ALLOWED,
      405,
    );
  }

  let requestBody: unknown;
  try {
    requestBody = await req.json();
  } catch {
    return errorResponse("Invalid JSON body", ERROR_CODES.INVALID_BODY, 400);
  }

  const address = readAddress(requestBody);
  if (!address) {
    return errorResponse(
      "address is required",
      ERROR_CODES.MISSING_ADDRESS,
      400,
    );
  }

  let coords = await deps.geocodeCensus(address);
  let geocodeSource: "census" | "google" = "census";

  if (!coords) {
    const googleKey = deps.getEnv("GOOGLE_MAPS_API_KEY");

    if (!googleKey) {
      return errorResponse(
        "Geocoding failed and no fallback provider is configured",
        ERROR_CODES.GEOCODE_NO_FALLBACK,
        502,
      );
    }

    coords = await deps.geocodeGoogle(address, googleKey);
    geocodeSource = "google";
  }

  if (!coords) {
    return errorResponse(
      "Address could not be geocoded by any available provider",
      ERROR_CODES.GEOCODE_FAILURE,
      422,
    );
  }

  let lookupResult: RpcResult<FloodRiskRow[]>;
  try {
    const supabase = deps.createFloodRiskClient();
    lookupResult = await supabase
      .rpc("fn_get_flood_risk", { p_lat: coords.lat, p_lng: coords.lng })
      .returns<FloodRiskRow[]>();
  } catch {
    return errorResponse("Spatial query failed", ERROR_CODES.DB_ERROR, 500);
  }

  const { data, error } = lookupResult;

  if (error) {
    return errorResponse("Spatial query failed", ERROR_CODES.DB_ERROR, 500);
  }

  const determination = data && data.length > 0 ? data[0] : null;

  // ── Neighborhood risk lookup (Verixio bridge) ─────────────────────────
  let neighborhoodRisk: Record<string, unknown> | null = null;
  if (determination !== null || true) {
    // Attempt neighborhood lookup regardless of flood zone result
    neighborhoodRisk = await deps.lookupNeighborhoodRisk(coords.lat, coords.lng);
  }

  const response: DetermineZoneResponse = {
    address,
    coordinates: coords,
    geocode_source: geocodeSource,
    determination,
    neighborhood: neighborhoodRisk,
    unmapped: determination === null,
    requested_at: deps.now().toISOString(),
    disclaimer: DISCLAIMER,
  };

  return successResponse(response);
}

if (import.meta.main) {
  serve((req: Request): Promise<Response> => handleDetermineZoneRequest(req));
}
