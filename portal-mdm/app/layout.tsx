import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { QueryProvider } from "@/components/providers/query-provider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s — Portal MDM ACP",
    default: "Portal MDM — ACP",
  },
  description:
    "Portal de gestión de datos maestros (MDM) para analistas, administradores y ejecutivos de ACP.",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      data-theme="dark"
      className={`${inter.variable} ${jetBrainsMono.variable} h-full antialiased`}
    >
      <body className="bg-bg text-text min-h-full font-sans">
        {/* Skip navigation link — visible on focus for keyboard users */}
        <a
          href="#main-content"
          className="bg-[var(--color-primary)] text-[var(--color-primary-foreground)] fixed left-2 top-2 z-[9999] -translate-y-20 rounded-md px-4 py-2 text-sm font-medium transition-transform focus:translate-y-0"
        >
          Saltar al contenido principal
        </a>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
