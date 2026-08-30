# FloodOps Data

`data/`는 원본, 가공 결과, 데이터셋 메타데이터를 분리해 보관한다.

## 폴더

### `data/raw/`

출처에서 받은 원본 파일을 수정하지 않고 저장한다. 원본의 기준연도, 관측기간, 취득일, 파일 크기, 해시는 `data/manifests/`에 기록한다.

### `data/processed/`

분석이나 애플리케이션 사용을 위해 원본에서 파생한 파일을 저장한다. 원본을 덮어쓰지 않으며, 처리 결과에는 원본 파일과 처리 방법을 연결한다.

### `data/manifests/`

데이터 출처, 기준연도, snapshot, CRS, geometry, 레코드 수, 상태, 해시와 데이터 사용 정책을 기록한다. 데이터별 상세 상태의 기준 문서는 `data/manifests/source-availability.yml`이다.

## 사용 원칙

1. 원본은 `raw/`에 그대로 보존한다.
2. 가공본은 `processed/`에 별도 생성한다.
3. 원본과 가공본의 기준연도 및 취득일을 혼동하지 않는다.
4. 데이터 상태와 출처는 manifest를 먼저 확인한다.
5. 데이터 구조·우선순위·provenance 정의는 [DATA_GUIDE](../docs/DATA_GUIDE.md)를 따른다.
