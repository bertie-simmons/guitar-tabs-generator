import type { Metadata } from "next";
import { Overpass, Overpass_Mono } from "next/font/google";
import "./globals.css";

const overpass = Overpass({
  variable: "--font-sans",
  subsets: ["latin"],
});

const overpassMono = Overpass_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GTAB — guitar tablature from video",
  description:
    "Upload a guitar video and read back a playable ASCII tab, synced to the footage.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${overpass.variable} ${overpassMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
