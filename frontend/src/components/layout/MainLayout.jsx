import { Sidebar } from "./Sidebar";

export function MainLayout({ chat, tools, workspace }) {
  return (
    <div className="app-shell">
      <Sidebar />
      {chat}
      {tools}
      {workspace}
    </div>
  );
}
