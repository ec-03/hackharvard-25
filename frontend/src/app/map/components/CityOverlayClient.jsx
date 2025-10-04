"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";

export default function CityOverlayClient({ city }) {
  const router = useRouter();
  const [open, setOpen] = useState(true);

  const display = city && city.length ? city[0].toUpperCase() + city.slice(1) : "Error";

  if (!open) return null;

  return (
    <motion.div 
      data-overlay="city"
      className="absolute right-[2vw] top-[50vh] z-20 w-[78vw] h-[90vh] p-4 bg-white/90 rounded-lg shadow-lg -translate-y-1/2"
      initial={{ opacity: 0, x: 150 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, y: 50 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
    >
      <div className="flex items-start justify-between">
        <h2 className="text-xl font-semibold">{display}</h2>
        <div className="flex gap-2">
          <button
            className="text-sm text-gray-500 hover:text-gray-700"
            onClick={() => {
              // navigate back to the map index so the overlay is removed
              router.push("/map");
            }}
            aria-label="Close overlay"
          >
            ✕
          </button>
        </div>
      </div>
      <p className="mt-2 text-sm">Population: ~10.5M (example)</p>
      <div className="mt-4 flex gap-2">
        <button
          className="text-sm text-blue-600 underline"
          onClick={() => router.push(`/map/${String(city).toLowerCase()}/more`)}
        >
          More
        </button>
      </div>
    </motion.div>
  );
}
