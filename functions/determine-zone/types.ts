export interface GeocodeResult {
  lat: number;
  lon: number;
  formattedAddress: string;
  source: "census" | "google";
}

export interface FloodRiskRow {
  fld_zone: string;
  zone_subty: string | null;
  sfha_tf: boolean;
  static_bfe: number | null;
  depth: number | null;
  eff_date: string | null;
  dfirm_id: string;
}

export interface FloodRiskResponse {
  address: string;
  coordinates: {
    lat: number;
    lon: number;
  };
  flood_zone: string;
  zone_subtype: string | null;
  special_flood_hazard_area: boolean;
  base_flood_elevation_ft: number | null;
  depth_ft: number | null;
  effective_date: string | null;
  firm_panel: string;
  geocoder_source: "census" | "google";
}
