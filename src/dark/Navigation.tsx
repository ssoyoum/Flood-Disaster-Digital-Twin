import { ChevronDown, PanelsTopLeft } from "lucide-react";
import "./navigation.css";

export type FloodOpsRoute = "watch" | "validation" | "osong" | "twin" | "cases" | "compare" | "intro";

const ROUTES: Array<{ id: FloodOpsRoute; label: string; href: string }> = [
  { id: "intro", label: "홈 · FloodOps 소개", href: "#" },
  { id: "watch", label: "전국 관제 보드", href: "#watch" },
  { id: "validation", label: "과거 홍수 검증", href: "#watch?tab=vc" },
  { id: "osong", label: "오송 HAND 시뮬레이션", href: "#event/osong-2023" },
  { id: "twin", label: "운영 시설 통제 판단", href: "#twin" },
  { id: "cases", label: "사례 라이브러리", href: "#cases" },
  { id: "compare", label: "사례 간 비교", href: "#compare" },
];

export function AppNavigation({ active }: { active: FloodOpsRoute }) {
  return (
    <details className="fo-global-menu">
      <summary aria-label="FloodOps 화면 이동">
        <PanelsTopLeft size={16} />
        <span>화면 이동</span>
        <ChevronDown size={14} className="fo-global-menu-chevron" />
      </summary>
      <nav className="fo-global-menu-panel" aria-label="FloodOps 화면">
        {ROUTES.map((route) => (
          <a key={route.id} href={route.href} aria-current={active === route.id ? "page" : undefined}>
            {route.label}
          </a>
        ))}
      </nav>
    </details>
  );
}
