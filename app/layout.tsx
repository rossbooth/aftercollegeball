import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

const SITE_URL = "https://aftercollegeball.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "What Happens After College Ball? | NCAA D1 Basketball Career Outcomes",
  description:
    "We tracked 18,688 NCAA D1 men's basketball players from 2015 to present. Only 1 in 22 made the NBA. Explore where the rest ended up — NBA, G-League, Europe, International, or no pro career.",
  keywords: [
    "NCAA basketball", "D1 basketball", "college basketball career outcomes",
    "NBA draft", "G-League", "basketball career paths", "college basketball stats",
    "what percentage of college basketball players go pro",
    "NCAA to NBA", "college basketball player outcomes",
  ],
  openGraph: {
    title: "What Happens After College Ball?",
    description:
      "We tracked 18,688 D1 basketball players. Only 1 in 22 made the NBA. See where the rest ended up.",
    type: "website",
    url: SITE_URL,
    siteName: "After College Ball",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "What happens after college ball? Interactive career outcome visualization for NCAA D1 basketball players",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "What Happens After College Ball?",
    description:
      "We tracked 18,688 D1 basketball players. Only 1 in 22 made the NBA. See where the rest ended up.",
    images: ["/og-image.png"],
  },
  alternates: {
    canonical: SITE_URL,
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "48x48" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: "/favicon.svg",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};

// JSON-LD structured data
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      name: "After College Ball",
      url: SITE_URL,
      description: "Interactive career outcome data for NCAA D1 men's basketball players from 2015 to present.",
    },
    {
      "@type": "Dataset",
      name: "NCAA D1 Men's Basketball Career Outcomes (2015-2025)",
      description: "Career path data for 18,688 NCAA Division I men's basketball players, tracking post-college destinations including NBA, G-League, European leagues, other international leagues, and players who left professional basketball.",
      url: SITE_URL,
      keywords: ["NCAA basketball", "career outcomes", "NBA", "G-League", "international basketball"],
      temporalCoverage: "2015/2025",
      variableMeasured: [
        "Post-college career destination",
        "Career length",
        "College statistics",
      ],
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "What percentage of D1 basketball players make the NBA?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Only about 4.4% of NCAA D1 men's basketball players who completed their college careers between 2015 and 2025 played in the NBA. That's roughly 1 in 22 players.",
          },
        },
        {
          "@type": "Question",
          name: "Where do college basketball players go if they don't make the NBA?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Of 18,688 D1 players tracked, 5.7% went to the NBA G-League, 11.1% played in European leagues, 17.0% played in other international leagues, and 61.9% had no professional basketball career.",
          },
        },
        {
          "@type": "Question",
          name: "How many PPG did NBA players average in college?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Players who made it to the NBA averaged 14.8 points per game in their final college season, compared to 12.1 PPG for G-League players, 10.3 PPG for European league players, and 4.8 PPG for those with no pro career.",
          },
        },
        {
          "@type": "Question",
          name: "Which colleges produce the most NBA players?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "From 2015-2025, the top NBA-producing schools were Kentucky (41 players), Duke (40), Arizona (20), Kansas (19), and Gonzaga (17).",
          },
        },
      ],
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
