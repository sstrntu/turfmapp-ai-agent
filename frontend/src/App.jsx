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
  const [initialMessages, setInitialMessages] = React.useState([]);
  const [key, setKey] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(false);

  const runtime = useLocalRuntime(adapter, {
    initialMessages: initialMessages,
  });

  // Expose adapter and runtime globally for conversation loading
  React.useEffect(() => {
    if (adapter && runtime) {
      window.chatAdapter = adapter;
      window.chatRuntime = runtime;

      // Global function to load a conversation
      window.loadConversation = async (conversationId) => {
        try {
          console.log('Loading conversation:', conversationId);

          // Show loading state immediately using flushSync for synchronous update
          flushSync(() => {
            setIsLoading(true);
          });

          const messages = await adapter.loadConversation(conversationId);

          // Update messages and key synchronously to ensure immediate UI update
          flushSync(() => {
            setInitialMessages(messages);
            setKey(k => k + 1); // Force recreation of runtime
          });

          // Small delay to allow runtime to initialize with new messages
          await new Promise(resolve => setTimeout(resolve, 100));

          // Hide loading state
          flushSync(() => {
            setIsLoading(false);
          });

          console.log('✅ Conversation loaded successfully');
        } catch (error) {
          console.error('Failed to load conversation:', error);
          flushSync(() => {
            setIsLoading(false);
          });
          throw error;
        }
      };
    }
    return () => {
      delete window.chatAdapter;
      delete window.chatRuntime;
      delete window.loadConversation;
    };
  }, [adapter, runtime]);

  if (!runtime || isLoading) {
    return <LoadingState message={isLoading ? "Loading conversation…" : "Initializing chat…"} />;
  }

  return (
    <AssistantRuntimeProvider key={key} runtime={runtime}>
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
