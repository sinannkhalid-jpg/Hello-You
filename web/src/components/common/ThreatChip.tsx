/**
 * ThreatChip — kept for back-compat. Internally, this is now just
 * a thin wrapper around the new RiskChip so the color/label logic
 * stays in one place.
 *
 *   risk_level  →  band name
 *   "Low Risk"   (green)
 *   "Guarded"    (lime)
 *   "Moderate"   (amber)
 *   "High Risk"  (orange)
 *   "Critical"   (red)
 *
 * New code should use `RiskChip` directly.
 */
import { RiskChip } from "./RiskChip";

export { RiskChip as ThreatChip };
