# 로컬 Kubernetes 학습 계획

확인일: 2026-10-20. **미실행 실습 설계**다. 기준 구현은 Docker/Compose와 EC2 단일 컨테이너이며 Kubernetes manifest·workflow·EKS는 확인되지 않았다. 이 문서로 운영 경험을 추가하지 않는다.

## 현재 구성에서 달라지는 책임

| 현재 | kind 로컬 실습에서 배울 것 | 아직 얻지 못하는 증거 |
|---|---|---|
| Dockerfile.aws의 FastAPI+dist 단일 이미지 | Deployment가 Pod 재생성·이미지 revision 관리 | 분리된 서비스·운영 클러스터 아키텍처 설계 |
| EC2 localhost 8000 + Caddy 과거 기록 | ClusterIP Service + port-forward | AWS LB·인증서·DNS·EKS 운영 |
| Compose PostGIS 기동, 앱은 demo-in-memory | 저장소 전환 없이 앱 한 개 replica | PostGIS 연동·다중 replica 데이터 정합성 |
| 컨테이너 환경변수 | ConfigMap/Secret, Pod 재시작 시 설정 반영 | 비밀값 암호화·로테이션·권한 운영 |

첫 실습은 **kind 하나**로 한정한다. minikube를 함께 도입하지 않는다. Docker·kind·kubectl은 사용자가 준비한 환경에서 확인하고, 클라우드 노드·유료 자원은 생성하지 않는다.

## 실습 1 — 같은 이미지를 로컬 클러스터에서 실행

원본 checkout의 처리 자료·Docker build 입력을 먼저 확인한다. 아래 명령은 표준 kind/kubectl 절차를 제안한 것으로 이번에 실행하거나 설치 여부를 확인하지 않았다.

```bash
docker build -f Dockerfile.aws -t floodops:learning-v1 .
kind create cluster --name floodops-learning
kind load docker-image floodops:learning-v1 --name floodops-learning
kubectl create namespace floodops-learning
kubectl -n floodops-learning create deployment floodops --image=floodops:learning-v1 --port=8000 --replicas=1
kubectl -n floodops-learning expose deployment floodops --port=8000 --target-port=8000 --type=ClusterIP
kubectl -n floodops-learning rollout status deployment/floodops --timeout=180s
kubectl -n floodops-learning get pods,services
kubectl -n floodops-learning port-forward service/floodops 8000:8000
```

별도 터미널에서 `curl -fsS http://127.0.0.1:8000/health`와 `curl -fsS http://127.0.0.1:8000/api/events`를 확인한다. 정상 Pod·정적 페이지·사건 자료 가용성을 실행 기록에 남기면 완료다. 이미지 build가 실패하면 원자료/의존성/경로 문제를 해결하는 작업으로 되돌아가며 COPY를 무시하지 않는다.

메모리 기반 scenario_repository 때문에 replica는 1개로 유지한다. replica 2개로 늘려 일관된 서비스를 구현했다고 주장하지 않는다.

## 실습 2 — readiness/liveness와 자원 제한

새 YAML 파일은 이번에 생성하지 않는다. 후속 실습에서 `kubectl -n floodops-learning edit deployment/floodops`로 컨테이너에 다음 probe를 설정하는 방법을 배운다.

- readinessProbe: httpGet /health, port 8000, initialDelaySeconds 10, periodSeconds 5, failureThreshold 3.
- livenessProbe: httpGet /health, port 8000, initialDelaySeconds 30, periodSeconds 10, failureThreshold 3.
- 위 숫자는 **제안값**이다. 실제 startup 시간·자원 측정 후 조정한다.
- /health는 고정 응답이다. 프로세스의 응답성과 Service 수신 여부만 검사하며 PostGIS·모델·자료 신선도 readiness를 검증하지 못한다. 외부 모델 일시 장애를 liveness 실패로 연결해 재시작 루프를 만들지 않는다.

