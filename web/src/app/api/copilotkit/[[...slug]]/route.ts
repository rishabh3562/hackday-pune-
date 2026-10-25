import { CopilotRuntime, createCopilotEndpoint, InMemoryAgentRunner } from "@copilotkit/runtime/v2";
import { handle } from "hono/vercel";
import { HttpAgent } from "@ag-ui/client";

// Our Python backend speaks AG-UI at /agui.
const agent = new HttpAgent({ url: process.env.AGENT_URL || "http://localhost:8000/agui" });
const runtime = new CopilotRuntime({ agents: { asset_copilot: agent as any }, runner: new InMemoryAgentRunner() });
const app = createCopilotEndpoint({ runtime, basePath: "/api/copilotkit" });

export const GET = handle(app);
export const POST = handle(app);
