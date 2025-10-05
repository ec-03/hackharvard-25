"use client";
import Link from "next/link";
import CityMap from "./map/components/CityMap";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-sky-50 to-white">
      <div className="container mx-auto px-6 lg:px-20 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <div>
            <div className="mb-4">
              <img src="/logo.png" alt="SimulWave Logo" className="h-50 w-auto" />
            </div>
            <p className="mt-4 text-lg text-slate-700 max-w-xl">
              Interactive map displaying information regarding tsunami history and damage in coastal cities.
            </p>

            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <Link href="/map" className="inline-block px-5 py-3 bg-blue-600 text-white rounded shadow hover:bg-blue-700">
                Open Map
              </Link>
              <Link href="/about" className="inline-block px-5 py-3 border border-slate-200 rounded text-slate-700 hover:bg-slate-50">
                About
              </Link>
            </div>
          </div>

          <div className="w-full h-96 rounded-lg overflow-hidden shadow-lg bg-white">
            {/* lightweight preview of the city map */}
            <div className="w-full h-full">
              <CityMap onSelect={() => {}} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
