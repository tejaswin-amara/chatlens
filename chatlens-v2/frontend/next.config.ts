import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath: process.env.BASE_PATH || undefined,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
