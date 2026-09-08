import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Two lockfiles exist above this app (one in the repo root's parent);
  // pin the workspace root so module resolution and file watching stay here.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
