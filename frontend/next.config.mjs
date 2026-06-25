/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained build output for small, dependency-free Docker images.
  output: "standalone",
  // Proxy /api/* to the FastAPI backend so the browser can use same-origin paths.
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8754";
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
