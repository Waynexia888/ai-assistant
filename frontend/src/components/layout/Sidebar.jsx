import { useState } from "react";
import { historyGroups } from "../../data/dashboardData";
import { Icon } from "../common/Icon";

export function Sidebar({ onOpenWorkspace }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  function closeMobileMenu() {
    setIsMobileMenuOpen(false);
  }

  return (
    <>
      <aside className={`sidebar ${isMobileMenuOpen ? "is-open" : ""}`}>
        <button
          className="mobile-menu-trigger"
          type="button"
          aria-label="Open sidebar"
          aria-expanded={isMobileMenuOpen}
          onClick={() => setIsMobileMenuOpen(true)}
        >
          <Icon name="menu" />
        </button>
        <button
          className="workspace-rail-trigger"
          type="button"
          aria-label="Open agent workspace"
          onClick={onOpenWorkspace}
        >
          <Icon name="bot" />
        </button>
        <div className="mobile-top-actions">
          <button type="button" aria-label="Open agent workspace" onClick={onOpenWorkspace}>
            <Icon name="gear" />
          </button>
          <button type="button" aria-label="New window">
            <Icon name="edit" />
          </button>
          <button type="button" aria-label="More options">
            <Icon name="more" />
          </button>
        </div>

        <div className="sidebar-drawer">
          <div className="brand">
            <span className="brand-mark"><Icon name="bot" /></span>
            <strong>AI Assistant</strong>
          </div>

          <button className="mobile-menu-close" type="button" aria-label="Close sidebar" onClick={closeMobileMenu}>
            <Icon name="close" />
          </button>

          <button className="new-chat" type="button" onClick={closeMobileMenu}><Icon name="plus" />New Chat</button>
          <div className="searchbox"><Icon name="search" /><span>Search chats...</span><kbd>⌘ K</kbd></div>
          <h2>Chat History</h2>
          <div className="history">
            {historyGroups.map((group) => (
              <section key={group.label}>
                <p>{group.label}</p>
                {group.items.map(([title, time, active]) => (
                  <div className={`history-item ${active ? "active" : ""}`} key={title} onClick={closeMobileMenu}>
                    <span>{title}</span>
                    <time>{time}</time>
                  </div>
                ))}
              </section>
            ))}
          </div>
          <div className="profile">
            <img src="https://i.pravatar.cc/80?img=11" alt="" />
            <div>
              <strong>Zhang San</strong>
              <span>Online</span>
            </div>
            <button type="button">⌄</button>
          </div>
        </div>
      </aside>

      {isMobileMenuOpen && <button className="mobile-menu-backdrop" type="button" aria-label="Close sidebar" onClick={closeMobileMenu} />}
    </>
  );
}
