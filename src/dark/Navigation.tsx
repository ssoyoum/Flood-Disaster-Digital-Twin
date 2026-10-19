import { ChevronDown, PanelsTopLeft } from "lucide-react";
import "./navigation.css";

export type FloodOpsRoute = "intro" | "watch" | "scorecard" | "twin" | "cases" | "osong" | "compare";

type MenuItem = { id: FloodOpsRoute; label: string; season?: string; href: string; children?: MenuItem[] };

// 홈 아래 네 화면. 메뉴 이름은 업무 시기(장마 중·후·전)와 근거 자료로 나눈다.
export const SCREENS: MenuItem[] = [
  { id: "intro", label: "홈", href: "#" },
  { id: "watch", label: "관제 보드", season: "장마 중", href: "#watch" },
  { id: "scorecard", label: "기준 채점", season: "장마 후", href: "#scorecard" },
  { id: "twin", label: "시설 기준", season: "장마 전", href: "#twin" },
  {
    id: "cases", label: "사례 재구성", season: "근거", href: "#cases",
    children: [
      { id: "osong", label: "오송 HAND 시뮬레이션", href: "#event/osong-2023" },
      { id: "compare", label: "사례 간 비교", href: "#compare" },
    ],
  },
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
        {SCREENS.map((item) => (
          <div key={item.id} className="fo-global-menu-group">
            <a href={item.href} aria-current={active === item.id ? "page" : undefined}>
              <span>{item.label}</span>
              {item.season && <small>{item.season}</small>}
            </a>
            {item.children?.map((child) => (
              <a key={child.id} className="fo-global-menu-sub" href={child.href} aria-current={active === child.id ? "page" : undefined}>
                {child.label}
              </a>
            ))}
          </div>
        ))}
      </nav>
    </details>
  );
}
