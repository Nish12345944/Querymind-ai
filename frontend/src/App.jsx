import { useState } from "react";
import axios from "axios";
import {
  Database,
  Send,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  MessageCircleQuestion,
} from "lucide-react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState(false);
  const [error, setError] = useState("");

  const [clarificationAnswer, setClarificationAnswer] = useState("");
  const [clarifying, setClarifying] = useState(false);

  const submitQuestion = async (event) => {
    event?.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      setError("Please enter a question.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setShowSql(false);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/query/`,
        {
          question: trimmedQuestion,
        }
      );

      setResult(response.data);
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to connect to QueryMind API. Make sure the FastAPI server is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const submitClarification = async (event) => {
    event?.preventDefault();

    if (!clarificationAnswer.trim()) {
      return;
    }

    if (!result?.conversation_id) {
      setError("Conversation ID is missing.");
      return;
    }

    setClarifying(true);
    setError("");

    try {
      const response = await axios.post(
        `${API_BASE_URL}/query/clarify`,
        {
          conversation_id: result.conversation_id,
          answer: clarificationAnswer.trim(),
        }
      );

      setResult(response.data);
      setClarificationAnswer("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to continue the clarification."
      );
    } finally {
      setClarifying(false);
    }
  };

  const renderResult = () => {
    if (!result) {
      return null;
    }

    if (result.status === "clarification_required") {
      return (
        <section className="result-card clarification-card">
          <div className="result-header">
            <div className="result-title">
              <MessageCircleQuestion size={22} />
              <div>
                <h2>Clarification required</h2>
                <p>QueryMind needs a little more information.</p>
              </div>
            </div>

            <span className="status-badge clarification">
              Clarification
            </span>
          </div>

          <div className="clarification-content">
            <p className="clarification-question">
              {result.question ||
                result.clarification ||
                result.reason ||
                "Please clarify your request."}
            </p>

            {result.options?.length > 0 && (
              <div className="clarification-options">
                {result.options.map((option, index) => (
                  <button
                    key={index}
                    className="option-button"
                    onClick={() =>
                      setClarificationAnswer(
                        option.label || option.description || ""
                      )
                    }
                  >
                    <strong>{option.label}</strong>

                    {option.description && (
                      <span>{option.description}</span>
                    )}
                  </button>
                ))}
              </div>
            )}

            <form
              className="clarification-form"
              onSubmit={submitClarification}
            >
              <input
                type="text"
                value={clarificationAnswer}
                onChange={(event) =>
                  setClarificationAnswer(event.target.value)
                }
                placeholder="Type your clarification..."
                disabled={clarifying}
              />

              <button
                type="submit"
                disabled={
                  clarifying || !clarificationAnswer.trim()
                }
              >
                {clarifying ? (
                  <Loader2 className="spin" size={18} />
                ) : (
                  <Send size={18} />
                )}

                Continue
              </button>
            </form>
          </div>
        </section>
      );
    }

    if (result.status === "unsupported") {
      return (
        <section className="result-card error-card">
          <div className="result-header">
            <div className="result-title">
              <AlertCircle size={22} />
              <div>
                <h2>Unsupported query</h2>
                <p>QueryMind cannot answer this request.</p>
              </div>
            </div>

            <span className="status-badge unsupported">
              Unsupported
            </span>
          </div>

          <p className="reason-text">
            {result.reason ||
              "The requested information is not available in the database."}
          </p>
        </section>
      );
    }

    if (result.status !== "query_executed") {
      return (
        <section className="result-card error-card">
          <div className="result-header">
            <div className="result-title">
              <AlertCircle size={22} />
              <div>
                <h2>Query failed</h2>
                <p>QueryMind could not complete the request.</p>
              </div>
            </div>
          </div>

          <p className="reason-text">
            {result.error ||
              result.reason ||
              "An unexpected error occurred."}
          </p>
        </section>
      );
    }

    const rows = result.rows || [];

    return (
      <section className="result-card">
        <div className="result-header">
          <div className="result-title">
            <CheckCircle2 size={22} />
            <div>
              <h2>Query executed</h2>
              <p>
                {result.row_count ?? rows.length} result
                {result.row_count === 1 ? "" : "s"} returned.
              </p>
            </div>
          </div>

          <span className="status-badge success">
            Success
          </span>
        </div>

        {result.answer && (
          <div className="answer-box">
            <span className="answer-label">Answer</span>
            <p>{result.answer}</p>
          </div>
        )}

        {rows.length > 0 && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  {Object.keys(rows[0]).map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {Object.keys(rows[0]).map((column) => (
                      <td key={column}>
                        {String(row[column] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {result.sql && (
          <div className="sql-section">
            <button
              className="sql-toggle"
              onClick={() => setShowSql(!showSql)}
            >
              <span>
                <Database size={17} />
                Generated SQL
              </span>

              {showSql ? (
                <ChevronUp size={18} />
              ) : (
                <ChevronDown size={18} />
              )}
            </button>

            {showSql && (
              <pre className="sql-code">
                <code>{result.sql}</code>
              </pre>
            )}
          </div>
        )}
      </section>
    );
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Database size={22} />
          </div>

          <div>
            <h1>QueryMind AI</h1>
            <span>Enterprise Text-to-SQL Copilot</span>
          </div>
        </div>

        <div className="connection-status">
          <span className="status-dot" />
          API Ready
        </div>
      </header>

      <main className="main-content">
        <section className="hero">
          <span className="eyebrow">AI DATABASE COPILOT</span>

          <h2>
            Ask your database
            <br />
            <span>anything.</span>
          </h2>

          <p>
            QueryMind converts natural-language questions into
            validated SQL, executes them safely, and explains
            the results.
          </p>
        </section>

        <form className="query-form" onSubmit={submitQuestion}>
          <div className="input-container">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about your database..."
              rows={3}
              disabled={loading}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey
                ) {
                  event.preventDefault();
                  submitQuestion(event);
                }
              }}
            />

            <button
              type="submit"
              className="submit-button"
              disabled={loading || !question.trim()}
            >
              {loading ? (
                <Loader2 className="spin" size={19} />
              ) : (
                <Send size={19} />
              )}

              {loading ? "Thinking..." : "Ask QueryMind"}
            </button>
          </div>

          <span className="input-hint">
            Press Enter to submit · Shift + Enter for a new line
          </span>
        </form>

        {error && (
          <div className="global-error">
            <AlertCircle size={18} />
            {error}
          </div>
        )}

        {renderResult()}
      </main>

      <footer>
        <span>QueryMind AI</span>
        <span>Secure · Read-only · AI-powered</span>
      </footer>
    </div>
  );
}

export default App;