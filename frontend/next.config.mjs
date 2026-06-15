/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api/* to the FastAPI backend so the browser can use same-origin paths.
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
