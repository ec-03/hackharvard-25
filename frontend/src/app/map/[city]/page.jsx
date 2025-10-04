import CityOverlayClient from "../components/CityOverlayClient";

export default async function CitySidebar({ params }) {
  // Await params (Next.js may provide params as a promise for some dynamic APIs)
  const resolvedParams = await params;
  const city = resolvedParams?.city;// ?? "asklfl";

  return <CityOverlayClient city={city} />;
}
