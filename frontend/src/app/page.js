"use client";
import { useEffect, useState } from "react";
import CityMap from "./map/components/CityMap";

export default function HomePage() {
  const [message, setMessage] = useState("Loading...");

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
      }}
    >
      <h1>Hi</h1>
    </main>
  );
}
