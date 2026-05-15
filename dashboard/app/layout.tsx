import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Wand Deployment Readiness Harness",
  description: "GO / NO-GO verdict for any multi-agent system before it touches production.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-ink font-sans antialiased">{children}</body>
    </html>
  );
}
