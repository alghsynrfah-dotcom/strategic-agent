
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

type Domain = "financial" | "economic";
type UserAction = "message" | "edit" | "confirm" | "proceed";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface Project {
  project_id: string;
  domain: Domain;
  statement?: string;
  statement_status?: string;
  plan?: string;
  risks?: string;
  solution_comparison?: string;
}

interface Result {
  response?: string;
  statement?: string;
  statement_status?: string;
  assumptions?: string[];
  plan?: string;
  risks?: string;
  solution_comparison?: string;
  execution_time?: number;
}

function App() {
  const [domain, setDomain] = useState<Domain>("financial");
  const [project, setProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [editingProblem, setEditingProblem] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [backendOnline, setBackendOnline] = useState(false);

  const [streamStatement, setStreamStatement] = useState("");
  const [streamPlan, setStreamPlan] = useState("");
  const [streamRisks, setStreamRisks] = useState("");
  const [streamComparison, setStreamComparison] = useState("");

  const streamStageRef = useRef("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((r) => {
        if (!r.ok) throw new Error("Backend offline");
        setBackendOnline(true);
      })
      .catch(() => setBackendOnline(false));
  }, []);



  async function createProject() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not create project.");
      }

      setProject({
        project_id: data.project_id,
        domain: data.domain,
      });

      setMessages([]);
      setProgress([]);
      setResult(null);
      setStreamStatement("");
      setStreamPlan("");
      setStreamRisks("");
      setStreamComparison("");
      streamStageRef.current = "";
      setDraft("");
      setEditingProblem(false);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  }

  async function sendAction(action: UserAction, text?: string) {
    if (!project || loading) return;

    const message = (text ?? draft).trim();

    if (action === "message" && !message) {
      setError("Please enter a message first.");
      return;
    }

    setLoading(true);
    setError("");
    setProgress([]);
    setStreamStatement("");
    setStreamPlan("");
    setStreamRisks("");
    setStreamComparison("");
    streamStageRef.current = "";

    if (action === "edit") {
      setResult({
        statement: "",
        statement_status: "none",
        assumptions: [],
        plan: "",
        risks: "",
        solution_comparison: "",
        response: "",
      });

      setProject((old) =>
        old
          ? {
              ...old,
              statement: "",
              statement_status: "none",
              plan: "",
              risks: "",
              solution_comparison: "",
            }
          : old
      );
    } else {
      setResult(null);
    }

    if (action === "message" && message) {
      setMessages((old) => [
        ...old,
        { role: "user", content: message },
      ]);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: project.project_id,
          message,
          user_action: action,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          body.detail || body.error || `Request failed: ${response.status}`
        );
      }

      if (!response.body) {
        throw new Error("The browser does not support response streaming.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: Result | null = null;

      while (true) {
        const { value, done } = await reader.read();

        buffer += decoder.decode(value || new Uint8Array(), {
          stream: !done,
        });

        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          let eventName = "";
          const dataLines: string[] = [];

          for (const line of block.split(/\r?\n/)) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trim());
            }
          }

          if (!dataLines.length) continue;

          let payload: Record<string, unknown>;

          try {
            payload = JSON.parse(dataLines.join("\n"));
          } catch {
            continue;
          }

          if (eventName === "progress") {
            const progressMessage = String(
              payload.message || payload.text || payload.kind || ""
            );
            const eventKind = String(payload.kind || "").toLowerCase();

            if (progressMessage) {
              setProgress((old) => [...old, progressMessage]);
            }

            if (
              eventKind === "draft" ||
              eventKind.includes("draft_statement")
            ) {
              streamStageRef.current = "statement";
            } else if (
              eventKind === "statement_replace" ||
              eventKind.includes("statement_replace")
            ) {
              streamStageRef.current = "statement";

              const replacementText = String(
                payload.text || payload.statement || payload.message || ""
              );

              if (replacementText) {
                setStreamStatement(replacementText);
              }
            }
          }

          if (eventName === "token") {
            const tokenText = String(payload.text || "");
            const section = String(payload.section || "").toLowerCase();

            if (tokenText) {
              if (section === "plan") {
                setStreamPlan((old) => old + tokenText);
              } else if (section === "risks") {
                setStreamRisks((old) => old + tokenText);
              } else if (section === "comparison") {
                setStreamComparison((old) => old + tokenText);
              } else if (
                section === "statement" ||
                streamStageRef.current === "statement"
              ) {
                setStreamStatement((old) => old + tokenText);
              }
            }
          }

          if (eventName === "done") {
            finalResult = payload as Result;
          }

          if (eventName === "error") {
            throw new Error(
              String(payload.error || "The agent encountered an error.")
            );
          }
        }

        if (done) break;
      }

      if (!finalResult) {
        throw new Error("The workflow ended without a final result.");
      }

      setResult(finalResult);

      if (finalResult.response) {
        setMessages((old) => [
          ...old,
          {
            role: "assistant",
            content: finalResult.response!,
          },
        ]);
      }

      setProject((old) =>
        old
          ? {
              ...old,
              statement: finalResult?.statement ?? old.statement,
              statement_status:
                finalResult?.statement_status ?? old.statement_status,
              plan: finalResult?.plan ?? old.plan,
              risks: finalResult?.risks ?? old.risks,
              solution_comparison:
                finalResult?.solution_comparison ?? old.solution_comparison,
            }
          : old
      );

      setDraft("");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  const statement =
    streamStatement || result?.statement || project?.statement || "";

  const status =
    result?.statement_status ?? project?.statement_status ?? "none";

  const plan = streamPlan || result?.plan || project?.plan || "";
  const risks = streamRisks || result?.risks || project?.risks || "";

  const comparison =
    streamComparison ||
    result?.solution_comparison ||
    project?.solution_comparison ||
    "";

  const assumptions = result?.assumptions ?? [];

  function statusText(value: string) {
    const labels: Record<string, string> = {
      none: "Not drafted yet",
      draft: "Awaiting your decision",
      confirmed: "Confirmed",
      unconfirmed: "Continued without confirmation",
    };

    return labels[value] || value.replaceAll("_", " ");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Strategic Agent</strong>
            <small>Problem framing & decision support</small>
          </div>
        </div>

        <div className="connection">
          <span
            className={`connection-dot ${
              backendOnline ? "online" : "offline"
            }`}
          />
          {backendOnline ? "Backend connected" : "Backend offline"}
        </div>
      </header>

      <main className="layout">
        <aside className="sidebar">
          <p className="eyebrow">WORKSPACE</p>
          <h2>New analysis</h2>

          <p className="muted">
            Choose the domain for your problem.
          </p>

          <div className="domain-options">
            <button
              className={`domain-option ${
                domain === "financial" ? "selected" : ""
              }`}
              onClick={() => setDomain("financial")}
              disabled={loading}
            >
              <span className="domain-icon">$</span>
              <span>
                <strong>Financial</strong>
                <small>Revenue, costs, budgets</small>
              </span>
            </button>

            <button
              className={`domain-option ${
                domain === "economic" ? "selected" : ""
              }`}
              onClick={() => setDomain("economic")}
              disabled={loading}
            >
              <span className="domain-icon">↗</span>
              <span>
                <strong>Economic</strong>
                <small>Markets, demand, growth</small>
              </span>
            </button>
          </div>

          <button
            className="primary-button full"
            onClick={() => void createProject()}
            disabled={loading}
          >
            {loading ? "Creating..." : "+ New project"}
          </button>

          {project && (
            <div className="active-project">
              <p className="eyebrow">CURRENT PROJECT</p>
              <strong>{project.domain} analysis</strong>
              <small>ID: {project.project_id.slice(0, 8)}...</small>
            </div>
          )}

          <div className="sidebar-note">
            The agent clarifies the problem first. After you review
            the statement, it can continue to planning and risk analysis.
          </div>
        </aside>

        <section className="main-panel">
          {!project ? (
            <div className="welcome-card">
              <div className="welcome-symbol">✦</div>
              <p className="eyebrow">STRATEGIC INTELLIGENT AGENT</p>
              <h1>Turn a complex problem into a clear next step.</h1>
              <p className="muted welcome-copy">
                Describe your situation, clarify what is missing,
                and build a structured problem statement before planning.
              </p>
              <button
                className="primary-button"
                onClick={() => void createProject()}
                disabled={loading}
              >
                {loading ? "Creating project..." : "Start a project →"}
              </button>
            </div>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">
                    {project.domain.toUpperCase()} WORKSPACE
                  </p>
                  <h1>Problem analysis</h1>
                  <p className="muted">
                    Explain the situation. The agent will ask about
                    missing information when needed.
                  </p>
                </div>
                <span className="status-pill">{statusText(status)}</span>
              </div>

              <section className="panel">
                <div className="section-title">
                  <h2>01 — Conversation</h2>
                  <span>{messages.length} messages</span>
                </div>

                {messages.length === 0 && (
                  <div className="intro-message">
                    <div className="agent-avatar">S</div>
                    <div className="message-bubble assistant-bubble">
                      <strong>Let’s understand the problem first.</strong>
                      <p>
                        Tell me what is happening, the context, and
                        the impact you are seeing. It is okay if some
                        details are not known yet.
                      </p>
                    </div>
                  </div>
                )}

                <div className="message-list">
                  {messages.map((message, index) => (
                    <div
                      className={`message-row ${message.role}`}
                      key={`${index}-${message.role}`}
                    >
                      {message.role === "assistant" && (
                        <div className="agent-avatar">S</div>
                      )}
                      <div
                        className={`message-bubble ${
                          message.role === "assistant"
                            ? "assistant-bubble"
                            : "user-bubble"
                        }`}
                      >
                        <span className="message-author">
                          {message.role === "assistant"
                            ? "Strategic Agent"
                            : "You"}
                        </span>
                        <p dir="auto">{message.content}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {loading && (
                  <div className="working-box">
                    <span className="spinner" />
                    <div>
                      <strong>Agent is working...</strong>
                      <p>
                        {progress[progress.length - 1] ||
                          "Processing your request"}
                      </p>
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />

                <form
                  className="composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void sendAction("message");
                  }}
                >
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="Describe the problem or answer the agent..."
                    rows={3}
                    disabled={loading}
                  />
                  <div className="composer-footer">
                    <span>Describe the problem in your own words.</span>
                    <button
                      className="primary-button"
                      type="submit"
                      disabled={loading || !draft.trim()}
                    >
                      {loading ? "Working..." : "Send message ↑"}
                    </button>
                  </div>
                </form>
              </section>

              {error && (
                <div className="error-banner">
                  <strong>Something went wrong</strong>
                  <p>{error}</p>
                </div>
              )}

              {progress.length > 0 && (
                <section className="panel">
                  <div className="section-title">
                    <h2>Workflow activity</h2>
                    <span>{loading ? "In progress" : "Latest run"}</span>
                  </div>
                  <ol className="progress-list">
                    {progress.map((item, index) => (
                      <li key={`${index}-${item}`}>{item}</li>
                    ))}
                  </ol>
                </section>
              )}

              {statement && (
                <section className="panel">
                  <div className="section-title">
                    <h2>02 — Problem statement</h2>
                    <span className="status-pill">
                      {statusText(status)}
                    </span>
                  </div>

                  <div className="statement-box" dir="auto">
                    {statement}
                  </div>

                  {assumptions.length > 0 && (
                    <div className="assumptions-box">
                      <strong>Assumptions to validate</strong>
                      <ul>
                        {assumptions.map((item, index) => (
                          <li key={`${index}-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {!loading && !editingProblem && (
                    <div className="decision-actions">
                      <button
                        className="primary-button"
                        onClick={() => void sendAction("confirm")}
                      >
                        Confirm statement
                      </button>
                      <button
                        className="link-button"
                        onClick={() => {
                          setEditingProblem(true);
                          setDraft("");
                        }}
                      >
                        ✎ Edit problem & rethink
                      </button>
                    </div>
                  )}

                  {editingProblem && (
                    <form
                      className="composer"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void sendAction("edit");
                        setEditingProblem(false);
                      }}
                    >
                      <label htmlFor="problem-edit">
                        Describe the changes you want to make
                      </label>
                      <textarea
                        id="problem-edit"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        placeholder="Explain what should change in the problem statement..."
                        rows={4}
                        disabled={loading}
                        autoFocus
                      />
                      <div className="composer-footer">
                        <span>
                          The agent will reassess the problem using your changes.
                        </span>
                        <button
                          type="button"
                          className="link-button"
                          disabled={loading}
                          onClick={() => {
                            setEditingProblem(false);
                            setDraft("");
                            setError("");
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          className="primary-button"
                          type="submit"
                          disabled={loading || !draft.trim()}
                        >
                          {loading ? "Re-evaluating..." : "Submit changes"}
                        </button>
                      </div>
                    </form>
                  )}
                </section>
              )}

              {(plan || risks) && (
                <div className="results-grid">
                  {plan && (
                    <section className="panel">
                      <div className="section-title">
                        <h2>03 — Solution plan</h2>
                      </div>
                      <div className="result-text" dir="auto">
                        {plan}
                      </div>
                    </section>
                  )}

                  {risks && (
                    <section className="panel">
                      <div className="section-title">
                        <h2>04 — Risks of the solution plan</h2>
                      </div>
                      <div className="result-text" dir="auto">
                        {risks}
                      </div>
                    </section>
                  )}
                </div>
              )}

              {comparison && (
                <section className="panel">
                  <div className="section-title">
                    <h2>05 — Solution Comparison & Recommendation</h2>
                    <span className="status-pill">Completed</span>
                  </div>
                  <div className="result-text" dir="auto">
                    {comparison}
                  </div>
                </section>
              )}
            </>
          )}
        </section>
      </main>

      <footer className="footer">
        Strategic Intelligent Agent
        <span>Problem clarity · Planning · Risk analysis · Solution comparison</span>
      </footer>
    </div>
  );
}

export default App;

