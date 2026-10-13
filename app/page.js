"use client";

import { useState, useEffect, useRef } from "react";
import { 
  FaCog, 
  FaFileUpload, 
  FaDownload, 
  FaTable, 
  FaChartBar, 
  FaTrash, 
  FaRobot, 
  FaDatabase, 
  FaCheckCircle, 
  FaExclamationTriangle,
  FaKey,
  FaFileAlt,
  FaTimes,
  FaEye,
  FaEyeSlash
} from "react-icons/fa";
import { BiSolidSend, BiRefresh, BiLinkExternal } from "react-icons/bi";
import BarChart from "./components/BarChart";

const DEFAULT_BACKEND_URL = "http://localhost:8000";

export default function Home() {
  // Chat state
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      agent: "conversation",
      text: "👋 Welcome to **RAGChat AI**! I am your agentic assistant for document intelligence and structured dataset curation. Ask me anything about your uploaded documents, or request a structured dataset extraction.",
      dataset: [],
      sources: [],
      steps: []
    }
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStepText, setActiveStepText] = useState("");

  // Modals
  const [showSettings, setShowSettings] = useState(false);
  const [showDocManager, setShowDocManager] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showAstraToken, setShowAstraToken] = useState(false);

  // Settings State (stored in localStorage)
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL);
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-flash");
  const [astraToken, setAstraToken] = useState("");
  const [astraEndpoint, setAstraEndpoint] = useState("");
  const [astraKeyspace, setAstraKeyspace] = useState("default_keyspace");
  const [collectionName, setCollectionName] = useState("pdf");

  // Status & Health
  const [systemStatus, setSystemStatus] = useState({
    gemini_configured: false,
    astra_connected: false,
    total_chunks: 0,
    documents: []
  });
  const [connectionTestMsg, setConnectionTestMsg] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);

  // Upload state
  const [uploadUrl, setUploadUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  const chatBottomRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load settings from localStorage
  useEffect(() => {
    try {
      const savedBackend = localStorage.getItem("rag_backend_url");
      const savedGeminiKey = localStorage.getItem("rag_gemini_api_key");
      const savedGeminiModel = localStorage.getItem("rag_gemini_model");
      const savedAstraToken = localStorage.getItem("rag_astra_token");
      const savedAstraEndpoint = localStorage.getItem("rag_astra_endpoint");
      const savedKeyspace = localStorage.getItem("rag_astra_keyspace");
      const savedCol = localStorage.getItem("rag_collection_name");

      if (savedBackend) setBackendUrl(savedBackend);
      if (savedGeminiKey) setGeminiApiKey(savedGeminiKey);
      if (savedGeminiModel) setGeminiModel(savedGeminiModel);
      if (savedAstraToken) setAstraToken(savedAstraToken);
      if (savedAstraEndpoint) setAstraEndpoint(savedAstraEndpoint);
      if (savedKeyspace) setAstraKeyspace(savedKeyspace);
      if (savedCol) setCollectionName(savedCol);
    } catch (e) {
      console.warn("Could not read from localStorage:", e);
    }
  }, []);

  // Fetch status on mount or backend change
  useEffect(() => {
    fetchSystemStatus();
  }, [backendUrl]);

  // Scroll to bottom when messages update
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const saveSettings = () => {
    try {
      localStorage.setItem("rag_backend_url", backendUrl);
      localStorage.setItem("rag_gemini_api_key", geminiApiKey);
      localStorage.setItem("rag_gemini_model", geminiModel);
      localStorage.setItem("rag_astra_token", astraToken);
      localStorage.setItem("rag_astra_endpoint", astraEndpoint);
      localStorage.setItem("rag_astra_keyspace", astraKeyspace);
      localStorage.setItem("rag_collection_name", collectionName);
      setConnectionTestMsg({ type: "success", text: "Settings saved to browser storage!" });
      fetchSystemStatus();
      setTimeout(() => setShowSettings(false), 800);
    } catch (e) {
      setConnectionTestMsg({ type: "error", text: "Failed to save settings: " + e.message });
    }
  };

  const getRequestHeaders = () => {
    const headers = {
      "Content-Type": "application/json"
    };
    if (geminiApiKey) headers["X-Gemini-Api-Key"] = geminiApiKey.trim();
    if (geminiModel) headers["X-Gemini-Model"] = geminiModel.trim();
    if (astraToken) headers["X-Astra-Token"] = astraToken.trim();
    if (astraEndpoint) headers["X-Astra-Endpoint"] = astraEndpoint.trim();
    if (astraKeyspace) headers["X-Astra-Keyspace"] = astraKeyspace.trim();
    if (collectionName) headers["X-Collection-Name"] = collectionName.trim();
    return headers;
  };

  const fetchSystemStatus = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/config`, {
        headers: getRequestHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setSystemStatus({
          gemini_configured: data.gemini_configured || Boolean(geminiApiKey),
          astra_connected: data.astra_connected,
          astra_status_message: data.astra_status_message,
          total_chunks: data.total_chunks || 0,
          documents: data.documents || []
        });
      }
    } catch (e) {
      console.warn("Backend not reachable at", backendUrl);
    }
  };

  const testConnection = async () => {
    setTestingConnection(true);
    setConnectionTestMsg(null);
    try {
      const res = await fetch(`${backendUrl}/api/config`, {
        headers: getRequestHeaders()
      });
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      setSystemStatus({
        gemini_configured: data.gemini_configured || Boolean(geminiApiKey),
        astra_connected: data.astra_connected,
        astra_status_message: data.astra_status_message,
        total_chunks: data.total_chunks || 0,
        documents: data.documents || []
      });
      setConnectionTestMsg({
        type: "success",
        text: `Connected! Backend online. Vector store has ${data.total_chunks} chunks across ${data.documents?.length || 0} documents.`
      });
    } catch (err) {
      setConnectionTestMsg({
        type: "error",
        text: `Could not connect to backend at ${backendUrl}: ${err.message}`
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const query = inputQuery.trim();
    if (!query || loading) return;

    // Append user message
    const newMessages = [...messages, { role: "user", text: query }];
    setMessages(newMessages);
    setInputQuery("");
    setLoading(true);
    setActiveStepText("Query Agent analyzing intent...");

    try {
      const response = await fetch(`${backendUrl}/api/chat`, {
        method: "POST",
        headers: getRequestHeaders(),
        body: JSON.stringify({
          query: query,
          config: {
            gemini_api_key: geminiApiKey,
            gemini_model: geminiModel,
            astra_api_token: astraToken,
            astra_endpoint: astraEndpoint,
            astra_keyspace: astraKeyspace,
            collection_name: collectionName
          }
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          agent: data.agent || "synthesis",
          text: data.message || data.prompt || "No response received.",
          dataset: data.dataset || [],
          sources: data.sources || [],
          steps: data.steps || [],
          validation: data.validation
        }
      ]);
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          agent: "error",
          text: `⚠️ Could not reach the backend server at \`${backendUrl}\`.\n\nMake sure the FastAPI server is running with: \`python backend/main.py\`\n\nError details: ${err.message}`,
          dataset: [],
          sources: [],
          steps: []
        }
      ]);
    } finally {
      setLoading(false);
      setActiveStepText("");
      fetchSystemStatus();
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadMessage(`Uploading & embedding ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const headers = {};
      if (geminiApiKey) headers["X-Gemini-Api-Key"] = geminiApiKey.trim();
      if (astraToken) headers["X-Astra-Token"] = astraToken.trim();
      if (astraEndpoint) headers["X-Astra-Endpoint"] = astraEndpoint.trim();

      const res = await fetch(`${backendUrl}/api/upload`, {
        method: "POST",
        headers,
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      setUploadMessage(`✅ Successfully embedded ${data.chunks_embedded} chunks from ${data.filename}!`);
      fetchSystemStatus();
    } catch (err) {
      setUploadMessage(`❌ Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async (e) => {
    e.preventDefault();
    const url = uploadUrl.trim();
    if (!url) return;

    setUploading(true);
    setUploadMessage(`Fetching & embedding content from ${url}...`);

    try {
      const res = await fetch(`${backendUrl}/api/url`, {
        method: "POST",
        headers: getRequestHeaders(),
        body: JSON.stringify({ url })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Ingestion failed`);
      }

      const data = await res.json();
      setUploadMessage(`✅ Successfully ingested ${data.chunks_embedded} chunks from URL!`);
      setUploadUrl("");
      fetchSystemStatus();
    } catch (err) {
      setUploadMessage(`❌ Ingestion failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleClearDocuments = async () => {
    if (!confirm("Are you sure you want to clear all documents from the vector store?")) return;
    try {
      await fetch(`${backendUrl}/api/documents`, {
        method: "DELETE",
        headers: getRequestHeaders()
      });
      fetchSystemStatus();
      setUploadMessage("Cleared all documents from vector store.");
    } catch (err) {
      alert("Failed to clear documents: " + err.message);
    }
  };

  const exportAsCSV = (dataset, filename = "dataset.csv") => {
    if (!dataset || dataset.length === 0) return;
    const headers = Object.keys(dataset[0]);
    const csvRows = [
      headers.join(","),
      ...dataset.map(row => 
        headers.map(h => {
          const val = row[h] === null || row[h] === undefined ? "" : String(row[h]);
          return `"${val.replace(/"/g, '""')}"`;
        }).join(",")
      )
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportAsJSON = (dataset, filename = "dataset.json") => {
    if (!dataset || dataset.length === 0) return;
    const blob = new Blob([JSON.stringify(dataset, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col h-screen bg-[#070b12] text-slate-200 overflow-hidden font-sans">
      
      {/* ================= HEADER ================= */}
      <header className="h-16 border-b border-slate-800/80 bg-[#0c121e]/90 backdrop-blur-md px-6 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <FaRobot className="text-white text-lg" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-lg text-white tracking-wide">RAGChat AI</h1>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Agentic RAG
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Interactive Multi-Agent Document Intelligence & Dataset Curation</p>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center gap-3">
          
          {/* Vector Store Count Pill */}
          <button 
            onClick={() => setShowDocManager(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-slate-800 border border-slate-700/60 text-xs transition-all hover:border-emerald-500/40"
            title="Click to manage documents"
          >
            <FaDatabase className={systemStatus.total_chunks > 0 ? "text-emerald-400" : "text-slate-500"} />
            <span className="font-mono text-slate-300 font-medium">
              {systemStatus.total_chunks} Chunks
            </span>
            <span className="text-[11px] text-slate-400">({systemStatus.documents.length} docs)</span>
          </button>

          {/* Gemini Key Status Pill */}
          <button
            onClick={() => setShowSettings(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              geminiApiKey || systemStatus.gemini_configured
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
                : "bg-amber-950/40 border-amber-500/40 text-amber-300 hover:bg-amber-900/50"
            }`}
          >
            <FaKey className="text-xs" />
            <span>
              {geminiApiKey || systemStatus.gemini_configured ? "Gemini Ready" : "Set API Key"}
            </span>
          </button>

          {/* Upload Documents Button */}
          <button
            onClick={() => setShowDocManager(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-white transition-all shadow-sm"
          >
            <FaFileUpload className="text-emerald-400" />
            <span className="hidden md:inline">Documents</span>
          </button>

          {/* Settings Modal Toggle */}
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700/80 text-slate-300 hover:text-white transition-all"
            title="API & System Settings"
          >
            <FaCog className="text-base" />
          </button>
        </div>
      </header>

      {/* ================= CHAT CONTAINER ================= */}
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-12 lg:px-24 max-w-6xl w-full mx-auto space-y-6">
        
        {/* Quick Suggestion Chips if only initial greeting */}
        {messages.length === 1 && (
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 mb-4 backdrop-blur-sm">
            <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              Try a sample query on the indexed documents:
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                "What are the main fitness recommendations in the handbook?",
                "Extract all workout test benchmarks into a structured dataset",
                "Summarize cardiovascular fitness guidelines",
                "Create a structured table of fitness components and measurements"
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setInputQuery(suggestion);
                  }}
                  className="text-left text-xs p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/40 hover:border-emerald-500/40 text-slate-300 hover:text-white transition-all"
                >
                  &ldquo;{suggestion}&rdquo;
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Stream */}
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} space-y-2`}
          >
            {/* Sender / Agent Label */}
            <div className="flex items-center gap-2 px-1 text-xs text-slate-400">
              {msg.role === "user" ? (
                <span className="font-medium text-slate-300">You</span>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-emerald-400 capitalize">
                    {msg.agent === "conversation" ? "ConversationAgent" : `${msg.agent || "Synthesis"}Agent`}
                  </span>
                  {msg.agent && msg.agent !== "conversation" && (
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded border border-slate-700">
                      Multi-Agent Pipeline
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[90%] md:max-w-[80%] rounded-2xl px-5 py-3.5 shadow-md text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-br-none"
                  : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none"
              }`}
            >
              {/* Formatted Text */}
              <div className="whitespace-pre-wrap font-sans">
                {msg.text}
              </div>

              {/* Multi-Agent Steps Trace (Collapsible) */}
              {msg.steps && msg.steps.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800 text-xs">
                  <details className="group">
                    <summary className="cursor-pointer text-slate-400 hover:text-emerald-400 font-medium flex items-center gap-1.5 select-none">
                      <span>Pipeline execution trace ({msg.steps.length} steps)</span>
                    </summary>
                    <div className="mt-2 space-y-1.5 pl-2 border-l border-slate-700">
                      {msg.steps.map((step, sIdx) => (
                        <div key={sIdx} className="flex items-start gap-2 text-slate-300">
                          <span className="text-emerald-400 font-mono text-[11px] font-semibold">{step.agent}:</span>
                          <span className="text-slate-400">{step.description}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}

              {/* Structured Dataset Visualizer */}
              {msg.dataset && msg.dataset.length > 0 && (
                <DatasetViewer
                  dataset={msg.dataset}
                  onExportCSV={() => exportAsCSV(msg.dataset, `rag_dataset_${index}.csv`)}
                  onExportJSON={() => exportAsJSON(msg.dataset, `rag_dataset_${index}.json`)}
                />
              )}

              {/* Source Document References */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800 text-xs">
                  <details className="group">
                    <summary className="cursor-pointer text-slate-400 hover:text-emerald-400 font-medium flex items-center gap-1.5 select-none">
                      <span>Retrieved source evidence ({msg.sources.length} chunks)</span>
                    </summary>
                    <div className="mt-2 space-y-2">
                      {msg.sources.map((src, srcIdx) => (
                        <div key={srcIdx} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                            <span className="font-semibold text-emerald-300 font-mono flex items-center gap-1">
                              <FaFileAlt /> {src.filename}
                            </span>
                            {src.score && (
                              <span className="text-[10px] bg-slate-800 px-1 rounded text-slate-400 font-mono">
                                Match: {Math.round(src.score * 100)}%
                              </span>
                            )}
                          </div>
                          <p className="text-slate-300 text-xs font-mono line-clamp-3 bg-black/20 p-1.5 rounded">
                            {src.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}

            </div>
          </div>
        ))}

        {/* Loading Spinner with Agent Steps */}
        {loading && (
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-900 border border-slate-800 w-fit">
            <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
            <div className="flex flex-col text-xs">
              <span className="font-semibold text-white">Multi-Agent System Processing...</span>
              <span className="text-slate-400">{activeStepText || "Orchestrating agents..."}</span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* ================= INPUT FOOTER ================= */}
      <footer className="p-4 md:px-12 lg:px-24 border-t border-slate-800/80 bg-[#0c121e]/95 backdrop-blur-md shrink-0">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex items-center gap-2">
          
          {/* Quick File Attach */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-3 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all shrink-0"
            title="Upload file to index"
          >
            <FaFileUpload className="text-base" />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
            className="hidden"
            accept=".pdf,.txt,.csv,.json,.png,.jpg,.jpeg"
          />

          {/* Text Input */}
          <div className="relative flex-1">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a question or request structured data (e.g. 'Extract all fitness standards table')..."
              className="w-full py-3.5 pl-4 pr-12 rounded-xl bg-slate-900/90 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all shadow-inner"
            />
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!inputQuery.trim() || loading}
            className="p-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white font-semibold transition-all shrink-0 shadow-lg shadow-emerald-600/20"
          >
            <BiSolidSend className="text-lg" />
          </button>
        </form>

        <div className="max-w-4xl mx-auto flex items-center justify-between text-[11px] text-slate-500 mt-2 px-1">
          <span>Backend: <code className="text-slate-400 font-mono">{backendUrl}</code></span>
          <span>Tip: Click ⚙️ Settings anytime to configure Gemini or Astra DB</span>
        </div>
      </footer>

      {/* ================= SETTINGS MODAL ================= */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-700 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FaCog className="text-emerald-400 text-lg" />
                <h3 className="font-semibold text-white text-base">API & System Settings</h3>
              </div>
              <button 
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5 overflow-y-auto flex-1 text-xs">
              
              {/* Notice Banner */}
              <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 leading-relaxed">
                <span className="font-semibold">💡 Configurable Inputs:</span> API keys entered here are stored safely in your browser session and transmitted directly to the backend. You can also configure them via the <code className="bg-black/30 px-1 py-0.5 rounded font-mono">.env</code> file.
              </div>

              {/* 1. Google Gemini API Key */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="font-medium text-slate-200 flex items-center gap-1.5">
                    <FaKey className="text-emerald-400" /> Google Gemini API Key
                  </label>
                  <a
                    href="https://aistudio.google.com/"
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center gap-1"
                  >
                    Get Free Key <BiLinkExternal />
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showApiKey ? "text" : "password"}
                    value={geminiApiKey}
                    onChange={(e) => setGeminiApiKey(e.target.value)}
                    placeholder="AIzaSy..."
                    className="w-full py-2.5 px-3 pr-10 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-200"
                  >
                    {showApiKey ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400">
                  Required for full Gemini LLM multi-agent reasoning, data synthesis, and embeddings.
                </p>
              </div>

              {/* Gemini Model Selection */}
              <div className="space-y-1.5">
                <label className="font-medium text-slate-200">Gemini Model</label>
                <select
                  value={geminiModel}
                  onChange={(e) => setGeminiModel(e.target.value)}
                  className="w-full py-2.5 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
                >
                  <option value="gemini-1.5-flash">gemini-1.5-flash (Fast & Recommended)</option>
                  <option value="gemini-2.0-flash">gemini-2.0-flash (Next-Gen Flash)</option>
                  <option value="gemini-1.5-pro">gemini-1.5-pro (High Reasoning)</option>
                </select>
              </div>

              {/* 2. DataStax Astra DB Vector Settings */}
              <div className="pt-2 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <FaDatabase className="text-teal-400" /> DataStax Astra DB (Optional)
                  </label>
                  <a
                    href="https://astra.datastax.com/"
                    target="_blank"
                    rel="noreferrer"
                    className="text-teal-400 hover:underline flex items-center gap-1"
                  >
                    Astra Console <BiLinkExternal />
                  </a>
                </div>
                <p className="text-[11px] text-slate-400">
                  If Astra DB is not configured, RAGChat automatically uses a high-performance in-memory and local file vector store.
                </p>

                <div className="space-y-1.5">
                  <label className="text-slate-300">Astra Application Token</label>
                  <div className="relative">
                    <input
                      type={showAstraToken ? "text" : "password"}
                      value={astraToken}
                      onChange={(e) => setAstraToken(e.target.value)}
                      placeholder="AstraCS:..."
                      className="w-full py-2.5 px-3 pr-10 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-teal-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowAstraToken(!showAstraToken)}
                      className="absolute right-3 top-3 text-slate-400 hover:text-slate-200"
                    >
                      {showAstraToken ? <FaEyeSlash /> : <FaEye />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300">Astra API Endpoint</label>
                  <input
                    type="text"
                    value={astraEndpoint}
                    onChange={(e) => setAstraEndpoint(e.target.value)}
                    placeholder="https://<id>-<region>.apps.astra.datastax.com"
                    className="w-full py-2.5 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-teal-500 font-mono"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-slate-300">Keyspace</label>
                    <input
                      type="text"
                      value={astraKeyspace}
                      onChange={(e) => setAstraKeyspace(e.target.value)}
                      placeholder="default_keyspace"
                      className="w-full py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-slate-300">Collection</label>
                    <input
                      type="text"
                      value={collectionName}
                      onChange={(e) => setCollectionName(e.target.value)}
                      placeholder="pdf"
                      className="w-full py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* 3. Backend API URL */}
              <div className="pt-2 border-t border-slate-800 space-y-1.5">
                <label className="font-medium text-slate-200">Backend API URL</label>
                <input
                  type="text"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  className="w-full py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 font-mono"
                />
              </div>

              {/* Connection Status feedback */}
              {connectionTestMsg && (
                <div className={`p-3 rounded-lg text-xs ${
                  connectionTestMsg.type === "success" 
                    ? "bg-emerald-950/60 border border-emerald-500/40 text-emerald-300"
                    : "bg-rose-950/60 border border-rose-500/40 text-rose-300"
                }`}>
                  {connectionTestMsg.text}
                </div>
              )}

            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-800 bg-[#090d16] flex items-center justify-between">
              <button
                type="button"
                onClick={testConnection}
                disabled={testingConnection}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs flex items-center gap-1.5 transition-all"
              >
                <BiRefresh className={testingConnection ? "animate-spin text-base" : "text-base"} />
                {testingConnection ? "Testing..." : "Test Connection"}
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={saveSettings}
                  className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
                >
                  Save Settings
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ================= DOCUMENT MANAGER MODAL ================= */}
      {showDocManager && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FaDatabase className="text-emerald-400 text-lg" />
                <h3 className="font-semibold text-white text-base">Document Ingestion & Vector Store</h3>
              </div>
              <button 
                onClick={() => setShowDocManager(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <FaTimes />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
              
              {/* File Upload Zone */}
              <div className="space-y-2">
                <label className="font-semibold text-slate-200">Upload Files to Vector Store</label>
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
                  }}
                  className="border-2 border-dashed border-slate-700 hover:border-emerald-500 bg-slate-900/60 hover:bg-slate-900 rounded-2xl p-6 text-center cursor-pointer transition-all"
                >
                  <FaFileUpload className="text-3xl text-emerald-400 mx-auto mb-2" />
                  <p className="font-medium text-slate-200">Click or drag & drop documents here</p>
                  <p className="text-[11px] text-slate-400 mt-1">Supports PDF, TXT, CSV, JSON, PNG, JPG (Auto-chunked & embedded)</p>
                </div>
              </div>

              {/* URL Ingestion */}
              <div className="space-y-2">
                <label className="font-semibold text-slate-200">Ingest Webpage URL</label>
                <form onSubmit={handleUrlUpload} className="flex gap-2">
                  <input
                    type="url"
                    value={uploadUrl}
                    onChange={(e) => setUploadUrl(e.target.value)}
                    placeholder="https://example.com/documentation"
                    className="flex-1 py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                  />
                  <button
                    type="submit"
                    disabled={uploading || !uploadUrl.trim()}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-medium text-xs border border-slate-700 transition-all shrink-0"
                  >
                    Ingest URL
                  </button>
                </form>
              </div>

              {/* Upload Status Notification */}
              {uploadMessage && (
                <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200 font-medium">
                  {uploadMessage}
                </div>
              )}

              {/* Current Indexed Documents List */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <span>Indexed Documents in Vector Store</span>
                    <span className="text-slate-400 font-normal">({systemStatus.documents.length})</span>
                  </label>
                  {systemStatus.documents.length > 0 && (
                    <button
                      onClick={handleClearDocuments}
                      className="text-rose-400 hover:text-rose-300 text-[11px] flex items-center gap-1 transition-all"
                    >
                      <FaTrash /> Clear All Documents
                    </button>
                  )}
                </div>

                {systemStatus.documents.length === 0 ? (
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400">
                    No documents indexed yet. Upload a PDF or file above to get started!
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {systemStatus.documents.map((doc, idx) => (
                      <div key={idx} className="p-3 rounded-xl bg-slate-900 border border-slate-800/80 flex items-center justify-between">
                        <div className="flex items-center gap-2.5 overflow-hidden">
                          <FaFileAlt className="text-emerald-400 shrink-0 text-sm" />
                          <div className="truncate">
                            <span className="font-mono text-slate-200 font-medium block truncate">{doc.filename}</span>
                            <span className="text-[10px] text-slate-500 uppercase">{doc.type}</span>
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <span className="px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-500/30 text-emerald-400 font-mono text-[11px] font-semibold">
                            {doc.chunks} chunks
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-800 bg-[#090d16] flex justify-end">
              <button
                onClick={() => setShowDocManager(false)}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-all"
              >
                Close
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

// ================= DATASET VIEWER SUB-COMPONENT =================
function DatasetViewer({ dataset, onExportCSV, onExportJSON }) {
  const [viewMode, setViewMode] = useState("table"); // 'table' | 'chart' | 'json'

  if (!dataset || dataset.length === 0) return null;

  const headers = Object.keys(dataset[0]);

  return (
    <div className="mt-4 pt-3 border-t border-slate-800 space-y-3">
      
      {/* Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setViewMode("table")}
            className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              viewMode === "table" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            <FaTable /> Table ({dataset.length} rows)
          </button>
          <button
            onClick={() => setViewMode("chart")}
            className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              viewMode === "chart" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            <FaChartBar /> Chart
          </button>
          <button
            onClick={() => setViewMode("json")}
            className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              viewMode === "json" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Raw JSON
          </button>
        </div>

        {/* Download Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onExportCSV}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm"
          >
            <FaDownload /> Export CSV
          </button>
          <button
            onClick={onExportJSON}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm"
          >
            <FaDownload /> Export JSON
          </button>
        </div>
      </div>

      {/* Table View */}
      {viewMode === "table" && (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 max-h-72">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-900 sticky top-0 border-b border-slate-800 text-slate-300 font-semibold font-mono">
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="px-3.5 py-2.5 capitalize">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {dataset.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-slate-900/60 transition-colors">
                  {headers.map((h, cIdx) => (
                    <td key={cIdx} className="px-3.5 py-2 text-slate-300">
                      {row[h] !== null && row[h] !== undefined ? String(row[h]) : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Chart View */}
      {viewMode === "chart" && (
        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex justify-center">
          <BarChart data={dataset} />
        </div>
      )}

      {/* JSON View */}
      {viewMode === "json" && (
        <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-emerald-400 overflow-x-auto max-h-64">
          {JSON.stringify(dataset, null, 2)}
        </pre>
      )}

    </div>
  );
}
