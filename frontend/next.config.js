/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      { source: '/app', destination: '/dashboard', permanent: false },
      { source: '/app/:path*', destination: '/:path*', permanent: false },
    ];
  },
};

module.exports = nextConfig;
