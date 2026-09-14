import React from "react";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PharmaVigil AI | Drug Safety Intelligence & Regulatory Readiness",
  description:
    "Enterprise AI-powered pharmacovigilance platform for adverse-event signal detection (PRR, Chi-square), digital-twin walk-forward backtesting, and ICH M4 CTD dossier submission readiness checking. IBM Bobathon 2026 - Problem Statement P2.",
  keywords: "pharmacovigilance, drug safety, PRR, signal detection, CTD, ICH M4, FDA, regulatory, IBM Bob, AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#0c0d14] text-slate-100 antialiased min-h-screen selection:bg-blue-600/30 selection:text-white" style={{ fontFamily: "'Inter', sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
