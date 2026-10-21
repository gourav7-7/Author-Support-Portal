import { useEffect, useState } from "react";
import {
  Leaf,
  LayoutDashboard,
  BookOpen,
  MessagesSquare,
  ArrowRight,
  LogOut,
} from "lucide-react";
import { api, useResource, navigate, useRoute } from "./api.js";
import { Notice, Loading, Brand } from "./components/UI.jsx";
import { Login } from "./pages/Login.jsx";
import { AuthorOverview } from "./pages/AuthorOverview.jsx";
import { BooksPage } from "./pages/BooksPage.jsx";
import { NewTicket } from "./pages/NewTicket.jsx";
import { TicketsPage } from "./pages/TicketsPage.jsx";
import { TicketDetail } from "./pages/TicketDetail.jsx";

export function Workspace({ user, onLogout }) {
  const route = useRoute();
  const meta = useResource("/meta", false);
  const admin = user.role === "admin";
  const [path, query] = route.split("?");
  const [page, id] = path.split("/");
  const selectedBook = new URLSearchParams(query).get("book");
  const navItems = admin
    ? [
        { id: "overview", label: "Overview", icon: LayoutDashboard },
        { id: "tickets", label: "Support queue", icon: MessagesSquare },
      ]
    : [
        { id: "overview", label: "Overview", icon: LayoutDashboard },
        { id: "books", label: "My books", icon: BookOpen },
        { id: "tickets", label: "My tickets", icon: MessagesSquare },
      ];
  let content;
  if (page === "tickets" && id)
    content = (
      <TicketDetail key={id} ticketId={id} user={user} meta={meta.data} />
    );
  else if (!admin && page === "new")
    content = (
      <NewTicket key={selectedBook || "general"} selectedBook={selectedBook} />
    );
  else if (!admin && page === "books") content = <BooksPage bookId={id} />;
  else if (admin || page === "tickets")
    content = <TicketsPage admin={admin} meta={meta.data} />;
  else content = <AuthorOverview user={user} />;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">
          <span className="status-dot" />
          {admin ? "OPERATIONS TEAM" : "AUTHOR WORKSPACE"}
        </div>
        <nav aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "active" : ""}
              onClick={() => navigate(item.id)}
            >
              <item.icon size={19} />
              {item.label}
              {page === item.id && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Leaf size={27} />
          <h3>Here for every chapter.</h3>
          <p>
            {admin
              ? "A clear reply can turn a concern into confidence."
              : "Your questions deserve the same care as your stories."}
          </p>
          {!admin && (
            <button onClick={() => navigate("new")}>
              Let’s talk <ArrowRight size={16} />
            </button>
          )}
        </div>
        <div className="sidebar-bottom">
          BookLeaf Publishing<span>Author Support & Communication</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            {admin ? "Operations" : "Author care"}{" "}
            <span className="slash">/</span>{" "}
            {page === "books"
              ? "My books"
              : page === "new"
                ? "New query"
                : page === "tickets"
                  ? "Conversations"
                  : "Overview"}
          </span>
          <div>
            <span className="avatar small">{user.name[0]}</span>
            <div className="profile-name">
              <strong>{user.name}</strong>
              <small>{admin ? "Administrator" : "Author"}</small>
            </div>
            <button
              className="icon-button"
              onClick={onLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main>
          <Notice>{meta.error}</Notice>
          {admin && meta.data && !meta.data.ai_configured && (
            <Notice kind="info">
              AI key is not configured. Triage uses rules and drafts use
              templates; manual replies work normally. Configure the backend API
              key to test the LLM.
            </Notice>
          )}
          {content}
        </main>
        <footer>
          Made for meaningful conversations.
          <span>BookLeaf Author Care · Assignment demo</span>
        </footer>
      </div>
    </div>
  );
}

export function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  function logout() {
    sessionStorage.removeItem("bookleaf.token");
    setUser(null);
    navigate("overview");
  }
  useEffect(() => {
    const expired = () => {
      sessionStorage.removeItem("bookleaf.token");
      setUser(null);
      setError("Your session ended. Please sign in again.");
    };
    window.addEventListener("session-expired", expired);
    if (sessionStorage.getItem("bookleaf.token"))
      api("/auth/me")
        .then(setUser)
        .catch((err) => {
          sessionStorage.removeItem("bookleaf.token");
          setError(err.message);
        })
        .finally(() => setLoading(false));
    else setLoading(false);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  if (loading) return <Loading />;
  return user ? (
    <Workspace key={user.id} user={user} onLogout={logout} />
  ) : (
    <Login
      initialError={error}
      onLogin={(value) => {
        setError("");
        setUser(value);
      }}
    />
  );
}
