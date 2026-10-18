import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SentinelGraph | Autonomous Cross-System Failure Investigation",
  description: "Agentic AI-powered cross-system workflow failure investigation and root-cause analysis platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-slate-100 antialiased selection:bg-cyan-500 selection:text-slate-900">
        {children}
      </body>
    </html>
  );
}
