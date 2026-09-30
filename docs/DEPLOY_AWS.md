# FloodOps AWS 배포 준비

## 현재 상태

- `Dockerfile.aws`는 React 빌드 결과와 FastAPI를 한 컨테이너에서 같은 출처로 제공한다. 앱 포트는 `8000`이다.
- 2026-10-01 배포: 공개 주소 `https://floodops.duckdns.org`(별칭 `https://floodops.54-180-81-225.sslip.io`). AWS 서울 리전(ap-northeast-2)의 기존 EC2 t3.micro 한 대에 컨테이너 `floodops`(127.0.0.1:8000, 메모리 600MB 상한)로 올리고, 같은 서버의 Caddy가 HTTPS를 처리한다.
- 서버 메모리(1GB)를 아끼려고 프런트엔드는 로컬에서 `VITE_API_BASE=same-origin`으로 빌드하고, 서버에서는 Python 런타임만 이미지로 빌드한다. Gemini 키는 이미지에 넣지 않고 서버의 root 전용 `/etc/floodops.env`를 `--env-file`로 넘긴다.
- 계정은 무료 요금제 크레딧으로 운영하므로 서버를 추가하거나 사양을 바꾸지 않는다. 사양 변경 시 재시작으로 공인 IP가 바뀐다.
- 현재 API의 시나리오 상태는 메모리에 있으며 `/health`는 `database: demo-in-memory`, `postgis: pending`을 반환한다. 단일 인스턴스 시연에 맞춘 구성이다.
- 사건 목록은 5개지만 분석 자료가 연결된 사건은 오송이다. 서울 2022 침수흔적 원본 19,881개 피처는 확보됐으나 사건 API에는 아직 연결되지 않았다.

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
