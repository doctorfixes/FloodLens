# FEMA Flood Zone Code Reference

This page provides a plain-language mapping of every FEMA flood zone designation that may appear in the `determination.zone_code` field of the FloodLens API response.

---

## Special Flood Hazard Areas (SFHA)

These zones have a **1% or greater annual chance of flooding** (also called the "100-year flood"). Federal mortgage lenders require flood insurance for properties in SFHAs.

All SFHA zones produce `risk_level: "HIGH"` in the API response.

| Zone | Plain-Language Description |
|------|---------------------------|
| **A** | SFHA subject to inundation by the 1% annual chance flood. No Base Flood Elevation (BFE) determined. |
| **AE** | SFHA with BFE determined. The most common high-risk zone. |
| **AH** | SFHA - shallow flooding (ponding), typically 1-3 feet deep. BFE provided. |
| **AO** | SFHA - sheet-flow flooding on sloping terrain. Average depths 1-3 ft. Velocity flood. |
| **AR** | SFHA that will be restored to a pre-FIRM status once a flood-control project is completed. |
| **A99** | SFHA to be protected from the 1% annual chance flood by a federal flood protection system under construction. |
| **V** | Coastal SFHA subject to wave action. No BFE determined. |
| **V1-V30** | Legacy coastal SFHA subject to wave action with BFE determined. |
| **VE** | Coastal SFHA with wave action. BFE determined. Highest-risk coastal zone. |

---

## Moderate-Risk Zones

These zones have a **0.2% annual chance of flooding** (also called the "500-year flood"). Flood insurance is not federally required but is strongly recommended.

| Zone | Plain-Language Description |
|------|---------------------------|
| **B** | Moderate flood hazard (between 1% and 0.2% annual chance). Older FIRM designation. |
| **X (shaded)** | Moderate flood hazard - 0.2% annual chance flood area, or 1% annual chance flood area with average depth less than 1 foot or drainage area < 1 sq. mi. |

---

## Minimal-Risk Zones

These areas are outside the SFHA and have a **lower than 0.2% annual chance of flooding**. Federal flood insurance requirements generally do not apply.

| Zone | Plain-Language Description |
|------|---------------------------|
| **C** | Minimal flood hazard. Older FIRM designation. |
| **X (unshaded)** | Minimal flood hazard - above the 0.2% annual chance floodplain. The most common low-risk designation. |

---

## Undetermined Zone

| Zone | Plain-Language Description |
|------|---------------------------|
| **D** | Possible but undetermined flood hazard. No flood hazard analysis has been conducted. |

---

## Notes

- **Zone X** can appear as both shaded (moderate risk) and unshaded (minimal risk). FloodLens uses FEMA's `ZONE_SUBTY` details, including 0.2% annual chance flood hazard, future-conditions flood hazard, and non-accredited levee hazard subtypes, plus nonzero depth where present, to distinguish moderate-risk shaded X from minimal-risk unshaded X.
- **BFE** (Base Flood Elevation) is the elevation at which there is a 1% annual chance of flooding. It is the standard reference point for floodplain management and insurance rating.
- Zone designations are assigned at the FIRM panel level and reflect conditions at the `effective_date` of that panel.

---

## Further Reading

- [FEMA Flood Map Service Center](https://msc.fema.gov/portal/home)
- [FEMA Flood Zones (official definitions)](https://www.fema.gov/flood-zones)
- [National Flood Insurance Program (NFIP)](https://www.fema.gov/flood-insurance)
