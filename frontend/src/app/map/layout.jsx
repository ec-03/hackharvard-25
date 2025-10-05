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
    <motion.div 
      className="relative w-full h-screen bg-gradient-to-br from-blue-100 via-blue-200 to-sky-200"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1, ease: "easeInOut" }}
    >
      {/* center the map container so the map sits in the middle of the screen */}
      <motion.div 
        className="absolute inset-0 z-0 flex items-center justify-center"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.2, delay: 0.3, ease: "easeOut" }}
      >
        <CityMap onSelect={handleSelect} />
      </motion.div>

      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
