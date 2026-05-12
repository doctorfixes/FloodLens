export interface Coordinates {
  lat: number;
  lng: number;
}

export interface FloodRiskRow {
  zone_code: string;
  zone_label: string;
  risk_level: "HIGH" | "MODERATE" | "MINIMAL" | "UNDETERMINED" | "UNKNOWN";
  insurance_note: string;
  bfe: number | null;
  depth: number | null;
  panel_number: string | null;
  dfirm_id: string;
  eff_date: string | null;
  disclaimer: string;
}

export interface DetermineZoneResponse {
  address: string;
  coordinates: Coordinates;
  geocode_source: "census" | "google";
  determination: FloodRiskRow | null;
  unmapped: boolean;
  requested_at: string;
  disclaimer: string;
}

export interface ErrorResponse {
  error: string;
  code: string;
  disclaimer: string;
}
