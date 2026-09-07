const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

/**
 * Opens an authenticated WebSocket and calls `onEvent` for every message.
 * If the socket drops, it retries with a capped exponential backoff -
 * meanwhile the app keeps working off its last fetched state, and a manual
 * refresh (or the next successful reconnect) brings it current again.
 * Returns a cleanup function.
 */
export function connectSocket(accessToken, onEvent, onStatusChange) {
  let socket = null;
  let closedByUs = false;
  let attempt = 0;
  let retryTimer = null;

  function connect() {
    if (!accessToken) return;
    socket = new WebSocket(`${WS_URL}/ws?token=${encodeURIComponent(accessToken)}`);

    socket.onopen = () => {
      attempt = 0;
      onStatusChange?.("connected");
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onEvent(parsed);
      } catch {
        // ignore malformed frames
      }
    };

    socket.onclose = () => {
      onStatusChange?.("disconnected");
      if (!closedByUs) {
        const delay = Math.min(1000 * 2 ** attempt, 15000);
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      }
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  connect();

  return () => {
    closedByUs = true;
    if (retryTimer) clearTimeout(retryTimer);
    socket?.close();
  };
}
