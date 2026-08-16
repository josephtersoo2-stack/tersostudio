import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  Play,
  RefreshCw,
  Terminal,
  Trash2,
  Wrench,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/formatters";

interface LiveEvent {
  id: string;
  event_type: string;
  timestamp: string;
  generation_id?: string;
  agent_run_id?: string;
  step_id?: string;
  payload: Record<string, unknown>;
}

interface LiveEventsPanelProps {
  generationId: string;
}

const WS_BASE_URL =
  (import.meta as unknown as { env?: { VITE_WS_BASE_URL?: string } }).env?.VITE_WS_BASE_URL ||
  `ws://${window.location.host}`;

export const LiveEventsPanel: React.FC<LiveEventsPanelProps> = ({ generationId }) => {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting");
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const [autoScroll, setAutoScroll] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");

  const socketRef = useRef<WebSocket | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const connectWebSocket = () => {
    if (!generationId) return;

    if (socketRef.current) {
      socketRef.current.close();
    }

    setConnectionStatus("connecting");

    const wsUrl = `${WS_BASE_URL.replace(/\/$/, "")}/ws/v1/events/${generationId}/`;
    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          // Normalized event envelope
          const normalized: LiveEvent = {
            id: rawData.id || `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            event_type: rawData.event_type || rawData.type || "UNKNOWN",
            timestamp: rawData.timestamp || new Date().toISOString(),
            generation_id: rawData.generation_id,
            agent_run_id: rawData.agent_run_id,
            step_id: rawData.step_id,
            payload: rawData.payload || rawData,
          };

          setEvents((prev) => [...prev, normalized]);
        } catch {
          // Ignore invalid non-json frames
        }
      };

      ws.onerror = () => {
        setConnectionStatus("error");
      };

      ws.onclose = () => {
        setConnectionStatus("disconnected");
      };
    } catch {
      setConnectionStatus("error");
    }
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [generationId]);

  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredEvents = events.filter((ev) => {
    if (filterType === "ALL") return true;
    if (filterType === "AGENT") return ev.event_type.startsWith("agent.");
    if (filterType === "TOOL") return ev.event_type.includes("tool");
    if (filterType === "TASK") return ev.event_type.startsWith("task.");
    if (filterType === "SYSTEM") return ev.event_type.startsWith("system.");
    return true;
  });

  const getEventIcon = (eventType: string) => {
    const t = eventType.toLowerCase();
    if (t.includes("started") || t.includes("run")) return <Play className="w-3.5 h-3.5 text-blue-400" />;
    if (t.includes("tool")) return <Wrench className="w-3.5 h-3.5 text-amber-400" />;
    if (t.includes("thinking")) return <Cpu className="w-3.5 h-3.5 text-purple-400 animate-pulse" />;
    if (t.includes("completed") || t.includes("success")) return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
    if (t.includes("failed") || t.includes("error")) return <AlertCircle className="w-3.5 h-3.5 text-rose-400" />;
    if (t.includes("ping")) return <Zap className="w-3.5 h-3.5 text-slate-500" />;
    return <Terminal className="w-3.5 h-3.5 text-slate-400" />;
  };

  const getEventBadgeClass = (eventType: string) => {
    const t = eventType.toLowerCase();
    if (t.includes("failed") || t.includes("error")) return "bg-rose-950/60 text-rose-300 border-rose-800/60";
    if (t.includes("completed") || t.includes("success")) return "bg-emerald-950/60 text-emerald-300 border-emerald-800/60";
    if (t.includes("tool")) return "bg-amber-950/60 text-amber-300 border-amber-800/60";
    if (t.includes("thinking")) return "bg-purple-950/60 text-purple-300 border-purple-800/60";
    if (t.includes("started")) return "bg-blue-950/60 text-blue-300 border-blue-800/60";
    return "bg-slate-900 text-slate-400 border-slate-800";
  };

  return (
    <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm overflow-hidden flex flex-col h-[520px]">
      {/* Panel Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-semibold text-slate-200">Live Agent Event Stream</h3>
          </div>

          {/* Connection Status Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                connectionStatus === "connected"
                  ? "bg-emerald-500 animate-pulse"
                  : connectionStatus === "connecting"
                  ? "bg-amber-500 animate-ping"
                  : "bg-rose-500"
              }`}
            />
            <span
              className={
                connectionStatus === "connected"
                  ? "text-emerald-400 capitalize"
                  : connectionStatus === "connecting"
                  ? "text-amber-400 capitalize"
                  : "text-rose-400 capitalize"
              }
            >
              {connectionStatus}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Event Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-300 focus:border-brand-500 focus:outline-none font-mono"
          >
            <option value="ALL">All Events ({events.length})</option>
            <option value="AGENT">Agent Lifecycle</option>
            <option value="TOOL">Tool Execution</option>
            <option value="TASK">Task Milestones</option>
            <option value="SYSTEM">System Ping</option>
          </select>

          {/* Auto-scroll toggle */}
          <button
            type="button"
            onClick={() => setAutoScroll((v) => !v)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-mono transition-colors ${
              autoScroll
                ? "bg-brand-950/60 border-brand-800/80 text-brand-300"
                : "bg-slate-950 border-slate-800 text-slate-500"
            }`}
            title="Toggle auto-scroll to bottom on new event"
          >
            Auto-scroll: {autoScroll ? "ON" : "OFF"}
          </button>

          {/* Clear Log */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEvents([])}
            className="text-slate-500 hover:text-slate-200"
            title="Clear event logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>

          {/* Reconnect button */}
          {connectionStatus !== "connected" && (
            <Button
              variant="outline"
              size="sm"
              onClick={connectWebSocket}
              leftIcon={<RefreshCw className="w-3 h-3" />}
            >
              Reconnect
            </Button>
          )}
        </div>
      </div>

      {/* Events Log Area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-xs bg-slate-950/80 divide-y divide-slate-900"
      >
        {filteredEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
            <Terminal className="w-8 h-8 mb-2 opacity-50 text-slate-600" />
            <p className="text-sm font-semibold text-slate-400">Waiting for live agent events...</p>
            <p className="text-xs text-slate-600 max-w-sm mt-1">
              Events dispatched during generation execution will appear here in real-time over WebSocket.
            </p>
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const isExpanded = !!expandedEvents[ev.id];
            return (
              <div key={ev.id} className="pt-2 first:pt-0">
                <div
                  onClick={() => toggleExpand(ev.id)}
                  className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-slate-900/60 transition-colors cursor-pointer group"
                >
                  <button
                    type="button"
                    className="text-slate-600 group-hover:text-slate-400 mt-0.5"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>

                  <div className="mt-0.5">{getEventIcon(ev.event_type)}</div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-semibold tracking-wide uppercase ${getEventBadgeClass(
                          ev.event_type
                        )}`}
                      >
                        {ev.event_type}
                      </span>

                      {ev.agent_run_id && (
                        <span className="text-[10px] text-slate-500">
                          run: {ev.agent_run_id.substring(0, 8)}...
                        </span>
                      )}

                      <span className="text-[10px] text-slate-600 ml-auto flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(ev.timestamp)}
                      </span>
                    </div>

                    {/* Quick Payload Snippet */}
                    <div className="text-slate-300 text-xs mt-1 truncate">
                      {typeof ev.payload?.message === "string"
                        ? ev.payload.message
                        : typeof ev.payload?.tool === "string"
                        ? `Tool: ${ev.payload.tool}`
                        : typeof ev.payload?.thought === "string"
                        ? `Thought: ${ev.payload.thought}`
                        : JSON.stringify(ev.payload)}
                    </div>
                  </div>
                </div>

                {/* Expanded Payload Inspector */}
                {isExpanded && (
                  <div className="ml-8 mt-2 p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] overflow-x-auto">
                    <pre className="text-slate-300">
                      {JSON.stringify(ev.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
