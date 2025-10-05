"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { cities } from "./data";
import { normalizeName } from "../../../lib/nameUtils";

export default function CityOverlayClient({ city }) {
  const router = useRouter();
  const [open, setOpen] = useState(true);
  const [pageIndex, setPageIndex] = useState(0);

  // simple paginated content per city; expand or replace with fetched content later
  const displayName = city && city.length ? city : "ERROR";

  // find matching city entry from data.js using normalized names
  const rawCityProp = city || "";
  const normalizedRaw = normalizeName(rawCityProp);

  // Try exact normalized match first
  let matchedCity = cities.find((c) => normalizeName(c.name) === normalizedRaw);

  // Fallback: token-based contains matching (all tokens in raw must appear in candidate)
  if (!matchedCity && normalizedRaw) {
    const rawTokens = normalizedRaw.split(" ").filter(Boolean);
    // Only attempt fallback if we have more than one token (e.g. "crescent city")
    // or if the single token is reasonably long (>= 3 chars) to avoid accidental matches.
    if (rawTokens.length > 1 || (rawTokens.length === 1 && rawTokens[0].length >= 3)) {
      matchedCity = cities.find((c) => {
        const nc = normalizeName(c.name);
        return rawTokens.every((t) => nc.includes(t));
      });
    }
  }

  // (no debug logging in production)
  const firstPageText = matchedCity && matchedCity.description && matchedCity.description.trim().length
    ? matchedCity.description
    : `About ${displayName}: This is the first page of information. It contains an intro paragraph about the city and its context.`;

  const secondPageText = `Explore how ${displayName} might be affected by a tsunami using the following model: `;
  const thirdPageText = (matchedCity && matchedCity.preparedness && matchedCity.preparedness.trim().length)
    ? matchedCity.preparedness
    : `Preparedness: Practical tips for ${displayName} residents and visitors including evacuation routes, safe zones, and contact points.`;

  const pages = [
    firstPageText,
    secondPageText,
    thirdPageText,
  ];

  // slideshow state for the first page
  const [images, setImages] = useState([]);
  const [slideIndex, setSlideIndex] = useState(0);
  const slideRef = useRef(null);

  // generate a small set of Unsplash source URLs for the matched city (fallback to displayName)
  useEffect(() => {
    // Prefer local images placed under public/images/<imageFolder>/ when provided in data.js
    if (matchedCity && matchedCity.imageFolder && Array.isArray(matchedCity.images) && matchedCity.images.length > 0) {
      const imgs = matchedCity.images.map((fn) => `/images/${matchedCity.imageFolder}/${fn}`);
      setImages(imgs);
      setSlideIndex(0);
      return;
    }

    // Fallback: generate Unsplash sources based on city/display name
    const q = matchedCity?.name || displayName || "landscape";
    const imgs = Array.from({ length: 4 }).map((_, i) => `https://source.unsplash.com/800x450/?${encodeURIComponent(q)}&sig=${i}`);
    setImages(imgs);
    setSlideIndex(0);
  }, [matchedCity, displayName]);

  // autoplay when on the first page
  useEffect(() => {
    // only run when viewing page 0 and we have images
    if (pageIndex !== 0 || !images || images.length === 0) return;
    slideRef.current = setInterval(() => {
      setSlideIndex((s) => (s + 1) % images.length);
    }, 3000);
    return () => {
      if (slideRef.current) clearInterval(slideRef.current);
      slideRef.current = null;
    };
  }, [pageIndex, images]);

  // manual controls
  const prevSlide = () => {
    if (!images || images.length === 0) return;
    setSlideIndex((s) => (s - 1 + images.length) % images.length);
  };
  const nextSlide = () => {
    if (!images || images.length === 0) return;
    setSlideIndex((s) => (s + 1) % images.length);
  };

  const display = displayName;

  if (!open) return null;

  // Helper: convert plain-text URLs into clickable link elements
  const linkify = (text) => {
    if (!text || typeof text !== "string") return text;
    const urlRegex = /https?:\/\/[\S]+/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    let key = 0;
    while ((match = urlRegex.exec(text)) !== null) {
      const urlMatch = match[0];
      const start = match.index;
      // push text before the match
      if (start > lastIndex) parts.push(text.slice(lastIndex, start));

      // trim trailing punctuation that commonly follows URLs
      const trailingPuncMatch = urlMatch.match(/[\)\]\.,;:!?'"\u00BB]+$/);
      let url = urlMatch;
      let trailing = "";
      if (trailingPuncMatch) {
        trailing = trailingPuncMatch[0];
        url = urlMatch.slice(0, -trailing.length);
      }

      parts.push(
        <a key={`u-${key++}`} href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
          {url}
        </a>
      );

      if (trailing) parts.push(trailing);
      lastIndex = start + urlMatch.length;
    }
    // push remaining text
    if (lastIndex < text.length) parts.push(text.slice(lastIndex));
    return parts;
  };

  return (
    <motion.div 
      data-overlay="city"
      className="absolute right-[2vw] top-[50vh] z-20 w-[78vw] h-[90vh] p-4 bg-white/90 rounded-lg shadow-lg -translate-y-1/2"
      initial={{ opacity: 0, x: 150 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, y: 50 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
    >
      <div className="flex items-start justify-between pl-4 pt-3">
        <h2 className="text-5xl font-semibold" style={{fontFamily: 'var(--font-lobster)'}}>
          {display}
        </h2>
        <div className="flex gap-2 items-center">
          <div className="flex items-center text-lg text-gray-600 mr-2">{pageIndex + 1} / {pages.length}</div>
          <button
            className={`px-4 py-1.5 rounded text-lg ${pageIndex === 0 ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : 'bg-white border text-gray-700 hover:bg-gray-50'}`}
            onClick={() => setPageIndex((p) => Math.max(p - 1, 0))}
            aria-label="Back page"
            disabled={pageIndex === 0}
          >
            Back
          </button>
          <button
            className={`px-4 py-1.5 rounded text-lg ${pageIndex === pages.length - 1 ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
            onClick={() => {
              // advance to next page; disable advancing past the last
              setPageIndex((p) => Math.min(p + 1, pages.length - 1));
            }}
            aria-label="Next page"
            disabled={pageIndex === pages.length - 1}
          >
            Next
          </button>
          <button
            className="text-lg text-gray-500 hover:text-gray-700"
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
      <motion.div
        key={pageIndex}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24 }}
        className="mt-4 text-xl text-gray-800 bg-white/80 p-4 rounded whitespace-pre-wrap"
      >
        {pageIndex === 0 ? (
          <div>
            <div>{linkify(pages[pageIndex])}</div>
            {/* slideshow */}
            <div className="w-full mb-4 rounded overflow-hidden bg-gray-200">
              {images && images.length ? (
                <div className="relative w-full h-[35vh]">
                  <img src={images[slideIndex]} alt={`${display} image ${slideIndex + 1}`} className="w-full h-full object-cover" />
                  <div className="absolute bottom-2 left-2 flex gap-2">
                    <button onClick={prevSlide} className="px-2 py-1 bg-white/80 rounded">◀</button>
                    <button onClick={nextSlide} className="px-2 py-1 bg-white/80 rounded">▶</button>
                  </div>
                </div>
              ) : (
                <div className="w-full h-[35vh] flex items-center justify-center text-sm text-gray-500">No preview images</div>
              )}
            </div>
          </div>
        ) : (
          linkify(pages[pageIndex])
        )}
      </motion.div>
      <div className="mt-4 flex gap-2">
        {pageIndex === 1 ? (
          <div className="w-full h-[65vh] flex justify-center items-center bg-gray-100">
            <iframe
              src="https://hackharvard-25.onrender.com/"
              title="Streamlit App"
              width="100%"
              height="100%"
              style={{
                border: "none",
                borderRadius: "12px",
                boxShadow: "0 0 10px rgba(0,0,0,0.2)",
              }}
            />
          </div>
        ) : (
          // when not on page 2, keep the area small and empty so it doesn't fill the overlay
          <div className="w-full h-24 flex items-center justify-center bg-transparent text-lg text-gray-500">
            {/* intentionally empty */}
          </div>
        )}
      </div>
    </motion.div>
  );
}
