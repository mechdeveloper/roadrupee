import type { Metadata } from "next";
import { Inter, Noto_Sans_Devanagari } from "next/font/google";
import { I18nProvider } from "@/lib/i18n";
import "leaflet/dist/leaflet.css";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
// Inter has no Devanagari glyphs; this covers Hindi and Marathi text.
const deva = Noto_Sans_Devanagari({ variable: "--font-deva", subsets: ["devanagari"] });

export const metadata: Metadata = {
  title: "RoadRupee — where did the repair money go?",
  description:
    "Follow Mumbai's monsoon road repair money: what was spent, whether the fix held, and where the next rupee should go. Synthetic data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${deva.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