```bash
kubectl -n floodops-learning set resources deployment/floodops --requests=cpu=100m,memory=512Mi --limits=cpu=1,memory=1Gi
kubectl -n floodops-learning rollout status deployment/floodops --timeout=180s
kubectl -n floodops-learning describe deployment floodops
kubectl -n floodops-learning get endpoints floodops
kubectl -n floodops-learning logs deployment/floodops --tail=100
```

자원값 역시 실습 가설이며 기존 EC2 상한을 복사한 운영 권장치가 아니다. 완료 조건은 probe 설정과 Pod Ready·Service endpoint·재시작 횟수를 대조하고, 문제 발생 시 describe의 Events와 로그로 ImagePull/CrashLoop/OOM 등 원인을 구분하는 것이다. metrics-server가 없는 kind에서 kubectl top 결과를 가정하지 않는다.

## 실습 3 — 설정·Secret·데이터 범위

- 첫 실행에는 실제 모델 키를 넣지 않는다. 모델 없음과 도구 결과 반환 경로를 관찰한다.
- 일반 설정은 ConfigMap, 키는 Secret으로 분리하는 것이 **후속 구현 제안**이다. Secret은 기본적으로 base64 인코딩이며 그 자체가 암호화 보장은 아니다.
- 실제 Gemini 키 주입은 Live 호출 가능성을 열므로 별도 승인한 경우만 한다. 값을 YAML/Git/명령 기록/로그에 노출하지 않는다.
- 설정 이름은 기존 코드의 AGENT_LLM_PROVIDER, AGENT_ASK_TIMEOUT_SECONDS, FLOODOPS_TWIN_MODE, GEMINI_API_KEY를 재사용한다. 환경에 따라 replay/live 자료 연동 범위도 기록한다.
- 완료 조건: 비밀값을 표시하지 않는 설정 참조, 모델 미설정 동작, Pod 교체 후 메모리 시나리오 상태 소실을 관찰·기록. 영속 저장소 구현은 별도 작업이다.

## 실습 4 — rollout과 rollback

동일 코드를 두 번째 로컬 태그로 build해 배포 절차를 연습할 수 있다. 실제 기능 변경/성능 개선과 구분한다.

```bash
docker build -f Dockerfile.aws -t floodops:learning-v2 .
kind load docker-image floodops:learning-v2 --name floodops-learning
kubectl -n floodops-learning set image deployment/floodops floodops=floodops:learning-v2
kubectl -n floodops-learning rollout status deployment/floodops --timeout=180s
kubectl -n floodops-learning rollout history deployment/floodops
kubectl -n floodops-learning rollout undo deployment/floodops
kubectl -n floodops-learning rollout status deployment/floodops --timeout=180s
kubectl -n floodops-learning get deployment floodops -o jsonpath='{.spec.template.spec.containers[0].image}'
```

위 컨테이너명 floodops는 create deployment 명령으로 만든 이름을 가정한다. 실제 get deployment로 이름을 먼저 대조한다. 이미지 변경 전후·rollback revision·/health·사건 자료 응답을 남기면 완료다. rollback은 이미지/Pod template 복원이지 메모리 데이터 복원이 아니다.

## 실습 5 — Actions 연결은 설계까지만

[CI_CD_DESIGN.md](CI_CD_DESIGN.md)의 테스트 → 이미지 build → commit SHA 태그 → 레지스트리 push → 승인된 배포 → rollout 확인 → smoke → 실패 시 이전 digest 복원 순서를 학습한다. 현재 workflow는 없으며 레지스트리 자격·클러스터 접근·배포 코드는 별도 구현이다.

GitHub-hosted runner가 개인 PC kind에 자동으로 접근할 수 있다고 가정하지 않는다. 로컬 검증은 이미지 load 방식, 실제 AWS 배포는 레지스트리·권한·네트워크·클러스터 비용 검토가 각각 필요하다. EKS·Ingress·HPA·영속 볼륨·운영 모니터링은 이 로컬 학습의 완료 기준에 포함하지 않는다.

실습 종료 시 본인이 만든 클러스터만 `kind delete cluster --name floodops-learning`로 정리한다. 이 삭제 명령도 이번에 실행하지 않았다.

