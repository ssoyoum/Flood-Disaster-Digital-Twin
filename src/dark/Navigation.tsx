import { ChevronDown, PanelsTopLeft } from "lucide-react";

export type FloodOpsRoute = "watch" | "twin" | "cases" | "compare" | "intro";

const ROUTES: Array<{ id: FloodOpsRoute; label: string; href: string }> = [
  { id: "twin", label: "운영 시설 통제 판단", href: "#twin" },
  { id: "watch", label: "특보 입구 · 전국 감시", href: "#watch" },
  { id: "cases", label: "사례 검증", href: "#cases" },
  { id: "compare", label: "효과성 채점표", href: "#compare" },
  { id: "intro", label: "FloodOps 소개", href: "#intro" },
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
