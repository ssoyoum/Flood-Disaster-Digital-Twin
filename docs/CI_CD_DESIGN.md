# CI/CD 설계와 현재 배포 경계

확인일: 2026-10-20. 기준 commit: `88a7ee489d9f62ac4943dff8b86330a57aa6b72e`. **설계 문서**이며 workflow·코드·Secret은 수정하지 않았다. CI 실행·이미지 빌드·배포도 하지 않았다.

## 현재 구현

| 근거 | 확인한 상태 |
|---|---|
| Git tree의 .github/workflows | 기준 커밋에 파일 없음. Actions runs 조회도 0건. “CI 통과” 근거 없음 |
| `package.json` | test=vitest run, build=tsc -b && vite build, test:e2e=playwright test |
| `backend/tests/conftest.py` | 테스트에서 .env 읽기를 막고 Gemini 키를 제거하는 fixture 존재 |
| `Dockerfile` | Node 22 빌드 후 nginx 80. 프런트엔드 전용 |
| `backend/Dockerfile` | 별도 FastAPI 컨테이너 |
| `docker-compose.yml` | frontend 8080 / backend 8000 / PostGIS 5432. DB 기동 healthcheck 존재 |
| `Dockerfile.aws` | React dist + FastAPI 단일 이미지, 8000. 모델·시설·사건 처리 자료 COPY |
| `docs/DEPLOY_AWS.md` | EC2·Caddy 단일 인스턴스 배포 **과거 기록**. 현재 URL 가용성은 이번에 확인하지 않음 |
| `backend/app/scenario_repository.py`, `main.health` | 시나리오 메모리 저장. /health의 database=demo-in-memory, postgis=pending |

Compose가 PostGIS를 띄우고 DATABASE_URL을 준다는 사실은 API가 PostGIS를 실제 저장소로 사용한다는 증거가 아니다. 단일 EC2 Docker 운영과 Kubernetes/EKS 운영은 별도다.

## 제안 파이프라인: 테스트 실패 시 뒤 단계 차단

Career [#51](https://github.com/ssoyoum/career/issues/51)에 대응하는 **미구현 설계**다.

1. PR·main push 트리거에서 checkout. Python 3.12(`Dockerfile.aws`와 일치), Node 22 기준으로 고정.
2. Python 의존성 설치 → 백엔드 테스트. 비밀값·운영 API 호출을 기본 CI에서 차단하고 필요한 replay 자료가 없으면 누락 자료를 명시해 실패 원인을 분류한다. 테스트를 삭제하거나 전부 skip해 통과시키지 않는다.
3. `npm ci` → 프런트엔드 단위 테스트 → TypeScript/Vite 빌드. lockfile 기준 설치. package-lock.json이 실제 checkout에 있는지 사전 확인.
4. 위 검증이 전부 성공한 후 Docker 이미지 build. AWS 이미지 COPY 입력의 포함/제외를 .dockerignore와 대조한다. 로컬 전용 대용량 자료가 필요한 경우 “공개 Git 소스만으로 동일 기능 이미지 재현 가능”으로 표시하지 않는다.
5. 기본 CI에서는 이미지 로컬 빌드까지. 레지스트리 push는 신뢰된 main 변경에 한정하고, 실제 배포는 별도 승인된 단계로 분리한다.

검증 가능한 기존 명령(원본 저장소 루트, 이번에는 미실행):

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests -q
npm ci
npm test
npm run build
docker build -f Dockerfile.aws -t floodops:local-ci .
```

독립 테스트 job을 병렬화할 수 있지만 Docker build/push/deploy는 의존성 성공 후에만 수행한다. workflow YAML은 이 작업에서 만들지 않는다.

## 캐시·태그·권한·실패 처리 제안

- pip 캐시는 OS·Python 버전·backend/requirements.txt hash, npm 캐시는 OS·Node 버전·package-lock.json hash 기준. node_modules 자체의 재사용을 설치 성공으로 간주하지 않는다.
- 테스트 캐시와 Docker layer cache를 구분한다. 비밀값·평가 원문·민감한 자료를 캐시에 저장하지 않는다.
- 릴리스 이미지는 `sha-<전체 commit SHA>`와 digest를 기록. latest만으로 배포 이력을 남기지 않는다. 직전 정상 digest를 보관한다.
- PR job은 contents:read만 기본. fork PR에는 모델·AWS·레지스트리 자격을 주지 않는다. push job에만 필요한 권한을 별도 부여한다.
- Gemini 키는 build ARG나 이미지 layer가 아니라 런타임 환경변수. 프런트엔드 VITE_* 값은 번들에 노출되므로 비밀값이 아니다.
- 실패하면 테스트 이름·traceback·관련 자료 경로·소스 SHA를 보관한다. 환경/의존성, 데이터 부재, 코드 회귀를 로그로 구분한다. continue-on-error로 필수 검증을 성공 처리하지 않는다.
- E2E는 `playwright.config.ts`의 두 서비스와 브라우저가 필요하다. replay fixture·모델 호출 차단을 확인한 뒤 별도 필수 job 채택 여부를 결정한다. 현재 “자동 E2E CI 실행”은 미구현이다.

## AWS 배포와 로컬 개발 구분

[DEPLOY_AWS.md](DEPLOY_AWS.md)가 EC2 배포 기록과 기존 이미지 재현 명령의 원본이다. 이 문서는 동일한 서버 주소·접속 명령·Secret 값을 복제하지 않는다. 현재 코드의 multi-case 지원이 과거 공개 이미지에도 있다는 보장은 없다.

승인 후 배포를 별도 작업으로 진행할 때 확인할 증거:

- 이미지 digest·commit·처리 자료 버전·서버 설정 및 시간.
- /health HTTP 200 **외에** /api/events와 필요한 사건 reconstruction, 정적 프런트와 Agent offline 도구 경로.
- docker stats의 실제 메모리, restart 횟수, 오류 로그, 직전 이미지 복원 결과.
- /health는 단순 고정 응답이므로 DB 연결·자료 최신성·모든 도구 준비 여부를 보장하지 않는다.

## 완료 조건과 다음 작업

- [ ] #51에서 workflow 구현 후 PR 검사에 백엔드·프런트엔드·이미지 build 결과 링크가 남음.
- [ ] 필수 실패가 push/deploy를 차단함을 실패 사례로 확인.
- [ ] 처리 자료 누락 범위와 실제 지원 기능을 배포 기록에 명시.
- [ ] 실제 배포 승인과 결과를 CI 성공과 구분.

다음 작업 하나: **#51의 CI 구현**. 이 문서 작성은 CI 구현/실행의 완료가 아니다. AI PR 리뷰어(#52)·CI 로그 에이전트(#53)는 먼저 읽을 CI 실패 로그가 안정적으로 생성된 뒤 검토한다.

