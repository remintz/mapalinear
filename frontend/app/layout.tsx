import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navigation } from "@/components/layout/Navigation";
import { ImpersonationBanner } from "@/components/layout/ImpersonationBanner";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { ErrorReporterProvider } from "@/components/providers/ErrorReporterProvider";
import { Toaster } from "sonner";

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
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50`}
      >
        <AuthProvider>
          <ErrorReporterProvider>
            <QueryProvider>
              <div className="min-h-screen flex flex-col">
                <ImpersonationBanner />
                <Navigation />
                <main className="flex-1">
                  {children}
                </main>
              </div>
              <Toaster richColors position="top-right" />
            </QueryProvider>
          </ErrorReporterProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
