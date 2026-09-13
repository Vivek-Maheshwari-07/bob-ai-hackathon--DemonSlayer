import React from "react";

export const metadata = {
  title: "Drug Safety Signal Detector & Regulatory Submission Readiness Checker",
  description: "AI-powered pharmacovigilance safety signal detection and ICH M4 CTD dossier readiness checker with IBM Bob Copilot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
