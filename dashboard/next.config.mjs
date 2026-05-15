/** @type {import('next').NextConfig} */
// GitHub Pages publishes this app at /Wand-deployment-readiness-score/. Use
// BASE_PATH="" for Vercel or local dev (no path prefix).
const basePath = process.env.BASE_PATH === undefined
  ? '/Wand-deployment-readiness-score'
  : process.env.BASE_PATH;

const nextConfig = {
  output: 'export',
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};
export default nextConfig;
