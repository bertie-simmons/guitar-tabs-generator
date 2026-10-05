import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Emit .next/standalone: a server.js plus only the node_modules it needs,
  // so the container image doesn't carry the whole dependency tree.
  output: "standalone",
  // Two lockfiles exist above this app (one in the repo root's parent);
  // pin the workspace root so module resolution and file watching stay here.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
