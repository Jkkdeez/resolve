import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
  output: "standalone",
  async rewrites() {
    const apiOrigin = process.env.RESOLVE_API_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiOrigin}/:path*` }];
  },
};

export default nextConfig;
