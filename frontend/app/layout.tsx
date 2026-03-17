import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ContextShop — AI Retail Agent",
  description: "A retail agent that gets smarter with every message, powered by Qdrant context engineering",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
