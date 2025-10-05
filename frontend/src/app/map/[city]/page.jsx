import CityOverlayClient from "../components/CityOverlayClient";
import { decodeNameFromUrl } from "../../../lib/nameUtils";

export default async function CitySidebar({ params }) {
  // Await params (Next.js may provide params as a promise for some dynamic APIs)
  const resolvedParams = await params;
  const raw = resolvedParams?.city;
  const city = raw ? decodeNameFromUrl(raw) : raw;

  return <CityOverlayClient city={city} />;
}
