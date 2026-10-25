import type { Metadata } from "next";
import "@copilotkit/react-core/v2/styles.css";

export const metadata: Metadata = { title: "Asset Intelligence Copilot", description: "Chat copilot for oil-well operations (CopilotKit + AG-UI)" };
const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* the design tokens and block styles come from the backend, so both UIs look the same */}
        <link rel="stylesheet" href={`${API}/static/css/tokens.css`} />
        <link rel="stylesheet" href={`${API}/static/css/app.css`} />
      </head>
      <body style={{ margin: 0, background: "var(--bg)", color: "var(--ink)", font: "14px/1.5 var(--font)" }}>{children}</body>
    </html>
  );
}
