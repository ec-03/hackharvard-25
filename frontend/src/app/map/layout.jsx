"use client";
import dynamic from "next/dynamic";
import { useRouter, usePathname } from "next/navigation";
import { encodeNameForUrl } from "../../lib/nameUtils";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const CityMap = dynamic(() => import("./components/CityMap"), { ssr: false });

export default function MapLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [showInstructions, setShowInstructions] = useState(true);
  const [displayedAnimals, setDisplayedAnimals] = useState([]);

  // Animal images from the animals folder  
  const animalImages = [
    "/images/animals/1.png",
    "/images/animals/2.png",
    "/images/animals/3.png",
    "/images/animals/4.png",
    "/images/animals/5.png",
    "/images/animals/6.png",
    "/images/animals/7.png",
    "/images/animals/8.png",
    "/images/animals/9.png",
  ];

  // overlay is considered open when path is /map/<city>
  const overlayOpen = Boolean(pathname && /^\/map\/[^/]+$/.test(pathname));

  // Initialize 3 random animals along left edge
  useEffect(() => {
    const getRandomAnimals = () => {
      const shuffled = [...animalImages].sort(() => 0.5 - Math.random());
      return shuffled.slice(0, 3).map((image, index) => ({
        id: index,
        image,
        position: 20 + (index * 25) // 20%, 45%, 70% from top
      }));
    };

    setDisplayedAnimals(getRandomAnimals());

    // Refresh animals every 10 seconds
    const interval = setInterval(() => {
      setDisplayedAnimals(getRandomAnimals());
    }, 10000);

    return () => clearInterval(interval);
  }, [animalImages.length]);



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



      {/* Random Animals Along Left Edge */}
      <AnimatePresence>
        {displayedAnimals.map((animal) => (
          <motion.div
            key={animal.id}
            className="absolute left-4 z-5 pointer-events-none"
            style={{ top: `${animal.position}%` }}
            initial={{ opacity: 0, x: -50, scale: 0.8 }}
            animate={{ opacity: 0.4, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -50, scale: 0.8 }}
            transition={{ duration: 1, ease: "easeInOut" }}
          >
            <img 
              src={animal.image} 
              alt="Ocean creature" 
              className="w-16 h-16 object-contain"
            />
          </motion.div>
        ))}
      </AnimatePresence>

      <div className="relative z-10">{children}</div>

      {/* Instructions Popup */}
      <AnimatePresence>
        {showInstructions && !overlayOpen && (
          <motion.div
            className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div
              className="bg-white rounded-lg shadow-2xl max-w-md w-full mx-4 p-6 relative border border-gray-200"
            >
              {/* Close button */}
              <button
                onClick={() => setShowInstructions(false)}
                className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              {/* Content */}
              <div className="pr-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Map Instructions</h2>
                <div className="text-gray-600 space-y-3">
                  <p className="font-semibold">How to use the SimulWave Map:</p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Click on any city marker to view detailed tsunami risk information</li>
                    <li>View historical tsunami data and risk assessments for each location</li>
                    <li><span className="font-bold text-blue-600">Blue</span> markers indicate <b>recent</b> tsunamis.</li>
                    <li><span className="font-bold text-orange-500">Orange</span> markers indicate <b>potential</b> tsunamis.</li>
                  </ul>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
