import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: {
    default: "TalentScope — Intelijen Pasar Kerja Indonesia",
    template: "%s · TalentScope",
  },
  description:
    "Jelajahi arsip lowongan kerja Indonesia yang pernah tayang, distribusi wilayah, dan gaji yang dicantumkan, dengan sumber dan batasan data yang transparan.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" className={`${inter.variable} ${geist.variable} ${geistMono.variable}`}>
      <body className="min-h-screen bg-canvas">{children}</body>
    </html>
  );
}
