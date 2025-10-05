"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

export default function TopBar() {
  const pathname = usePathname() || "/";
  const tabs = [
    { label: "Introduction", href: "/" },
    { label: "Map", href: "/map" },
    { label: "About Us", href: "/about" },
    { label: "Source", href: "https://github.com/ec-03/hackharvard-25" },
  ];

  // detect city overlay route like /map/jakarta
  const overlayActive = pathname.startsWith("/map/") && pathname.split("/").length >= 3;

  return (
    <motion.div
      className="fixed left-1/2 -translate-x-1/2 top-6 z-50 w-full px-4"
      animate={overlayActive ? { y: -120, opacity: 0, pointerEvents: "none" } : { y: 0, opacity: 1, pointerEvents: "auto" }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
    >
      <nav className="mx-auto max-w-4xl bg-white/90 backdrop-blur rounded-xl shadow-lg border h-[5vh] px-4 py-0 relative">
        <div className="flex items-start">
          <img src="/logo.png" alt="SimulWave Logo" className="h-10 w-auto" />
        </div>

        {/* centered tabs */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="flex items-center gap-3">
            {tabs.map((t) => {
              const active = pathname === t.href || (t.href !== "/" && pathname?.startsWith(t.href));
              return (
                <Link
                  key={t.href}
                  href={t.href}
                  className={`text-sm px-3 py-1 rounded ${active ? "bg-blue-500 text-white" : "text-gray-700 hover:text-gray-900"}`}
                >
                  {t.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
    </motion.div>
  );
}
