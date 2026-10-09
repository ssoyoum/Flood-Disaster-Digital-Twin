# FloodOps 최종발표 v3 · 편집 안내

BASEMENT 2차 발표자료(`Basement-Flood-Vulnerability/docs/submission/vworld-spatial-information-contest-8th/presentation`)와 같은 도구로 만든다.

- `slides.py`: 장별 내용. 각 함수가 (Canvas, 캡처 목록, 발표자 메모)를 돌려준다. 수치는 2026-10-10 로컬 API·테스트 기준이며 출처는 마지막 «출처» 장에 모인다.
- `build.py`: `python -X utf8 build.py` → `FloodOps_최종발표_v3.pptx`(SVG 그림 포함)와 `_호환용(PNG).pptx`. 글자·도형은 PowerPoint 기본 개체라 바로 고칠 수 있다.
- `finalize.ps1`: `powershell -ExecutionPolicy Bypass -File finalize.ps1 -Preview out\preview` → PDF와 장별 PNG.
- `assets/shots/`: 2026-10-10 로컬 화면 캡처(1600×1000). 화면 픽셀은 편집할 수 없고, 주변 설명만 도형이다.
- 필요한 것: Noto Sans KR(Regular·Bold) 설치, Chrome(SVG→PNG 렌더), python-pptx·lxml·Pillow·fontTools.
- `python -X utf8 build.py --only 7,9` 처럼 특정 장만 따로 파일로 뽑을 수 있다.
