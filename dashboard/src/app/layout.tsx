import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JAA Dashboard • Job Application Assistant",
  description: "Phase 1 Application Tracking & Status Management Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-slate-100 antialiased selection:bg-cyan-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
