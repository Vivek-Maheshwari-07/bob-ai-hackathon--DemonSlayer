import React from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BOB AI Pharmacovigilance Platform | Drug Safety Signal Detector & CTD Readiness Checker",
  description:
    "AI-powered pharmacovigilance platform for drug safety signal detection (PRR, chi-square) and ICH M4 CTD dossier submission readiness checking. IBM BOB AI Hackathon 2026 - Problem P2.",
  keywords: "pharmacovigilance, drug safety, PRR, signal detection, CTD, ICH M4, FDA, regulatory",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ fontFamily: "'Inter', sans-serif", margin: 0 }}>{children}</body>
    </html>
  );
}
