import type { NextConfig } from "next";
import { previewConfig } from "./preview-config";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  ...previewConfig(process.env),
};

export default nextConfig;
