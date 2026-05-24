import { cloneElement, useState } from "react";
import { Sidebar } from "./Sidebar";

export function MainLayout({ chat, tools, workspace }) {
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar onOpenWorkspace={() => setIsWorkspaceOpen(true)} />
      {chat}
      {tools && cloneElement(tools, {
        isWorkspaceOpen,
        onCloseWorkspace: () => setIsWorkspaceOpen(false),
      })}
      {workspace}
      {isWorkspaceOpen && (
        <button
          className="workspace-backdrop"
          type="button"
          aria-label="Close workspace"
          onClick={() => setIsWorkspaceOpen(false)}
        />
      )}
    </div>
  );
}
