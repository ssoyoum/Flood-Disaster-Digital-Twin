import { useEffect, useRef, useState } from "react";
import "./watch.css";

type WatchView = { at: string | null; region: string | null; stage: string | null; station: string | null; driver: string | null };

function readWatchView(): WatchView {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return { at: query.get("at"), region: query.get("region"), stage: query.get("stage"), station: query.get("facility") ?? query.get("station"), driver: query.get("driver") };
}

function buildFrameUrl() {
  const params = new URLSearchParams();
  params.set("api", import.meta.env.VITE_API_BASE === "same-origin" ? "" : import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD ? "" : "http://localhost:8033"));
  Object.entries(readWatchView()).forEach(([key, value]) => { if (value) params.set(key, value); });
  return `/watch-board-integration.html?${params.toString()}`;
}

function viewHash(view: WatchView) {
  const params = new URLSearchParams();
  Object.entries(view).forEach(([key, value]) => { if (value) params.set(key, value); });
  const query = params.toString();
  return `#watch${query ? `?${query}` : ""}`;
}

export default function WatchBoard() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [frameUrl] = useState(buildFrameUrl);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      if (event.data?.type !== "floodops-watch-view") return;
      const incoming = event.data.view ?? {};
      const nextHash = viewHash({ at: incoming.at ?? null, region: incoming.region ?? null, stage: incoming.stage ?? null,
        station: incoming.facility_id ?? incoming.station ?? null, driver: incoming.driver ?? null });
      if (window.location.hash !== nextHash) window.location.hash = nextHash;
    };
    const onHashChange = () => {
      frameRef.current?.contentWindow?.postMessage({ type: "floodops-watch-set-view", view: readWatchView() }, window.location.origin);
    };
    window.addEventListener("message", onMessage);
    window.addEventListener("hashchange", onHashChange);
    return () => {
      window.removeEventListener("message", onMessage);
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);

  return (
    <main className="wb-root" aria-label="FloodOps 감시 보드">
      <iframe ref={frameRef} title="FloodOps 전국 하천 감시 보드" src={frameUrl} />
    </main>
  );
}
