import { useEffect, useRef, useCallback } from 'react';

const SSE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace('/api', '')}/api/cda/events`
  : '/api/cda/events';

interface SSEEvent {
  tipo: 'status' | 'heartbeat' | 'bargain';
  dados: Record<string, unknown>;
}

type EventHandler = (event: SSEEvent) => void;

export function useCDASSE(onEvent: EventHandler) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(SSE_URL);
    eventSourceRef.current = es;

    es.onmessage = (msg) => {
      try {
        const eventos: SSEEvent[] = JSON.parse(msg.data);
        eventos.forEach((ev) => onEventRef.current(ev));
      } catch {
        // ignora parse errors
      }
    };

    es.onerror = () => {
      es.close();
      // reconecta após 5s
      setTimeout(connect, 5000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);
}
