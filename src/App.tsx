import { useEffect, useState } from "react";
import { Activity, AlertTriangle } from "lucide-react";
import * as api from "./api";
import DarkConsole from "./dark/DarkConsole";
import { CaseSelectPage, IntroPage } from "./dark/Landing";
import { localizeEvent, localizeReconstruction } from "./dark/ko";
import type { DataStatusResponse, ExposureMetrics, FloodEvent, LayersResponse, ReconstructionResponse } from "./types";

// Hash routes keep the browser back button working: "" intro, "#cases", "#event/<id>".
type Route = { page: "intro" } | { page: "cases" } | { page: "event"; id: string };

function readRoute(): Route {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash === "cases") return { page: "cases" };
  if (hash.startsWith("event/")) return { page: "event", id: decodeURIComponent(hash.slice(6)) };
  return { page: "intro" };
}

// The layer payload is large; a slow or restarting server deserves a couple more tries before an error.
async function withRetry<T>(load: () => Promise<T>, attempts = 3): Promise<T> {
  for (let attempt = 1; ; attempt += 1) {
    try {
      return await load();
    } catch (error) {
      if (attempt >= attempts) throw error;
      await new Promise((resolve) => window.setTimeout(resolve, 2000 * attempt));
    }
  }
}

function go(hash: string) {
  window.location.hash = hash;
}

export default function App() {
  const [route, setRoute] = useState<Route>(readRoute);
  const [events, setEvents] = useState<FloodEvent[] | null>(null);
  const [eventsError, setEventsError] = useState(false);

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api.getEvents().then(setEvents).catch(() => setEventsError(true));
  }, []);

  useEffect(() => {
    if (route.page === "intro") document.title = "FloodOps | 홍수 대응 디지털 트윈";
    if (route.page === "cases") document.title = "사례 선택 | FloodOps";
  }, [route]);

  if (route.page === "intro") return <IntroPage onStart={() => go("cases")} />;
  if (route.page === "cases") {
    if (eventsError) return <ErrorState message="사례 목록을 불러오지 못했습니다. 백엔드 API 연결을 확인하세요." />;
    if (!events) return <LoadingState label="사례 목록을 불러오는 중" />;
    return <CaseSelectPage events={events} onSelect={(id) => go(`event/${encodeURIComponent(id)}`)} onBack={() => go("")} />;
  }
  return <EventConsole key={route.id} eventId={route.id} />;
}

function LoadingState({ label }: { label: string }) {
  return <div className="app-state"><Activity className="spin" /><strong>{label}</strong></div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="app-state error-state"><AlertTriangle /><strong>FloodOps를 불러오지 못했습니다</strong><span>{message}</span></div>;
}

function EventConsole({ eventId }: { eventId: string }) {
  const [eventData, setEventData] = useState<FloodEvent | null>(null);
  const [layers, setLayers] = useState<LayersResponse | null>(null);
  const [summary, setSummary] = useState<ExposureMetrics | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [reconstruction, setReconstruction] = useState<ReconstructionResponse | null>(null);
  const [time, setTime] = useState(0);
  const [scenario, setScenario] = useState<"baseline" | "intervention">("baseline");
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const nextEvent = await withRetry(() => api.getEvent(eventId));
        const [nextLayers, nextSummary, nextStatus, nextReconstruction] = await Promise.all([
          withRetry(() => api.getLayers(eventId, nextEvent.data_year)),
          api.getSummary(eventId),
          api.getStatus(eventId),
          api.getReconstruction(eventId),
        ]);
        const localized = localizeEvent(nextEvent);
        document.title = `${localized.name} | FloodOps`;
        setEventData(localized);
        setLayers(nextLayers);
        setSummary(nextSummary);
        setDataStatus(nextStatus);
        setReconstruction(localizeReconstruction(nextReconstruction));
      } catch {
        setError("이 사례의 관제 데이터를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  useEffect(() => {
    if (!reconstruction || !replayPlaying) return undefined;
    const timer = window.setInterval(() => {
      setTime((index) => {
        const nextIndex = index + 1;
        if (nextIndex >= reconstruction.replay.length) {
          setReplayPlaying(false);
          return index;
        }
        return nextIndex;
      });
    }, 1100);
    return () => window.clearInterval(timer);
  }, [reconstruction, replayPlaying]);

  if (loading) return <LoadingState label="관제 화면을 준비하는 중" />;
  if (error || !eventData || !layers) return <ErrorState message={error ?? "데이터가 비어 있습니다."} />;

  return (
    <DarkConsole
      eventData={eventData}
      layers={layers}
      summary={summary}
      dataStatus={dataStatus}
      reconstruction={reconstruction}
      time={time}
      setTime={setTime}
      playing={replayPlaying}
      setPlaying={setReplayPlaying}
      scenario={scenario}
      setScenario={setScenario}
    />
  );
}
