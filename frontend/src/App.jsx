import "./App.css";

import { useEffect, useMemo, useState, Component } from "react";
import axios from "axios";

import {
  Database,
  History,
  Send,
  Loader2,
  ChevronRight,
  X,
  Copy,
  Check,
  BarChart3,
} from "lucide-react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const API_KEY =
  import.meta.env.VITE_API_KEY || "";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "X-API-Key": API_KEY,
  },
});


// ============================================================
// ERROR BOUNDARY
// ============================================================

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          gap: "12px",
          color: "#f0a3ad",
          background: "#080b12",
          padding: "24px",
          textAlign: "center",
        }}>
          <X size={32} />
          <h2 style={{ margin: 0, color: "#e5e7eb" }}>Something went wrong</h2>
          <p style={{ margin: 0, color: "#7f8ba0", fontSize: "13px" }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: "8px",
              padding: "9px 18px",
              border: "1px solid #35445a",
              borderRadius: "8px",
              background: "#172033",
              color: "#e8edf5",
              cursor: "pointer",
              fontSize: "13px",
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}


function App() {

  // ============================================================
  // QUERY STATE
  // ============================================================

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const [response, setResponse] = useState(null);

  const [conversationId, setConversationId] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [options, setOptions] = useState([]);

  // ============================================================
  // HISTORY STATE
  // ============================================================

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [selectedHistory, setSelectedHistory] = useState(null);

  // ============================================================
  // UI STATE
  // ============================================================

  const [copied, setCopied] = useState(false);
  const [sqlOpen, setSqlOpen] = useState(false);


  // ============================================================
  // LOAD QUERY HISTORY
  // ============================================================

  const loadHistory = async () => {

    try {

      setHistoryLoading(true);

      const result = await api.get(
        `/query/history?limit=20`
      );

      setHistory(result.data.items || []);

    } catch (error) {

      console.error(
        "Failed to load query history:",
        error
      );

    } finally {

      setHistoryLoading(false);

    }
  };


  useEffect(() => {
    loadHistory();
  }, []);


  // ============================================================
  // RESET QUERY STATE
  // ============================================================

  const resetQueryState = () => {

    setResponse(null);
    setConversationId(null);
    setClarification(null);
    setOptions([]);
    setSelectedHistory(null);
    setCopied(false);
    setSqlOpen(false);

  };


  // ============================================================
  // SUBMIT QUERY
  // ============================================================

  const submitQuery = async () => {

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || loading) {
      return;
    }

    setLoading(true);

    resetQueryState();

    try {

      const result = await api.post(
        `/query/`,
        {
          question: trimmedQuestion,
        }
      );

      const data = result.data;

      setResponse(data);

      if (data.status === "clarification_required") {

        setConversationId(
          data.conversation_id
        );

        setClarification(
          data.question ||
          data.clarification
        );

        setOptions(
          data.options || []
        );

      }

      await loadHistory();

    } catch (error) {

      console.error(
        "Query failed:",
        error
      );

      setResponse({
        status: "error",
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          "Unable to process the query.",
      });

    } finally {

      setLoading(false);

    }
  };


  // ============================================================
  // SUBMIT CLARIFICATION
  // ============================================================

  const submitClarification = async (answer) => {

    if (
      !conversationId ||
      loading ||
      !answer?.trim()
    ) {
      return;
    }

    setLoading(true);

    try {

      const result = await api.post(
        `/query/clarify`,
        {
          conversation_id: conversationId,
          answer: answer.trim(),
        }
      );

      const data = result.data;

      setResponse(data);

      setClarification(null);
      setOptions([]);
      setConversationId(null);

      setSqlOpen(false);

      await loadHistory();

    } catch (error) {

      console.error(
        "Clarification failed:",
        error
      );

      setResponse({
        status: "error",
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          "Unable to process the clarification.",
      });

    } finally {

      setLoading(false);

    }
  };


  // ============================================================
  // HISTORY ITEM
  // ============================================================

  const openHistory = (item) => {

    setSelectedHistory(item);

    if (
      item.question ||
      item.original_question
    ) {

      setQuestion(
        item.question ||
        item.original_question ||
        ""
      );

    }

    // If the history API already returns the
    // complete result, display it immediately.
    if (
      item.answer ||
      item.sql ||
      item.rows
    ) {

      setResponse({
        ...item,
        status:
          item.status ||
          "query_executed",
      });

      setClarification(null);
      setOptions([]);
      setConversationId(null);
      setSqlOpen(false);

    }

  };


  // ============================================================
  // COPY SQL
  // ============================================================

  const copySql = async (sql) => {

    if (!sql) {
      return;
    }

    try {

      await navigator.clipboard.writeText(sql);

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 1500);

    } catch (error) {

      console.error(
        "Failed to copy SQL:",
        error
      );

    }
  };


  // ============================================================
  // FORMAT DATE
  // ============================================================

  const formatDate = (value) => {

    if (!value) {
      return "";
    }

    try {

      return new Date(value).toLocaleString();

    } catch {

      return value;

    }
  };


  // ============================================================
  // STATUS LABEL
  // ============================================================

  const getStatusLabel = (status) => {

    switch (status) {

      case "completed":
        return "Completed";

      case "query_executed":
        return "Executed";

      case "clarification_required":
        return "Clarification";

      case "unsupported":
        return "Unsupported";

      case "error":
        return "Error";

      default:
        return status || "Unknown";

    }
  };


  // ============================================================
  // SUCCESS RESULT
  // ============================================================

  const isSuccessfulResult =
    response &&
    (
      response.status === "completed" ||
      response.status === "query_executed"
    );


  // ============================================================
  // CHART DATA
  // ============================================================

  const chartConfig = useMemo(() => {

    if (
      !response?.rows ||
      response.rows.length === 0
    ) {
      return null;
    }

    const rows = response.rows;

    const firstRow = rows[0];

    const columns = Object.keys(firstRow);

    const labelColumn =
      columns.find((column) =>
        [
          "product_name",
          "category_name",
          "store_name",
          "region_name",
          "customer_name",
          "month",
          "date",
          "order_date",
        ].includes(column)
      ) ||
      columns.find(
        (column) =>
          typeof firstRow[column] === "string"
      );

    if (!labelColumn) {
      return null;
    }

    const numericColumns =
      columns.filter(
        (column) =>
          column !== labelColumn &&
          rows.some(
            (row) =>
              typeof row[column] === "number"
          )
      );

    if (numericColumns.length === 0) {
      return null;
    }

    const valueColumn =
      numericColumns.find(
        (column) =>
          column === "revenue"
      ) ||
      numericColumns.find(
        (column) =>
          column === "total_revenue"
      ) ||
      numericColumns.find(
        (column) =>
          column === "units_sold"
      ) ||
      numericColumns.find(
        (column) =>
          column === "quantity"
      ) ||
      numericColumns[0];

    const chartRows =
      rows
        .map((row) => ({
          label: String(
            row[labelColumn] ?? ""
          ),
          value:
            Number(row[valueColumn]) || 0,
        }))
        .slice(0, 20);

    return {
      labelColumn,
      valueColumn,
      data: chartRows,
    };

  }, [response]);


  // ============================================================
  // RENDER
  // ============================================================

  return (

    <div className="app">

      {/* ======================================================
          TOPBAR
      ====================================================== */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-icon">
            <Database size={21} />
          </div>

          <div>
            <h1>QueryMind</h1>
            <span>AI DATA COPILOT</span>
          </div>

        </div>


        <div className="connection-status">

          <span className="status-dot" />

          Database connected

        </div>

      </header>


      {/* ======================================================
          WORKSPACE
      ====================================================== */}

      <div className="workspace">


        {/* ====================================================
            HISTORY SIDEBAR
        ==================================================== */}

        <aside className="history-sidebar">

          <div className="history-heading">

            <History size={15} />

            <span>
              QUERY HISTORY
            </span>

          </div>


          {historyLoading ? (

            <div className="history-empty">
              Loading history...
            </div>

          ) : history.length === 0 ? (

            <div className="history-empty">
              No queries yet.
            </div>

          ) : (

            <div className="history-list">

              {history.map(
                (item, index) => {

                  const historyQuestion =
                    item.question ||
                    item.original_question ||
                    "Untitled query";

                  const historyStatus =
                    item.status ||
                    "unknown";

                  return (

                    <button
                      key={
                        item.id ||
                        item.history_id ||
                        item.conversation_id ||
                        index
                      }
                      className="history-item"
                      onClick={() =>
                        openHistory(item)
                      }
                    >

                      <div className="history-question">

                        {historyQuestion}

                      </div>


                      <div className="history-meta">

                        <span
                          className={
                            `history-status ${historyStatus}`
                          }
                        >
                          {getStatusLabel(
                            historyStatus
                          )}
                        </span>


                        <span className="history-arrow">

                          <ChevronRight
                            size={14}
                          />

                        </span>

                      </div>


                      {(
                        item.created_at ||
                        item.timestamp
                      ) && (

                        <div className="history-date">

                          {formatDate(
                            item.created_at ||
                            item.timestamp
                          )}

                        </div>

                      )}

                    </button>

                  );

                }
              )}

            </div>

          )}

        </aside>


        {/* ====================================================
            PAGE CONTENT
        ==================================================== */}

        <div className="page-content">


          {/* ==================================================
              MAIN
          ================================================== */}

          <main className="main-content">


            {/* ================================================
                HERO
            ================================================= */}

            <section className="hero">

              <div className="eyebrow">
                ENTERPRISE TEXT-TO-SQL
              </div>


              <h2>

                Ask your data.

                <br />

                <span>
                  Get answers.
                </span>

              </h2>


              <p>

                Query your database using natural language.
                QueryMind retrieves relevant schema context,
                generates validated SQL, executes it safely,
                and explains the result.

              </p>

            </section>


            {/* ================================================
                QUERY FORM
            ================================================= */}

            <section className="query-form">

              <div className="input-container">

                <textarea
                  value={question}
                  placeholder="Ask something like: What are the top 5 products by revenue?"
                  onChange={(event) =>
                    setQuestion(
                      event.target.value
                    )
                  }
                  onKeyDown={(event) => {

                    if (
                      event.key === "Enter" &&
                      !event.shiftKey
                    ) {

                      event.preventDefault();

                      submitQuery();

                    }

                  }}
                  disabled={loading}
                />


                <button
                  className="submit-button"
                  onClick={submitQuery}
                  disabled={
                    loading ||
                    !question.trim()
                  }
                >

                  {loading ? (

                    <>
                      <Loader2
                        size={16}
                        className="spin"
                      />

                      Running...
                    </>

                  ) : (

                    <>
                      <Send size={16} />

                      Run Query
                    </>

                  )}

                </button>

              </div>


              <span className="input-hint">

                Press Enter to run ·
                Shift + Enter for a new line

              </span>

              <p className="demo-notice">
                Demo may take a moment to start after inactivity.
              </p>

            </section>


            {/* ================================================
                CLARIFICATION
            ================================================= */}

            {clarification && (

              <section className="result-card">

                <div className="result-header">

                  <div className="result-title">

                    <ChevronRight size={18} />

                    <div>

                      <h2>
                        Clarification required
                      </h2>

                      <p>
                        Help QueryMind understand your intent.
                      </p>

                    </div>

                  </div>


                  <span className="status-badge clarification">

                    Clarification

                  </span>

                </div>


                <div className="clarification-content">

                  <p className="clarification-question">

                    {clarification}

                  </p>


                  {options.length > 0 && (

                    <div className="clarification-options">

                      {options.map(
                        (option, index) => (

                          <button
                            key={index}
                            className="option-button"
                            onClick={() =>
                              submitClarification(
                                option.label ||
                                option
                              )
                            }
                            disabled={loading}
                          >

                            <strong>

                              {option.label ||
                                option}

                            </strong>


                            {option.description && (

                              <span>

                                {option.description}

                              </span>

                            )}

                          </button>

                        )
                      )}

                    </div>

                  )}


                  {options.length === 0 && (

                    <div className="clarification-form">

                      <input
                        type="text"
                        placeholder="Type your clarification..."
                        disabled={loading}
                        onKeyDown={(event) => {

                          if (
                            event.key === "Enter" &&
                            event.target.value.trim()
                          ) {

                            submitClarification(
                              event.target.value.trim()
                            );

                            event.target.value = "";

                          }

                        }}
                      />

                    </div>

                  )}

                </div>

              </section>

            )}


            {/* ================================================
                ERROR
            ================================================= */}

            {response?.status === "error" && (

              <div className="global-error">

                <X size={18} />

                <span>

                  {response.error ||
                    "An unexpected error occurred."}

                </span>

              </div>

            )}


            {/* ================================================
                UNSUPPORTED
            ================================================= */}

            {response?.status === "unsupported" && (

              <section className="result-card error-card">

                <div className="result-header">

                  <div className="result-title">

                    <X size={18} />

                    <div>

                      <h2>
                        Query not supported
                      </h2>

                      <p>
                        QueryMind could not answer this question.
                      </p>

                    </div>

                  </div>


                  <span className="status-badge unsupported">

                    Unsupported

                  </span>

                </div>


                <p className="reason-text">

                  {response.reason}

                </p>

              </section>

            )}


            {/* ================================================
                SUCCESS RESULT
            ================================================= */}

            {isSuccessfulResult && (

              <section className="result-card">


                {/* RESULT HEADER */}

                <div className="result-header">

                  <div className="result-title">

                    <BarChart3 size={18} />

                    <div>

                      <h2>
                        Query result
                      </h2>

                      <p>

                        {response.question ||
                          response.original_question ||
                          question}

                      </p>

                    </div>

                  </div>


                  <span className="status-badge success">

                    Completed

                  </span>

                </div>


                {/* ANSWER */}

                {response.answer && (

                  <div className="answer-box">

                    <span className="answer-label">

                      Answer

                    </span>


                    <p>

                      {response.answer}

                    </p>

                  </div>

                )}


                {/* METRICS */}

                <div className="result-metrics">

                  <div className="metric-card">

                    <div className="metric-label">
                      Rows
                    </div>

                    <div className="metric-value">

                      {response.row_count ?? 0}

                      {response.row_count >= 100 && (
                        <span className="metric-capped">
                          &nbsp;(capped at 100)
                        </span>
                      )}

                    </div>

                  </div>


                  <div className="metric-card">

                    <div className="metric-label">
                      SQL
                    </div>

                    <div className="metric-value">

                      {response.sql
                        ? "Generated"
                        : "—"}

                    </div>

                  </div>


                  <div className="metric-card">

                    <div className="metric-label">
                      Status
                    </div>

                    <div className="metric-value">

                      Ready

                    </div>

                  </div>

                </div>


                {/* CHART */}

                {chartConfig && (

                  <div className="chart-section">

                    <div className="chart-header">

                      <div>

                        <div className="chart-title">
                          Visualization
                        </div>

                        <div className="chart-subtitle">

                          {chartConfig.valueColumn}
                          {" "}by{" "}
                          {chartConfig.labelColumn}

                        </div>

                      </div>

                    </div>


                    <div className="chart-container">

                      <ResponsiveContainer
                        width="100%"
                        height="100%"
                      >

                        <BarChart
                          data={chartConfig.data}
                          margin={{
                            top: 10,
                            right: 20,
                            left: 10,
                            bottom: 50,
                          }}
                        >

                          <CartesianGrid
                            strokeDasharray="3 3"
                          />

                          <XAxis
                            dataKey="label"
                            angle={-35}
                            textAnchor="end"
                            interval={0}
                            height={70}
                          />

                          <YAxis />

                          <Tooltip />

                          <Bar
                            dataKey="value"
                            name={
                              chartConfig.valueColumn
                            }
                            radius={[
                              5,
                              5,
                              0,
                              0,
                            ]}
                          />

                        </BarChart>

                      </ResponsiveContainer>

                    </div>

                  </div>

                )}


                {/* TABLE */}

                {response.rows &&
                  response.rows.length > 0 && (

                    <div className="table-wrapper">

                      <table>

                        <thead>

                          <tr>

                            {Object.keys(
                              response.rows[0]
                            ).map(
                              (column) => (

                                <th key={column}>

                                  {column}

                                </th>

                              )
                            )}

                          </tr>

                        </thead>


                        <tbody>

                          {response.rows.map(
                            (row, rowIndex) => (

                              <tr key={rowIndex}>

                                {Object.keys(
                                  response.rows[0]
                                ).map(
                                  (column) => (

                                    <td key={column}>

                                      {row[column] === null
                                        ? "NULL"
                                        : String(
                                            row[column]
                                          )}

                                    </td>

                                  )
                                )}

                              </tr>

                            )
                          )}

                        </tbody>

                      </table>

                    </div>

                  )}


                {/* SQL */}

                {response.sql && (

                  <div className="sql-section">

                    <div className="sql-header">

                      <button
                        className="sql-toggle"
                        onClick={() =>
                          setSqlOpen(
                            (previous) =>
                              !previous
                          )
                        }
                      >

                        <span>

                          <Database size={14} />

                          Generated SQL

                        </span>


                        <span className="sql-actions">

                          {sqlOpen
                            ? "Hide"
                            : "Show"}

                        </span>

                      </button>


                      <button
                        className="sql-copy-button"
                        onClick={() =>
                          copySql(
                            response.sql
                          )
                        }
                      >

                        {copied ? (

                          <>
                            <Check size={13} />
                            Copied
                          </>

                        ) : (

                          <>
                            <Copy size={13} />
                            Copy
                          </>

                        )}

                      </button>

                    </div>


                    {sqlOpen && (

                      <pre className="sql-code">

                        {response.sql}

                      </pre>

                    )}

                  </div>

                )}

              </section>

            )}

          </main>


          {/* ==================================================
              FOOTER
          ================================================== */}

          <footer>

            <span>
              QueryMind AI
            </span>

            <span>
              Secure read-only database intelligence
            </span>

          </footer>

        </div>

      </div>

    </div>

  );
}


export default function WrappedApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}