import { useEffect, useState } from "react";

import { motion } from "framer-motion";

import {
  Send,
  Fish,
  LogOut,
  Plus,
  MessageCircle,
  Menu,
  X,
  Sparkles,
  Droplets,
  Utensils,
  Stethoscope,
  Waves,
  Trash2,
} from "lucide-react";

import { BRAND_NAME } from "./brand";
import AnswerText from "./components/AnswerText";
import {
  AmbientBackground,
  BrandMark,
  PhotoBackdrop,
  PhotoBanner,
  VeltrisCredit,
  WaterOrb,
} from "./components/Brand";
import { PHOTOS } from "./photos";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


function App() {
  // ==========================================================
  // STATE
  // ==========================================================

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [showSignup, setShowSignup] = useState(false);

  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");

  const [question, setQuestion] = useState("");

  const [messages, setMessages] = useState([]);

  const [history, setHistory] = useState([]);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [sidebarOpen, setSidebarOpen] = useState(
    () => window.matchMedia("(min-width: 768px)").matches
  );

  // Currently selected conversation
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  // Current conversation UUID
  const [conversationId, setConversationId] = useState(null);


  // ==========================================================
  // SAVE AUTH SESSION
  // ==========================================================

  function saveAuthSession(data) {
    if (data.access_token) {
      localStorage.setItem(
        "meenamitra_token",
        data.access_token
      );
    }

    if (data.refresh_token) {
      localStorage.setItem(
        "meenamitra_refresh_token",
        data.refresh_token
      );
    }

    if (data.email) {
      localStorage.setItem(
        "meenamitra_email",
        data.email
      );
    }
  }


  // ==========================================================
  // CLEAR AUTH SESSION
  // ==========================================================

  function clearAuthSession() {
    localStorage.removeItem(
      "meenamitra_token"
    );

    localStorage.removeItem(
      "meenamitra_refresh_token"
    );

    localStorage.removeItem(
      "meenamitra_email"
    );
  }


  // ==========================================================
  // REFRESH ACCESS TOKEN
  // ==========================================================

  async function refreshAccessToken() {
    const refreshToken =
      localStorage.getItem(
        "meenamitra_refresh_token"
      );

    if (!refreshToken) {
      return null;
    }

    try {
      const response = await fetch(
        `${API_URL}/refresh`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        clearAuthSession();
        return null;
      }

      saveAuthSession(data);

      return data.access_token;
    }

    catch (err) {
      console.error(
        "Token refresh error:",
        err
      );

      return null;
    }
  }


  // ==========================================================
  // AUTHENTICATED FETCH
  //
  // Automatically retries once after
  // an expired access token.
  // ==========================================================

  async function authenticatedFetch(
    url,
    options = {}
  ) {
    let token =
      localStorage.getItem(
        "meenamitra_token"
      );

    if (!token) {
      throw new Error(
        "Please login first."
      );
    }

    const firstOptions = {
      ...options,

      headers: {
        ...(options.headers || {}),

        Authorization:
          `Bearer ${token}`,
      },
    };

    let response =
      await fetch(
        url,
        firstOptions
      );

    // --------------------------------------------------------
    // ACCESS TOKEN EXPIRED
    // --------------------------------------------------------

    if (response.status === 401) {
      const newToken =
        await refreshAccessToken();

      if (!newToken) {
        throw new Error(
          "Your session has expired. Please login again."
        );
      }

      const retryOptions = {
        ...options,

        headers: {
          ...(options.headers || {}),

          Authorization:
            `Bearer ${newToken}`,
        },
      };

      response =
        await fetch(
          url,
          retryOptions
        );
    }

    return response;
  }


  // ==========================================================
  // RESTORE SESSION ON PAGE LOAD
  // ==========================================================

  useEffect(() => {
    async function restoreSession() {
      const token =
        localStorage.getItem(
          "meenamitra_token"
        );

      const refreshToken =
        localStorage.getItem(
          "meenamitra_refresh_token"
        );

      // Nothing stored
      if (!token && !refreshToken) {
        return;
      }

      // --------------------------------------------------------
      // First try existing access token
      // --------------------------------------------------------

      if (token) {
        try {
          const response =
            await fetch(
              `${API_URL}/history`,
              {
                headers: {
                  Authorization:
                    `Bearer ${token}`,
                },
              }
            );

          if (response.ok) {
            setIsLoggedIn(true);

            const data =
              await response.json();

            setHistory(
              Array.isArray(
                data.history
              )
                ? data.history
                : []
            );

            return;
          }
        }

        catch (err) {
          console.error(
            "Session check error:",
            err
          );
        }
      }

      // --------------------------------------------------------
      // Existing token failed.
      // Try refresh token.
      // --------------------------------------------------------

      if (refreshToken) {
        const newToken =
          await refreshAccessToken();

        if (newToken) {
          setIsLoggedIn(true);

          await loadHistory(
            newToken
          );

          return;
        }
      }

      // --------------------------------------------------------
      // Both tokens failed.
      // --------------------------------------------------------

      clearAuthSession();

      setIsLoggedIn(false);
    }

    restoreSession();
  }, []);


  // ==========================================================
  // SIGNUP
  // ==========================================================

  async function handleSignup(e) {
    e.preventDefault();

    setError("");

    try {
      const response =
        await fetch(
          `${API_URL}/signup`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Signup failed"
        );
      }

      // --------------------------------------------------------
      // If backend returned session immediately
      // --------------------------------------------------------

      if (data.access_token) {
        saveAuthSession(data);

        setIsLoggedIn(true);

        setEmail("");

        setPassword("");

        setMessages([]);

        setConversationId(null);

        setActiveHistoryId(null);

        await loadHistory(
          data.access_token
        );
      }

      // --------------------------------------------------------
      // Email confirmation required
      // --------------------------------------------------------

      else {
        setError(
          "Signup successful. Please check your email to confirm your account, then login."
        );

        setShowSignup(false);
      }
    }

    catch (err) {
      setError(
        err.message ||
        "Signup failed"
      );
    }
  }


  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(e) {
    e.preventDefault();

    setError("");

    try {
      const response =
        await fetch(
          `${API_URL}/login`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Login failed"
        );
      }

      saveAuthSession(data);

      setIsLoggedIn(true);

      setMessages([]);

      setConversationId(null);

      setActiveHistoryId(null);

      setPassword("");

      await loadHistory(
        data.access_token
      );
    }

    catch (err) {
      setError(
        err.message ||
        "Login failed"
      );
    }
  }


  // ==========================================================
  // LOAD HISTORY
  // ==========================================================

  async function loadHistory(
    token = null
  ) {
    try {
      let response;

      if (token) {
        response =
          await fetch(
            `${API_URL}/history`,
            {
              headers: {
                Authorization:
                  `Bearer ${token}`,
              },
            }
          );
      }

      else {
        response =
          await authenticatedFetch(
            `${API_URL}/history`
          );
      }

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not load chat history"
        );
      }

      setHistory(
        Array.isArray(
          data.history
        )
          ? data.history
          : []
      );
    }

    catch (err) {
      console.error(
        "History loading error:",
        err
      );
    }
  }


  // ==========================================================
  // DELETE ONE SAVED CONVERSATION
  // ==========================================================

  async function deleteConversation(conversation, event) {
    event?.stopPropagation();

    const id = conversation?.conversation_id;
    if (!id) {
      setError("This conversation has no valid ID.");
      return;
    }

    const title = conversation.title ||
      (conversation.messages?.[0]?.question || "this conversation");

    if (!window.confirm(`Delete "${title}"? This will permanently remove its saved messages.`)) {
      return;
    }

    setError("");

    try {
      const response = await authenticatedFetch(
        `${API_URL}/history/${encodeURIComponent(id)}`,
        { method: "DELETE" }
      );

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Could not delete this conversation.");
      }

      setHistory((current) => current.filter(
        (item) => item.conversation_id !== id
      ));

      if (activeHistoryId === id || conversationId === id) {
        setActiveHistoryId(null);
        setConversationId(null);
        setMessages([]);
        setQuestion("");
      }
    } catch (err) {
      setError(err.message || "Could not delete this conversation.");
    }
  }


  // ==========================================================
  // OPEN OLD CONVERSATION
  // ==========================================================

  function openHistoryChat(conversation) {
    if (!conversation) {
      return;
    }

    // --------------------------------------------------------
    // Set the selected conversation
    // --------------------------------------------------------

    setConversationId(
      conversation.conversation_id
    );

    setActiveHistoryId(
      conversation.conversation_id
    );

    setError("");

    // --------------------------------------------------------
    // Restore every message in the conversation
    // --------------------------------------------------------

    const restoredMessages = [];

    const conversationMessages =
      Array.isArray(
        conversation.messages
      )
        ? conversation.messages
        : [];

    // Backend returns newest first.
    // Reverse it so chat displays oldest → newest.
    conversationMessages
      .slice()
      .reverse()
      .forEach((item) => {
        restoredMessages.push({
          role: "user",
          content: item.question,
        });

        restoredMessages.push({
          role: "assistant",
          content: item.answer,
        });
      });

    setMessages(
      restoredMessages
    );

    // On smaller screens, close sidebar
    setSidebarOpen(false);
  }


  // ==========================================================
  // SEND MESSAGE
  // ==========================================================

  async function sendMessage(e) {
    e.preventDefault();

    if (
      !question.trim() ||
      loading
    ) {
      return;
    }

    const token =
      localStorage.getItem(
        "meenamitra_token"
      );

    if (!token) {
      setError(
        "Please login first."
      );

      return;
    }

    const currentQuestion =
      question.trim();

    // --------------------------------------------------------
    // Immediately show user message
    // --------------------------------------------------------

    setMessages(
      previous => [
        ...previous,

        {
          role: "user",
          content:
            currentQuestion,
        },
      ]
    );

    setQuestion("");

    setLoading(true);

    setError("");

    try {
      // ------------------------------------------------------
      // IMPORTANT:
      // Send the CURRENT conversation ID.
      //
      // null = create a new conversation
      // UUID = continue existing conversation
      // ------------------------------------------------------

      const response =
        await authenticatedFetch(
          `${API_URL}/chat`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              question:
                currentQuestion,

              access_token:
                token,

              conversation_id:
                conversationId,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Something went wrong"
        );
      }

      // ------------------------------------------------------
      // Backend creates conversation ID for first question.
      // Save it for every future question.
      // ------------------------------------------------------

      if (data.conversation_id) {
        setConversationId(
          data.conversation_id
        );

        setActiveHistoryId(
          data.conversation_id
        );
      }

      // ------------------------------------------------------
      // Show AI response in SAME chat
      // ------------------------------------------------------

      setMessages(
        previous => [
          ...previous,

          {
            role: "assistant",
            content:
              data.answer,
          },
        ]
      );

      // ------------------------------------------------------
      // Reload sidebar.
      //
      // IMPORTANT:
      // We DO NOT reset conversationId here.
      // ------------------------------------------------------

      await loadHistory();
    }

    catch (err) {
      console.error(
        "Chat error:",
        err
      );

      setError(
        err.message ||
        "Unable to get response"
      );
    }

    finally {
      setLoading(false);
    }
  }


  // ==========================================================
  // LOGOUT
  // ==========================================================

  function logout() {
    clearAuthSession();

    setIsLoggedIn(false);

    setMessages([]);

    setHistory([]);

    setConversationId(null);

    setActiveHistoryId(null);

    setQuestion("");

    setEmail("");

    setPassword("");

    setError("");
  }


  // ==========================================================
  // NEW CONVERSATION
  // ==========================================================

  function newChat() {
    // --------------------------------------------------------
    // THIS IS VERY IMPORTANT
    //
    // Setting conversationId to null tells the backend:
    // "The next question is a brand-new conversation."
    // --------------------------------------------------------

    setConversationId(null);

    setActiveHistoryId(null);

    setMessages([]);

    setQuestion("");

    setError("");

    setSidebarOpen(false);
  }


  // ==========================================================
  // LOGIN / SIGNUP SCREEN
  // ==========================================================

  // ==========================================================
  // SHARED STYLE TOKENS (presentation only)
  // ==========================================================

  const inputClass =
    "w-full rounded-2xl border border-white/10 bg-abyss-950/50 px-4 py-3.5 text-[0.95rem] text-foam-50 placeholder:text-foam-200/40 outline-none transition focus:border-tide-400/60 focus:bg-abyss-950/70 focus:ring-4 focus:ring-tide-400/15";

  const iconButtonClass =
    "grid h-10 w-10 shrink-0 place-items-center rounded-xl text-foam-200/70 transition hover:bg-white/10 hover:text-foam-50";

  const suggestions = [
    {
      icon: Droplets,
      label: "Low dissolved oxygen",
      prompt: "What should I do if dissolved oxygen is low?",
    },
    {
      icon: Utensils,
      label: "Feeding schedule",
      prompt: "How often should I feed fish in a pond?",
    },
    {
      icon: Stethoscope,
      label: "Fish health",
      prompt: "What are common signs of disease in farmed fish?",
    },
    {
      icon: Waves,
      label: "Fish behavior",
      prompt: "Why are fish coming to the surface early in the morning?",
    },
  ];


  // ==========================================================
  // LOGIN / SIGNUP SCREEN
  // ==========================================================

  if (!isLoggedIn) {
    return (
      <div className="relative flex min-h-dvh items-center justify-center p-5 sm:p-8">

        <PhotoBackdrop src={PHOTOS.pondAerial.src} />
        <AmbientBackground />

        <motion.main
          initial={{ opacity: 0, y: 18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="glass-panel w-full max-w-md rounded-[2rem] p-8 text-center shadow-[0_40px_90px_-30px_rgb(0_0_0/0.7)] sm:p-10"
        >

          <div className="flex justify-center">
            <WaterOrb>
              <Fish size={34} strokeWidth={1.8} />
            </WaterOrb>
          </div>

          <h1 className="mt-6 text-3xl font-extrabold tracking-tight">
            {BRAND_NAME}
          </h1>

          <p className="mt-2 text-sm text-foam-200/70">
            Your intelligent aquaculture companion
          </p>

          <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-full border border-tide-400/25 bg-tide-400/10 px-3.5 py-1.5 text-xs font-medium text-tide-300">
            <Sparkles size={14} />
            AI-powered fish farming advisor
          </div>

          <h2 className="mt-9 text-xl font-bold tracking-tight">
            {showSignup
              ? "Create your account"
              : "Welcome back"}
          </h2>

          <p className="mt-1.5 text-sm text-foam-200/65">
            {showSignup
              ? `Create your ${BRAND_NAME} account to save your conversations.`
              : "Sign in to continue your fish-farming journey."}
          </p>

          <form
            className="mt-7 space-y-3 text-left"
            onSubmit={
              showSignup
                ? handleSignup
                : handleLogin
            }
          >

            <input
              type="email"
              placeholder="Email address"
              aria-label="Email address"
              className={inputClass}
              value={email}
              onChange={e =>
                setEmail(
                  e.target.value
                )
              }
              required
            />

            <input
              type="password"
              placeholder="Password"
              aria-label="Password"
              className={inputClass}
              value={password}
              onChange={e =>
                setPassword(
                  e.target.value
                )
              }
              minLength={6}
              required
            />

            {error && (
              <div
                role="alert"
                className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="mt-2 w-full rounded-2xl bg-linear-to-br from-tide-400 to-tide-600 px-5 py-3.5 font-bold text-abyss-950 shadow-lg shadow-tide-500/30 transition hover:brightness-110 active:scale-[0.99]"
            >
              {showSignup
                ? "Create Account"
                : "Login"}
            </button>

          </form>

          <button
            type="button"
            className="mt-6 text-sm font-semibold text-tide-300 transition hover:text-tide-400"
            onClick={() => {
              setShowSignup(
                !showSignup
              );

              setError("");
            }}
          >
            {showSignup
              ? "Already have an account? Login"
              : `New to ${BRAND_NAME}? Create an account`}
          </button>

          <VeltrisCredit className="mt-8 justify-center" />

        </motion.main>

      </div>
    );
  }


  // ==========================================================
  // MAIN APPLICATION
  // ==========================================================

  return (
    <div className="relative flex h-dvh overflow-hidden">

      <AmbientBackground />

      {/* Mobile overlay behind the open sidebar */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="fixed inset-0 z-30 bg-abyss-950/60 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh shrink-0 flex-col overflow-hidden bg-abyss-900/75 backdrop-blur-2xl transition-[transform,width] duration-300 ease-out md:relative ${
          sidebarOpen
            ? "w-72 translate-x-0 border-r border-white/10"
            : "w-72 -translate-x-full md:w-0 md:border-r-0"
        }`}
      >

        <div className="relative flex h-full w-72 flex-col">

          <img
            src={PHOTOS.waterSurface.src}
            alt=""
            aria-hidden="true"
            loading="lazy"
            decoding="async"
            className="pointer-events-none absolute inset-x-0 top-0 h-64 w-full object-cover opacity-25 [mask-image:linear-gradient(to_bottom,black,transparent)]"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />

          <div className="relative flex items-center justify-between gap-3 px-5 pt-5 pb-4">

            <div className="flex min-w-0 items-center gap-3">
              <BrandMark size="sm" />

              <span className="truncate font-bold tracking-tight">
                {BRAND_NAME}
              </span>
            </div>

            <button
              type="button"
              aria-label="Close sidebar"
              className={iconButtonClass}
              onClick={() =>
                setSidebarOpen(false)
              }
            >
              <X size={18} />
            </button>

          </div>


          {/* NEW CONVERSATION */}

          <div className="px-4">
            <button
              type="button"
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-linear-to-br from-tide-400 to-tide-600 px-4 py-3 font-semibold text-abyss-950 shadow-lg shadow-tide-500/25 transition hover:brightness-110 active:scale-[0.99]"
              onClick={newChat}
            >
              <Plus size={18} strokeWidth={2.4} />
              New conversation
            </button>
          </div>


          {/* HISTORY TITLE */}

          <div className="mt-7 flex items-center gap-2 px-5 text-sm font-semibold text-foam-200/55">
            <MessageCircle size={15} />
            Recent conversations
          </div>


          {/* HISTORY LIST */}

          <div className="mt-2 flex-1 space-y-1 overflow-y-auto px-3 pb-3">

            {history.length === 0 ? (

              <div className="px-3 py-8 text-center text-sm leading-relaxed text-foam-200/45">
                No conversations yet.
                <br />
                Ask {BRAND_NAME} your first question!
              </div>

            ) : (

              history.map(
                (conversation) => {

                  const isActive =
                    activeHistoryId ===
                    conversation.conversation_id;

                  return (

                    <div
                      key={conversation.conversation_id}
                      className={`group relative flex w-full items-center gap-1 rounded-xl transition ${
                        isActive
                          ? "bg-tide-400/12 text-foam-50"
                          : "text-foam-200/70 hover:bg-white/5 hover:text-foam-50"
                      }`}
                    >
                      <button
                        type="button"
                        className="relative flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm"
                        onClick={() => openHistoryChat(conversation)}
                        title={conversation.title || conversation.messages?.[0]?.question || "Conversation"}
                      >
                        {isActive && (
                          <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-tide-400" />
                        )}
                        <MessageCircle size={15} className="shrink-0 opacity-70" />
                        <span className="truncate">
                          {conversation.title ||
                            (conversation.messages?.length > 0
                              ? conversation.messages[0].question
                              : "Conversation")}
                        </span>
                      </button>

                      <button
                        type="button"
                        className="mr-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg text-foam-200/40 opacity-0 transition hover:bg-red-400/15 hover:text-red-300 focus-visible:opacity-100 group-hover:opacity-100"
                        title="Delete conversation"
                        aria-label={`Delete conversation: ${conversation.title || "Conversation"}`}
                        onClick={(event) => deleteConversation(conversation, event)}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>

                  );

                }
              )

            )}

          </div>


          {/* SIDEBAR BOTTOM */}

          <div className="border-t border-white/10 p-4">

            <VeltrisCredit className="mb-3 px-3" />

            <div className="flex items-center gap-2.5 rounded-xl bg-white/5 px-3 py-2.5 text-sm text-foam-200/80">

              <span className="relative flex h-2.5 w-2.5 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ripple rounded-full bg-tide-400" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-tide-400" />
              </span>

              {BRAND_NAME} online

            </div>

            <button
              type="button"
              className="mt-2 flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-foam-200/60 transition hover:bg-white/5 hover:text-foam-50"
              onClick={logout}
            >

              <LogOut size={17} />

              Logout

            </button>

          </div>

        </div>

      </aside>


      {/* ======================================================
          MAIN CHAT
      ====================================================== */}

      <main className="flex min-w-0 flex-1 flex-col">

        <header className="flex items-center gap-3 border-b border-white/10 bg-abyss-950/30 px-4 py-3.5 backdrop-blur-xl sm:px-6">

          {!sidebarOpen && (

            <button
              type="button"
              aria-label="Open sidebar"
              className={iconButtonClass}
              onClick={() =>
                setSidebarOpen(true)
              }
            >
              <Menu size={20} />
            </button>

          )}

          <BrandMark size="sm" />

          <div className="min-w-0">

            <h2 className="truncate text-base font-bold tracking-tight">
              {BRAND_NAME}
            </h2>

            <p className="truncate text-xs text-foam-200/55">
              Aquaculture AI advisor
            </p>

          </div>

          <div className="ml-auto hidden items-center gap-3 sm:flex">
            <VeltrisCredit />
          </div>

        </header>


        {/* ====================================================
            MESSAGES
        ==================================================== */}

        <section className="flex-1 overflow-y-auto">

          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6">

            {messages.length === 0 ? (

              <div className="flex flex-1 flex-col items-center justify-center text-center">

                <PhotoBanner
                  src={PHOTOS.fishUnderwater.src}
                  alt={PHOTOS.fishUnderwater.alt}
                >
                  <WaterOrb>
                    <Fish size={32} strokeWidth={1.8} />
                  </WaterOrb>
                </PhotoBanner>

                <h1 className="mt-20 text-3xl font-extrabold tracking-tight sm:mt-24 sm:text-4xl">
                  How can I help your pond today?
                </h1>

                <p className="mt-3 max-w-md text-[0.95rem] leading-relaxed text-foam-200/60">
                  Ask me about water quality,
                  feeding, fish health,
                  pond management and more.
                </p>


                <div className="mt-7 sm:mt-9 grid w-full max-w-xl grid-cols-1 gap-2.5 sm:gap-3 sm:grid-cols-2">

                  {suggestions.map(
                    ({ icon: Icon, label, prompt }) => (

                      <motion.button
                        key={label}
                        type="button"
                        whileHover={{ y: -2 }}
                        whileTap={{ scale: 0.98 }}
                        className="glass-panel flex items-center gap-3 rounded-2xl px-4 py-3 sm:py-4 text-left text-sm font-medium text-foam-50/90 transition hover:border-tide-400/40 hover:bg-white/10"
                        onClick={() =>
                          setQuestion(prompt)
                        }
                      >

                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-tide-400/12 text-tide-300">
                          <Icon size={18} />
                        </span>

                        {label}

                      </motion.button>

                    )
                  )}

                </div>

              </div>

            ) : (

              messages.map(
                (message, index) => {

                  const isUser =
                    message.role === "user";

                  return (

                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: "easeOut" }}
                      className={`flex gap-3.5 ${
                        isUser ? "flex-row-reverse" : ""
                      }`}
                    >

                      <div
                        className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-base ${
                          isUser
                            ? "bg-white/10 ring-1 ring-white/10"
                            : "bg-tide-400/15 text-tide-300 ring-1 ring-tide-400/25"
                        }`}
                      >

                        {isUser
                          ? "👩‍🌾"
                          : <Fish size={17} strokeWidth={2} />}

                      </div>

                      <div
                        className={`flex max-w-[85%] flex-col gap-1.5 ${
                          isUser ? "items-end" : "items-start"
                        }`}
                      >

                        <span className="px-1 text-xs font-semibold text-foam-200/50">
                          {isUser ? "You" : BRAND_NAME}
                        </span>

                        <div
                          className={`break-words rounded-2xl px-4 py-3 text-[0.95rem] leading-relaxed ${
                            isUser
                              ? "rounded-tr-md bg-tide-500/20 text-foam-50 ring-1 ring-tide-400/25"
                              : "glass-panel rounded-tl-md text-foam-50/90"
                          }`}
                        >

                          {isUser ? message.content : <AnswerText text={message.content} />}

                        </div>

                      </div>

                    </motion.div>

                  );

                }
              )

            )}


            {/* LOADING */}

            {loading && (

              <div className="flex gap-3.5">

                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-tide-400/15 text-tide-300 ring-1 ring-tide-400/25">
                  <Fish size={17} strokeWidth={2} />
                </div>

                <div className="flex flex-col items-start gap-1.5">

                  <span className="px-1 text-xs font-semibold text-foam-200/50">
                    {BRAND_NAME}
                  </span>

                  <div
                    role="status"
                    aria-label={`${BRAND_NAME} is thinking`}
                    className="glass-panel flex items-center gap-1.5 rounded-2xl rounded-tl-md px-4 py-4"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-tide-300 animate-bob" />
                    <span className="h-1.5 w-1.5 rounded-full bg-tide-300 animate-bob [animation-delay:0.15s]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-tide-300 animate-bob [animation-delay:0.3s]" />
                  </div>

                </div>

              </div>

            )}

          </div>

        </section>


        {/* ERROR */}

        {error && (

          <div className="mx-auto w-full max-w-3xl px-4 sm:px-6">
            <div
              role="alert"
              className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
            >
              {error}
            </div>
          </div>

        )}


        {/* ====================================================
            CHAT INPUT
        ==================================================== */}

        <form
          className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6"
          onSubmit={sendMessage}
        >

          <div className="mx-auto max-w-3xl">

            <div className="glass-panel flex items-end gap-2 rounded-3xl p-2 pl-5 shadow-[0_20px_60px_-20px_rgb(0_0_0/0.6)] transition focus-within:border-tide-400/50 focus-within:ring-4 focus-within:ring-tide-400/10">

              <textarea
                aria-label="Ask a question"
                className="max-h-40 min-h-11 flex-1 resize-none bg-transparent py-2.5 text-[0.95rem] leading-relaxed text-foam-50 outline-none placeholder:text-foam-200/40"
                value={question}

                onChange={e =>
                  setQuestion(
                    e.target.value
                  )
                }

                placeholder="Ask about your fish farm..."

                rows={1}

                onKeyDown={e => {

                  if (
                    e.key === "Enter" &&
                    !e.shiftKey
                  ) {

                    e.preventDefault();

                    sendMessage(e);

                  }

                }}

              />


              <button
                type="submit"
                aria-label="Send message"
                disabled={
                  loading ||
                  !question.trim()
                }
                className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-linear-to-br from-tide-400 to-tide-600 text-abyss-950 shadow-lg shadow-tide-500/30 transition hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
              >

                <Send size={18} />

              </button>

            </div>


            <p className="mt-3 px-2 text-center text-xs leading-relaxed text-foam-200/40">
              {BRAND_NAME} provides general aquaculture guidance.
              For serious fish-health problems, consult a qualified professional.
            </p>

          </div>

        </form>

      </main>

    </div>
  );
}


export default App;
