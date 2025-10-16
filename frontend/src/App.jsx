import React from "react";
import { flushSync } from "react-dom";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
} from "@assistant-ui/react";
import { TurfmappChatAdapter } from "./runtime/TurfmappChatAdapter.js";
import { ChatThread } from "./components/ChatThread.jsx";

const LoadingState = ({ message = "Initializing chat…" }) => (
  <div className="assistant-loading-state">{message}</div>
);

const ErrorState = () => (
  <div className="assistant-error-state">
    We couldn&apos;t start the chat experience. Please refresh or try again
    later.
  </div>
);

const ChatRuntime = ({ adapter }) => {
  const [state, setState] = React.useState({
    initialMessages: null,
    isLoading: true,
  });

  // Check for conversation ID in localStorage on mount
  React.useEffect(() => {
    const loadConvId = localStorage.getItem('loadConversationId');
    if (loadConvId && adapter) {
      console.log('Loading conversation from localStorage:', loadConvId);

      adapter.loadConversation(loadConvId)
        .then(messages => {
          console.log('Loaded messages:', messages);
          // Clear the flag after loading
          localStorage.removeItem('loadConversationId');
          setState({ initialMessages: messages, isLoading: false });
        })
        .catch(error => {
          console.error('Failed to load conversation:', error);
          localStorage.removeItem('loadConversationId');
          setState({ initialMessages: [], isLoading: false });
        });
    } else {
      // No conversation to load, start with empty messages
      setState({ initialMessages: [], isLoading: false });
    }
  }, [adapter]);

  // Expose global function for conversation loading
  React.useEffect(() => {
    if (adapter) {
      // Global function to load a conversation - uses page reload
      window.loadConversation = async (conversationId) => {
        try {
          console.log('Requesting to load conversation:', conversationId);
          // Store conversation ID in localStorage
          localStorage.setItem('loadConversationId', conversationId);
          // Reload the page to properly reinitialize everything
          window.location.reload();
        } catch (error) {
          console.error('Failed to prepare conversation load:', error);
          alert('Failed to load conversation. Please try again.');
        }
      };
    }
    return () => {
      delete window.loadConversation;
    };
  }, [adapter]);

  // Show loading state until messages are loaded
  if (state.isLoading || state.initialMessages === null) {
    return <LoadingState message="Loading conversation…" />;
  }

  // Now render the runtime with the loaded messages
  return <ChatRuntimeWithMessages adapter={adapter} initialMessages={state.initialMessages} />;
};

const ChatRuntimeWithMessages = ({ adapter, initialMessages }) => {
  const runtime = useLocalRuntime(adapter, {
    initialMessages: initialMessages,
  });

  // Expose adapter and runtime globally
  React.useEffect(() => {
    if (adapter && runtime) {
      window.chatAdapter = adapter;
      window.chatRuntime = runtime;
    }
    return () => {
      delete window.chatAdapter;
      delete window.chatRuntime;
    };
  }, [adapter, runtime]);

  if (!runtime) {
    return <LoadingState message="Initializing chat…" />;
  }

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ChatThread />
    </AssistantRuntimeProvider>
  );
};

const ChatApp = () => {
  const [adapter, setAdapter] = React.useState(null);
  const [initializing, setInitializing] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;

    const initialise = async () => {
      try {
        if (typeof window !== "undefined") {
          if (typeof window.initializeSupabase === "function") {
            await window.initializeSupabase();
          }
        }

        const getAuthToken = () => {
          try {
            return window?.supabase?.getAccessToken?.() ?? null;
          } catch (err) {
            console.error("Unable to read Supabase auth token", err);
            return null;
          }
        };

        const instance = new TurfmappChatAdapter(getAuthToken);
        if (!cancelled) {
          setAdapter(instance);
        }
      } catch (err) {
        console.error("Failed to initialise chat runtime", err);
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setInitializing(false);
        }
      }
    };

    initialise();

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <ErrorState />;
  }

  if (initializing || !adapter) {
    return <LoadingState message="Preparing your workspace…" />;
  }

  return <ChatRuntime adapter={adapter} />;
};

export default ChatApp;
