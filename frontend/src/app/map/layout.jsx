"use client";
import dynamic from "next/dynamic";
import { useRouter, usePathname } from "next/navigation";
import { encodeNameForUrl } from "../../lib/nameUtils";
import { motion, AnimatePresence } from "framer-motion";

const CityMap = dynamic(() => import("./components/CityMap"), { ssr: false });

export default function MapLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();

  // overlay is considered open when path is /map/<city>
  const overlayOpen = Boolean(pathname && /^\/map\/[^/]+$/.test(pathname));

  const handleSelect = (city) => {
    if (!city) return;
    // encode so spaces/commas are safe in the URL
    const encoded = encodeNameForUrl(city);
    router.push(`/map/${encoded}`);
  };

  const url = "http://localhost:5001/api/thinkhazard/tokyo";
  return (
    <div className="relative w-full h-screen">
      {/* center the map container so the map sits in the middle of the screen */}
      <div className="absolute inset-0 z-0 flex items-center justify-center">
        <CityMap onSelect={handleSelect} />
      </div>

      <div className="relative z-10">{children}</div>
    </div>
  );
}
