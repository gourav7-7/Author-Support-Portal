import { useState } from "react";
import { BookOpen, ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { api } from "../api.js";
import { Notice, Brand } from "../components/UI.jsx";

export function Login({ onLogin, initialError }) {
  const [email, setEmail] = useState("priya.sharma@email.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(initialError || "");
  const [busy, setBusy] = useState(false);
  const choose = (role) => {
    setEmail(
      role === "admin" ? "admin@authorcare.demo" : "priya.sharma@email.com",
    );
    setPassword(role === "admin" ? "AdminDemo!2026" : "AuthorDemo!2026");
    setError("");
  };
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      sessionStorage.setItem("authorcare.token", data.access_token);
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <Brand inverse />
        <div className="story-center">
          <span className="eyebrow">WORDS BRING US TOGETHER</span>
          <h1>
            Your story matters.
            <br />
            <em>
              So does your peace
              <br />
              of mind.
            </em>
          </h1>
          <p>
            A dedicated space for your books, royalties and conversations with
            the AuthorCare team.
          </p>
          <div className="story-books" aria-hidden="true">
            <div className="spine one">THE AUTHOR’S JOURNEY</div>
            <div className="spine two">WORDS & WONDER</div>
            <div className="spine three">A NEW CHAPTER</div>
          </div>
        </div>
        <small>Thoughtful publishing. Personal support.</small>
      </section>
      <section className="login-side">
        <div className="login-form">
          <span className="eyebrow">WELCOME TO AUTHOR CARE</span>
          <h2>
            A little closer to
            <br />
            your next chapter.
          </h2>
          <p>Sign in to your author or operations workspace.</p>
          <Notice>{error}</Notice>
          <form onSubmit={submit}>
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
              />
            </label>
            <button className="button primary full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in to your workspace"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="demo-login">
            <span className="eyebrow">EXPLORE THE ASSIGNMENT DEMO</span>
            <div>
              <button onClick={() => choose("author")}>
                <BookOpen size={16} />
                Author account
              </button>
              <button onClick={() => choose("admin")}>
                <ShieldCheck size={16} />
                Admin account
              </button>
            </div>
            <small>
              These buttons fill the documented demo credentials. Accounts use
              the supplied sample data.
            </small>
          </div>
          <div className="login-note">
            <LockKeyhole size={15} />
            Your books and conversations stay within your account.
          </div>
        </div>
      </section>
    </div>
  );
}
