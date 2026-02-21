import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navigation } from "@/components/layout/Navigation";
import { ImpersonationBanner } from "@/components/layout/ImpersonationBanner";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { ErrorReporterProvider } from "@/components/providers/ErrorReporterProvider";
import { Toaster } from "sonner";
import { OfflineProvider } from "@/components/providers/OfflineProvider";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { InstallPrompt } from "@/components/ui/InstallPrompt";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OraPOIS - Pontos de Interesse em Viagens",
  description: "Crie mapas lineares com pontos de interesse para suas viagens brasileiras",
  manifest: "/manifest.webmanifest",
  themeColor: "#2563eb",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "OraPOIS",
  },
  icons: {
    apple: "/icons/apple-touch-icon.png",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="manifest" href="/manifest.webmanifest" />
        <meta name="theme-color" content="#2563eb" />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50`}
      >
        <AuthProvider>
          <ErrorReporterProvider>
            <QueryProvider>
              <OfflineProvider>
                <OfflineBanner />
                <div className="min-h-screen flex flex-col">
                  <ImpersonationBanner />
                  <Navigation />
                  <main className="flex-1">
                    {children}
                  </main>
                </div>
                <Toaster richColors position="top-right" />
                <InstallPrompt />
              </OfflineProvider>
            </QueryProvider>
          </ErrorReporterProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
