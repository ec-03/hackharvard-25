"use client";
import dynamic from "next/dynamic";
import { useRouter, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

const CityMap = dynamic(() => import("./components/CityMap"), { ssr: false });
import TsunamiMap from "../components/TsunamiMap";

export default function MapLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();

  // overlay is considered open when path is /map/<city>
  const overlayOpen = Boolean(pathname && /^\/map\/[^/]+$/.test(pathname));

  const handleSelect = (city) => {
    if (!city) return;
    const slug = String(city).toLowerCase();
    // navigate to /map/<city>
    router.push(`/map/${slug}`);
  };

  const url = "http://localhost:5001/api/thinkhazard/tokyo";
  return (
    <div className="relative w-full h-screen">
      {/* center the map container so the map sits in the middle of the screen */}
      <div className="absolute inset-0 z-0 flex items-center justify-center">
        <CityMap onSelect={handleSelect} />
      </div>

      {/* show the small preview only when an overlay is open */}
      <AnimatePresence>
        {overlayOpen && (
          <motion.div
            key="tsunami-preview"
            className="absolute top-[5vh] left-[5vh] z-20 pointer-events-auto"
            initial={{ opacity: 0, x: 150 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, y: 50 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
          >
            <div className="w-[15vw] h-[20vh] rounded-lg shadow overflow-hidden">
              <TsunamiMap url={url} autoFit={false} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10">{children}</div>
    </div>
  );
}
