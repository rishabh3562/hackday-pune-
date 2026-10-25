"use client";

import { CopilotChat, CopilotKitProvider, useAgent, useCopilotKit, useFrontendTool } from "@copilotkit/react-core/v2";
import { useEffect, useState } from "react";
import { z } from "zod";
import { PickContext, ResultView } from "@/components/ResultView";

export const dynamic = "force-dynamic";
const AGENT = "asset_copilot";
const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";

function Chat({ user }: { user: string }) {
  const { agent } = useAgent({ agentId: AGENT });
  const { copilotkit } = useCopilotKit();
  // clicking a clarify option sends it as the next user message (same as typing it)
  const pick = async (text: string) => {
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content: text } as any);
    await copilotkit.runAgent({ agent });
  };
  // The Python backend reads the acting user from AG-UI state, so private memory stays per user.
  useEffect(() => { agent?.setState?.({ ...(agent.state || {}), user_id: user }); }, [agent, user]);
  // Generative UI: the backend emits a `show_result` tool call whose args are the typed UI spec.
  useFrontendTool({
    name: "show_result",
    description: "Render a table, card, chart, map or heatmap for the answer",
    parameters: z.object({}).passthrough() as any,
    followUp: false, // render-only tool: do not send the result back to the agent (that re-ran it in a loop)
    render: ({ args }: any) => <ResultView spec={args} />,
  } as any, []);
  return <PickContext.Provider value={pick}><CopilotChat agentId={AGENT} welcomeScreen={false} className="flex-1" labels={{ chatInputPlaceholder: "Ask about your wells…" } as any} /></PickContext.Provider>;
}

export default function Page() {
  const [users, setUsers] = useState<any[]>([]);
  const [user, setUser] = useState("U-201");
  useEffect(() => { fetch(`${API}/api/users`).then((r) => r.json()).then(setUsers).catch(() => {}); }, []);
  return (
    <CopilotKitProvider runtimeUrl="/api/copilotkit">
      <div style={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
        <header className="chat-head">
          <b>🛢 Asset Intelligence Copilot <span className="badge info">CopilotKit + AG-UI</span></b>
          <label className="small mute">User{" "}
            <select className="select" style={{ width: "auto" }} value={user} onChange={(e) => setUser(e.target.value)}>
              {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.name} · {u.role.replace(/_/g, " ")}</option>)}
            </select>
          </label>
        </header>
        <div style={{ flex: 1, minHeight: 0, display: "flex" }}><Chat user={user} /></div>
      </div>
    </CopilotKitProvider>
  );
}
