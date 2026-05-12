import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { geocodeAddress } from "./geocoder.ts";
import { ErrorCodes, errorResponse } from "./errors.ts";
import { FloodRiskResponse, FloodRiskRow } from "./types.ts";

Deno.serve(async (req: Request): Promise<Response> => {
  // Only accept GET requests
  if (req.method !== "GET") {
    return errorResponse(405, ErrorCodes.INTERNAL_ERROR, "Method not allowed");
  }

  const url = new URL(req.url);
  const address = url.searchParams.get("address")?.trim();

  if (!address) {
    return errorResponse(
      400,
      ErrorCodes.MISSING_ADDRESS,
      "Query parameter 'address' is required"
    );
  }

  // Geocode the address
  const geocoded = await geocodeAddress(address);
  if (!geocoded) {
    return errorResponse(
      422,
      ErrorCodes.GEOCODE_FAILED,
      "Could not geocode the provided address"
    );
  }

  // Query the database for flood risk
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
  );

  const { data, error } = await supabase.rpc("fn_get_flood_risk", {
    p_lat: geocoded.lat,
    p_lon: geocoded.lon,
  });

  if (error) {
    console.error("Database error:", error);
    return errorResponse(
      500,
      ErrorCodes.INTERNAL_ERROR,
      "An internal error occurred"
    );
  }

  if (!data || (Array.isArray(data) && data.length === 0)) {
    return errorResponse(
      404,
      ErrorCodes.NO_FLOOD_DATA,
      "No flood zone data available for this location"
    );
  }

  const row: FloodRiskRow = Array.isArray(data) ? data[0] : data;

  const response: FloodRiskResponse = {
    address: geocoded.formattedAddress,
    coordinates: {
      lat: geocoded.lat,
      lon: geocoded.lon,
    },
    flood_zone: row.fld_zone,
    zone_subtype: row.zone_subty,
    special_flood_hazard_area: row.sfha_tf,
    base_flood_elevation_ft: row.static_bfe,
    depth_ft: row.depth,
    effective_date: row.eff_date,
    firm_panel: row.dfirm_id,
    geocoder_source: geocoded.source,
  };

  return new Response(JSON.stringify(response), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});
