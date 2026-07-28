import path from 'node:path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // @veo/ui ships TypeScript + CSS Modules source, so Next compiles it directly.
  transpilePackages: ['@veo/ui'],
  poweredByHeader: false,
  turbopack: {
    // The repo lives inside a larger checkout, so pin the root explicitly
    // instead of letting Next infer it from the nearest lockfile.
    root: path.join(import.meta.dirname, '..', '..'),
  },
};

export default nextConfig;
