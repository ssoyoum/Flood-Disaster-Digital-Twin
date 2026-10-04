import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { analyticsConfigured, configuredIds, loadAnalytics, readConsent, writeConsent } from "../analytics";
import "./landing.css";
import "./consent.css";

/* 방문 통계·광고 측정 동의 배너. 측정 ID가 빌드에 없으면 아예 나타나지 않는다. */
export function ConsentBanner({ onPrivacy, onDecided }: { onPrivacy: () => void; onDecided: () => void }) {
  const [choice, setChoice] = useState(readConsent);
  const ids = configuredIds();
  if (!analyticsConfigured(ids) || choice !== null) return null;

  const decide = (value: "granted" | "denied") => {
    writeConsent(value);
    setChoice(value);
    if (value === "granted") loadAnalytics(ids);
    onDecided();
  };

  const uses = [ids.ga4 && "방문 통계(Google Analytics)", ids.pixel && "광고 성과 측정(Meta 픽셀)"].filter(Boolean).join(", ");
  return (
    <div className="fo-consent" role="dialog" aria-live="polite" aria-label="쿠키 사용 동의">
      <p>FloodOps는 다음 목적으로 쿠키를 사용합니다: {uses}. 동의하지 않아도 모든 화면을 그대로 쓸 수 있습니다.</p>
      <div>
        <button type="button" className="fo-ghost" onClick={onPrivacy}>개인정보 안내</button>
        <button type="button" className="fo-ghost" onClick={() => decide("denied")}>거부</button>
        <button type="button" className="fo-consent-accept" onClick={() => decide("granted")}>동의</button>
      </div>
    </div>
  );
}

export function PrivacyPage({ onBack }: { onBack: () => void }) {
  const ids = configuredIds();
  const contact = import.meta.env.VITE_PRIVACY_CONTACT?.trim();
  const reset = () => {
    writeConsent("denied");
    window.location.reload();
  };
  return (
    <main className="fo-landing fo-privacy">
      <header><button className="fo-ghost" type="button" onClick={onBack}><ArrowLeft size={16} /> 돌아가기</button></header>
      <article>
        <p className="fo-eyebrow">PRIVACY</p>
        <h2>개인정보 처리 안내</h2>
        <p>FloodOps는 회원가입이나 로그인이 없고, 이름·연락처 같은 개인정보를 직접 입력받지 않습니다.</p>
        <h3>방문 통계와 광고 측정</h3>
        {analyticsConfigured(ids) ? (
          <ul>
            {ids.ga4 && <li>Google Analytics 4(Google LLC): 방문한 화면, 머문 시간, 기기·브라우저 종류, 대략적 지역(국가·도시)을 쿠키 식별자와 함께 수집합니다. IP 주소는 익명화 설정으로 보냅니다.</li>}
            {ids.pixel && <li>Meta 픽셀(Meta Platforms, Inc.): 광고를 보고 들어온 방문을 측정하기 위해 방문 화면과 쿠키 식별자를 Meta로 보냅니다.</li>}
            <li>이 정보는 동의 배너에서 "동의"를 누른 경우에만 수집합니다. 각 서비스의 보관 기간과 국외 이전은 해당 회사의 정책을 따릅니다.</li>
          </ul>
        ) : (
          <p>현재 이 사이트에는 방문 통계·광고 측정 도구가 연결되어 있지 않습니다.</p>
        )}
        <h3>Agent 질문</h3>
        <p>대응 에이전트에 입력한 질문과 분석 도구 결과는 답변 생성을 위해 Google Gemini API로 전송됩니다. 개인정보를 입력하지 마세요.</p>
        {analyticsConfigured(ids) && (
          <>
            <h3>동의 철회</h3>
            <p>아래 버튼을 누르면 이 브라우저에서 측정을 거부한 상태로 바뀝니다. 브라우저의 쿠키 삭제로도 철회할 수 있습니다.</p>
            <button type="button" className="fo-ghost" onClick={reset}>측정 거부로 변경</button>
          </>
        )}
        <h3>문의</h3>
        <p>{contact ? contact : "사이트 운영자에게 문의해 주세요."}</p>
      </article>
    </main>
  );
}
