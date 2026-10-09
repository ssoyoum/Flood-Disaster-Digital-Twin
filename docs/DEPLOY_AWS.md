# FloodOps AWS 배포 준비

## 현재 상태

- `Dockerfile.aws`는 React 빌드 결과와 FastAPI를 한 컨테이너에서 같은 출처로 제공한다. 앱 포트는 `8000`이다.
- 2026-10-01 배포: 공개 주소 `https://floodops.duckdns.org`(별칭 `https://floodops.54-180-81-225.sslip.io`). AWS 서울 리전(ap-northeast-2)의 기존 EC2 t3.micro 한 대에 컨테이너 `floodops`(127.0.0.1:8000, 메모리 600MB 상한)로 올리고, 같은 서버의 Caddy가 HTTPS를 처리한다.
- 서버 메모리(1GB)를 아끼려고 프런트엔드는 로컬에서 `VITE_API_BASE=same-origin`으로 빌드하고, 서버에서는 Python 런타임만 이미지로 빌드한다. Gemini 키는 이미지에 넣지 않고 서버의 root 전용 `/etc/floodops.env`를 `--env-file`로 넘긴다.
- 계정은 무료 요금제 크레딧으로 운영하므로 서버를 추가하거나 사양을 바꾸지 않는다. 사양 변경 시 재시작으로 공인 IP가 바뀐다.
- 현재 API의 시나리오 상태는 메모리에 있으며 `/health`는 `database: demo-in-memory`, `postgis: pending`을 반환한다. 단일 인스턴스 시연에 맞춘 구성이다.
- 사건 목록은 5개이며 `main`에서는 오송·서울 2022·포항 2022·안동·의성 2026 네 사례의 관제 화면과 반사실 분석이 동작한다. 익산 2024는 시각 근거가 없어 잠겨 있다.
- 2026-10-09 확인: 공개 서버는 10-01 빌드라 `/api/events`에는 5개 사건이 보이지만 `seoul-2022`·`pohang-2022`·`andong-uiseong-2026`의 `/reconstruction`은 404다. 다른 사례를 공개 화면에서 열려면 현재 `main`으로 이미지를 다시 빌드해 컨테이너를 교체해야 한다.

## 다른 사례까지 여는 재배포 준비 (2026-10-09)

이미지에 들어가야 하는 것과 확인한 값이다. 로컬 Docker가 없어 서버 Docker로 빌드한다.

- `Dockerfile.aws`는 `data/processed/{osong,seoul_2022,pohang_2022,andong_uiseong_2026}`을 모두 복사한다. 예전 `.dockerignore`의 `data/processed/seoul*` 줄이 `seoul_2022` 디렉터리까지 제외해 COPY가 실패했으므로, 지금은 원본 export 두 파일(`seoul_flood_footprints_2022.geojson`, `seoul_rainfall_2022_event.csv`)만 제외한다.
- 서버에 올리는 패키지는 지난 배포와 같이 `backend/app`, `backend/requirements.txt`, 위 네 데이터 폴더, 로컬에서 `VITE_API_BASE=same-origin npm run build`로 만든 `dist`(`index.html`이 가리키는 자산만)로 구성한다. 오송 건물 QA(31MB)·OSM 건물 두 파일·CODIL 텍스트는 뺀다. 서버 Dockerfile은 `Dockerfile.aws`의 Python 단계에서 `COPY --from=frontend-build /web/dist ./dist`를 `COPY dist ./dist`로 바꾼 것이다.
- 레이어 응답 크기(`/api/events/{id}/layers`, 5자리 좌표·화면 속성만, 2026-10-10 HAND 셀 포함): 오송 gzip 1.07 MB, 서울 1.18 MB, 포항 0.10 MB, 안동 0.35 MB.
- 메모리: 네 사례 레이어를 모두 읽은 뒤 Python 프로세스 RSS 364 MB(로컬 측정, 오송만 읽었을 때 259 MB). 컨테이너 상한 600 MB 안에 들어가지만 여유는 10-01 배포(291 MB)보다 줄어든다. 배포 뒤 `docker stats`로 확인한다.
- 배포 뒤 확인: `/health` 200, `/api/events` 5건, 네 사례 각각 `/api/events/{id}/reconstruction` 200, `/api/cases/lead-times` 200, 브라우저에서 사례 선택 → 서울·포항·안동 관제 화면과 반사실 비교가 열리는지 확인한다. 로컬에서는 `npm run test:e2e`의 `other-cases.spec.ts`가 같은 흐름을 검사한다.

## 빌드와 로컬 확인

저장소의 현재 작업 트리에서 이미지를 빌드한다. 오송 건물·도로의 일부 가공 파일은 Git에 추적되지 않고 로컬에만 있으므로, GitHub 소스만으로 다시 빌드한 이미지와 기능 범위가 달라질 수 있다. 배포 전에 해당 자료의 출처·이용 조건과 이미지 포함 여부를 확인한다.

```sh
docker build -f Dockerfile.aws -t floodops:challenge .
docker run --rm -p 8000:8000 floodops:challenge
```

다른 터미널에서 다음 응답을 확인한다.

```sh
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/events
curl -I http://localhost:8000/
```

브라우저에서 지도, 오송 재생, Agent 계획·승인·실행, 출처·한계 표시를 확인한다. 배포 시에는 HTTPS가 제공되는 AWS 진입점을 사용하고 컨테이너의 `8000` 포트를 연결한다. LLM 키는 이미지에 넣지 않고 필요할 때 런타임 비밀값으로 주입한다. 키가 없으면 규칙 플래너를 사용한다.

## 배포 기록에 남길 항목

AWS 계정의 승인된 리전·서비스, 이미지 식별자, 공개 URL, 배포 시각, `/health` 및 `/api/events` 응답, 브라우저 시연 결과를 기록한다. 이 확인 전에는 공모전 문서에 배포 완료라고 쓰지 않는다.
