import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Plus_Jakarta_Sans } from "next/font/google";

import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const appUrl =
  process.env.APP_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: {
    default: "CyVerse Internal Tools",
    template: "%s · CyVerse",
  },
  description: "Secure internal tools for explainable AI and trusted media workflows.",
  openGraph: {
    title: "CyVerse Internal Tools",
    description: "Detect · Deceive · Defend",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "CyVerse Internal Tools" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CyVerse Internal Tools",
    description: "Detect · Deceive · Defend",
    images: ["/og.png"],
  },
};

import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={plusJakartaSans.variable} suppressHydrationWarning>
      <body className={plusJakartaSans.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
          <Toaster position="top-right" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
