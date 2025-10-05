"use client";
import { useState, useRef, useEffect } from "react";
import { motion, useAnimation } from "framer-motion";
import { useParams } from "next/navigation";
import { cities } from "./data";
import { normalizeName } from "../../../lib/nameUtils";

export default function CityMap({ onSelect }) {
  // use relative coordinates (0..1) so markers keep correct positions when the map resizes
  const params = useParams();
  // decode params.city will be the encoded route segment; compare normalized forms
  let selected = null;
  if (params?.city) {
    try {
      selected = normalizeName(decodeURIComponent(String(params.city)));
    } catch (e) {
      selected = normalizeName(String(params.city));
    }
  }

  // animation controls for the map wrapper (zoom + pan)
  const controls = useAnimation();
  const [origin, setOrigin] = useState({ x: "50%", y: "50%" });
  const [animating, setAnimating] = useState(false);
  const wrapperRef = useRef(null);
  const [persistX, setPersistX] = useState(0); // pixel translate to persist while overlay is open
  const [persistY, setPersistY] = useState(0); // pixel translate vertically (for potential vertical pans)
  const width = typeof window !== "undefined" ? window.innerWidth : 0;
  const height = typeof window !== "undefined" ? window.innerHeight : 0;

  const handleMarkerClick = async (city) => {
    if (animating) return; // ignore repeated clicks while animating
    setAnimating(true);

    // set transform origin to the clicked point so scale centers on it
    const originX = `${city.x * 100}%`;
    const originY = `${city.y * 100}%`;
    setOrigin({ x: originX, y: originY });
    
    try {
      // zoom in around the city
      await controls.start({ scale: 5, transition: { duration: 0.6, ease: "easeInOut" } });
      // compute pixel translate values
      const pxX = width * (0.1 - city.x);
      const pxY = height * (0.5 - city.y);
      // animate to the pixel translate (x/y accept numbers)
      await controls.start({ x: pxX, y: pxY, transition: { duration: 0.6, ease: "easeInOut" } });

      // persist this pixel pan while overlay is open
      setPersistX(pxX);
      setPersistY(pxY);
    } catch (e) {
      // ignore animation interruption
    }

    // after animation, call the parent's handler (navigation)
    if (onSelect) onSelect(city.name);
    // do not immediately reset; keep the pan while overlay exists
    // clear animating flag so further interactions are possible
    setAnimating(false);
  };

  // when overlay disappears, reset persisted x and origin
  useEffect(() => {
    const observer = new MutationObserver(async () => {
      const overlay = document.querySelector('[data-overlay="city"]');
      if (!overlay) {
        // reset transforms
        await controls.start({ scale: 1, x: 0, y: 0, transition: { duration: 0.6, ease: "easeInOut" } }).catch(() => {});
        setOrigin({ x: "50%", y: "50%" });
        setPersistX(0);
        setPersistY(0);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [controls]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden">
      {/* motion wrapper: apply zoom & pan here so both background and markers are transformed */}
      <motion.div
        ref={wrapperRef}
        animate={controls}
        initial={{ scale: 1, x: 0, y: 0 }}
        style={{ width: "100%", height: "100%", transformOrigin: `${origin.x} ${origin.y}`, x: persistX, y: persistY }}
      >
        {/* background world svg: contain so full SVG height is visible */}
        <img
          src="/world.svg"
          alt="world map"
          className="absolute inset-0 w-full h-full object-contain"
          style={{ objectPosition: "50% 50%" }}
        />

        {cities.map((city) => {
          const isSelected = selected === normalizeName(city.name);
          const baseColor = city.color === "blue" ? "#3b82f6" : "#f59e0b"; // blue or yellow
          return (
            // wrapper positions the marker using percentages and centers it with a static transform
            <div
              key={city.name}
              className="absolute"
              style={{
                top: `${city.y * 100}%`,
                left: `${city.x * 100}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <motion.div
                className="rounded-full cursor-pointer"
                style={{ width: 12, height: 12 }}
                animate={{
                  scale: isSelected ? 1.8 : 1,
                  backgroundColor: isSelected ? "#ef4444" : baseColor,
                }}
                transition={{ type: "spring", stiffness: 800, damping: 20 }}
                whileHover={{ scale: isSelected ? 2 : 1.3 }}
                onClick={() => handleMarkerClick(city)}
                role="button"
                aria-label={`Select ${city.name}`}
              />
            </div>
          );
        })}
      </motion.div>
    </div>
  );
}
