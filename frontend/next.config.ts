import type { NextConfig } from "next";
import withSerwistInit from "@serwist/next";

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        pathname: "/**",
      },
    ],
  },
  eslint: {
    // Ignora erros de lint durante build de produção
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignora erros de tipo durante build de produção
    ignoreBuildErrors: true,
  },
};

export default withSerwist(nextConfig);
