# OpenLocal

> 내 하드웨어에서 가장 적합한 Local LLM 구성을 찾고, 실행하고, 성능까지 측정하는 오픈소스 도구.

OpenLocal은 하드웨어를 감지하고 재현 가능한 모델/런타임 프로필을 추천한 뒤, 안전하게 배포하고 실제 성능을 측정합니다.

> 현재 상태: **pre-alpha**. v0.1은 Ubuntu 22.04/24.04와 Windows 10 21H2+/Windows 11의 NVIDIA GPU 환경을 지원 대상으로 합니다.

## 빠른 시작

Python 3.11 이상이 필요합니다.

```bash
python -m pip install -e .
openlocal doctor
openlocal doctor --json
openlocal recommend
openlocal recommend --json
```

v0.1의 사용자 흐름은 다음 네 단계에 집중합니다.

```text
Hardware -> Recommendation -> Run -> Benchmark
```

v0.1 alpha 명령을 모두 구현했습니다.

```bash
openlocal install --dry-run
openlocal install --ui
openlocal start
openlocal status
openlocal logs vllm
openlocal bench
openlocal stop
openlocal update
```

설치는 OpenAI 호환 `/v1/models` 조회와 첫 token 생성이 모두 성공해야 완료됩니다. `--dry-run`은 파일 작성, image pull, container 시작 없이 생성될 Compose를 보여줍니다.

## 차별점

설치 자체는 기본 기능입니다. OpenLocal의 제품 가치는 다음에 있습니다.

- 하드웨어를 고려한 구성 추천
- 실행 환경을 프로필로 재현
- 동일한 방법론으로 측정한 벤치마크
- 커뮤니티가 PR로 확장할 수 있는 하드웨어/모델 데이터

## 기본 보안 원칙

- 서비스는 기본적으로 `127.0.0.1`에만 바인딩
- 텔레메트리 및 자동 업로드 없음
- 벤치마크 제출은 명시적 opt-in과 전송 전 미리보기 필수
- 컨테이너 버전 고정
- 프로필, Compose, 로그, 벤치마크 결과에 비밀정보 저장 금지

자세한 범위와 일정은 [NON_GOALS.md](NON_GOALS.md), [ROADMAP.md](ROADMAP.md), [CLI 명세](docs/CLI_SPEC.md)를 참고하세요.

Windows에서는 vLLM을 네이티브 실행하지 않습니다. WSL2와 Docker Desktop의 Linux container GPU passthrough를 사용합니다. 요구사항은 [Windows 지원 문서](docs/WINDOWS.md)에 정리되어 있습니다.
