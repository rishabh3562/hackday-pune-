import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  reactStrictMode: false,
  // keep the CopilotKit runtime's logger (pino) out of the bundle
  serverExternalPackages: ["pino", "thread-stream", "pino-pretty", "@copilotkit/runtime"],
};
export default nextConfig;
