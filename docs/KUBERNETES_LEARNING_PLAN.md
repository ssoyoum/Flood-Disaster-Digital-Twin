# 로컬 Kubernetes 실행·복구 검증

2026-10-20: 설계만 있던 계획을 `deploy/local/floodops.yaml`과 kind 로컬 실행으로 옮겼다. **AWS EKS 운영·클라우드 배포 경험이 아니다.** 비용이 드는 자원·레지스트리 push·실제 키 주입은 하지 않았다.

## 현재 구현

| 요소 | 실제 구성·확인 | 보장하지 않는 것 |
|---|---|---|
| 이미지 | 기존 Dockerfile.aws의 FastAPI+dist, 로컬 learning-v1/v2 태그 | 서비스 분리·운영 최적화 |
| Deployment | replica 1, Recreate, imagePullPolicy Never | 메모리 시나리오의 영속성·다중 replica 일관성 |
| Service | ClusterIP 8000, 실제 EndpointSlice·port-forward 확인 | Ingress·DNS·외부 로드밸런서 |
| probe | /health readiness 5초/5초, liveness 30초/10초 | /health는 DB·모델·자료 최신성 검사 아님 |
| 자원 | requests 100m/512Mi, limits 1CPU/1Gi | 측정 기반 운영 권장 용량·부하 SLA |
| 설정 | replay·gemini ConfigMap, GEMINI_API_KEY가 빈 로컬 Secret | 키 로테이션·암호화·실제 모델 호출 |
| 서비스 계정 | token 자동 mount 비활성 | 전체 클러스터 보안 검증 |

## 정상 환경 재현 명령

Docker·kind·kubectl 설치 후 본인이 소유한 로컬 cluster에서만 실행한다. 명시적 context를 유지해 다른 cluster를 변경하지 않는다.

```bash
docker build -f Dockerfile.aws -t floodops:learning-v1 .
kind create cluster --name floodops-learning --wait 120s
kind load docker-image floodops:learning-v1 --name floodops-learning
kubectl --context kind-floodops-learning apply -f deploy/local/floodops.yaml
kubectl --context kind-floodops-learning -n floodops-learning rollout status deployment/floodops --timeout=120s
kubectl --context kind-floodops-learning -n floodops-learning get pods,service,endpointslices
kubectl --context kind-floodops-learning -n floodops-learning port-forward service/floodops 18080:8000
```

별도 터미널에서 `/health`, `/api/events`, `/`를 `http://127.0.0.1:18080`으로 확인한다. 실제 검사는 모두 HTTP 200, 사건 5건, Pod Ready=true·restart 0이었다. Pod 안의 Python urllib 검사도 통과했다. /health의 database는 demo-in-memory, postgis는 pending으로 표시됐다.

## 이번 관리형 컨테이너 환경의 차이

kind v0.31.0 / Kubernetes v1.35.0을 사용했다. 기본 생성은 kubelet의 `/dev/kmsg` 누락과 중첩 overlayfs `invalid argument`로 지연됐다. **본인이 만든 노드** `floodops-learning-control-plane`에 character device를 만들고, 그 노드 내부 containerd snapshotter만 native로 바꿔 기동했다. 외부 Docker daemon의 storage driver는 바꾸지 않았다.

이 환경에서는 `kind load docker-image`가 containerd transfer API의 `no unpack platforms defined`로 실패했다. 동일 Docker archive를 다음처럼 노드의 native snapshotter에 local import하여 해결했다. 일반 개발 PC에서도 이 우회가 필요하다고 가정하지 않는다.

```bash
docker save floodops:learning-v1 | docker exec -i floodops-learning-control-plane ctr --namespace k8s.io images import --local --platform linux/amd64 --snapshotter native -
```

HTTPS proxy CA는 이전 Docker 검증과 같이 임시 Dockerfile의 BuildKit secret mount로만 전달했다. 세션 인증서·실제 API 키·kubeconfig는 Git에 추가하지 않았다. 저장소 Dockerfile.aws는 변경하지 않았다.

## rollout·실패·rollback 실습 결과

1. 환경변수 `FLOODOPS_LEARNING_REVISION=2`로 Pod template을 바꾸고 rollout 성공, undo 후 Ready와 /health 복구를 확인했다.
2. 로컬에 없는 `floodops:learning-missing`으로 이미지를 바꿨다. `imagePullPolicy: Never`에 따라 ErrImageNeverPull, 20초 rollout timeout으로 실패했다. 실패를 무시하지 않고 undo한 뒤 Ready=true·restart 0·health 성공을 확인했다.
3. 최신 작업 소스의 learning-v2 이미지(SHA `8f60248a1ea039752f287a6ff584f08b1a5a0bb3482a5482f589ef51ffcd51ae`)를 load/import하고 rollout 성공, 이미지 안의 재생시각 전달 코드와 health를 확인했다. 이 이미지는 이후 감시 보드 후속 대화 수정 전의 검증 이미지이며 최종 commit의 이미지 검사는 Actions 결과를 기준으로 한다.

```bash
kubectl --context kind-floodops-learning -n floodops-learning set env deployment/floodops FLOODOPS_LEARNING_REVISION=2
kubectl --context kind-floodops-learning -n floodops-learning rollout status deployment/floodops --timeout=90s
kubectl --context kind-floodops-learning -n floodops-learning rollout undo deployment/floodops
kubectl --context kind-floodops-learning -n floodops-learning rollout status deployment/floodops --timeout=90s
kubectl --context kind-floodops-learning -n floodops-learning rollout history deployment/floodops
```

rollback은 Pod template 복원이며 메모리 상태 복원이 아니다. restart/liveness 실패를 고의로 발생시키는 검사는 이번에 하지 않았다. probe 설정과 Ready를 확인한 것과 장애 탐지 성능 검증을 구분한다.

## CI와 실제 배포 경계

현재 GitHub Actions는 테스트·offline 평가·브라우저 검사 → SHA 태그 이미지 build·network none smoke를 구현한다. registry push·kubectl 배포·EKS 접근 권한은 없다. 향후 실제 배포는 이미지 digest·자료 버전·Secret/OIDC·대상 환경·비용·rollback을 구체화한 뒤 별도 승인한다. GitHub runner에서 개인 PC kind로 자동 배포한다고 쓰지 않는다.

실습 종료 시 본인이 만든 cluster만 `kind delete cluster --name floodops-learning`로 정리한다. 이번 실습의 floodops-learning cluster와 노드는 실제로 삭제했다.
