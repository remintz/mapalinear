import type { NextConfig } from "next";

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

export default nextConfig;
