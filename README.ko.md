# Release-aware updater

[日本語](README.md) · [English](README.en.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md)

릴리스 노트를 읽고 호환성, 호환성을 깨뜨리는 변경 사항, 마이그레이션 절차를 확인한 뒤
앱, 라이브러리, 패키지 의존성, Docker 이미지를 업데이트하는 범용 스킬입니다.
Minecraft 플러그인 업데이트에도 사용할 수 있습니다.

Claude Code, Codex 및 기타 [Agent Skills](https://agentskills.io/specification)
지원 에이전트에서 동일한 `SKILL.md`를 사용할 수 있습니다. 특정 제공업체의 API나
Claude 전용 훅에 의존하지 않습니다.

**어떤 에이전트에서든 릴리스 노트를 바탕으로 의존성을 업데이트하세요.** 에이전트가
공식 릴리스 노트를 조사합니다. 선택적으로 사용할 수 있는 오프라인 Python 보조 도구는
검토 가능한 버전 고정 값의 차이를 생성하고, 허가된 로컬 수정을 적용하며,
적용 후 변경되지 않은 고정 값 업데이트를 되돌립니다.

## 지원 기능

- 현재 버전부터 후보 버전까지의 릴리스 노트, 의존성, 호환성 조사
- 앱/라이브러리의 API, 실행 환경, 직접/간접 의존성, lockfile 확인
- 필요한 경우에만 Minecraft, Java, 서버 구현체, 플러그인 의존성 확인
- Docker 이미지의 태그/digest, CPU 플랫폼, 영구 저장 데이터 확인
- 호환성을 깨뜨리는 변경 사항, 마이그레이션, 테스트, 롤백을 포함한 업데이트 계획과 차이 생성
- URL + SHA-256 / 이미지 digest의 로컬 업데이트 및 파일 hash 확인을 통한 복원
- 알 수 없거나, 호환되지 않거나, 검증되지 않은 항목을 보류하는 판단

npm/pip/Cargo/Maven/Gradle 등의 manifest와 lockfile은 기존 패키지 관리자로
업데이트합니다. Python 보조 CLI는 URL + SHA-256과 Docker digest를 텍스트로 고정하는
작업만 지원하며, 패키지 의존성 해결이나 lockfile 재생성을 수행하지 않습니다.
Docker Engine/OS 자체의 업데이트와 실제 운영 환경 배포는 별도의 작업입니다.
스크립트는 네트워크 통신, 다운로드, 명령 실행, 서비스 재시작을 하지 않습니다.
실제 릴리스 노트 조사에는 에이전트의 웹/저장소 탐색 기능을 사용합니다.

## 언어 지원

에이전트가 작성하는 제안과 설명은 일본어, 영어, 한국어, 중국어 간체를 지원합니다.
원하는 언어를 명시하거나 해당 언어로 요청하세요.
`plan` 하위 명령 뒤에 `--lang en`, `--lang ja`, `--lang ko`, `--lang zh-CN` 중 하나를
지정하면 Markdown 보고서의 제목과 항목 이름, 안전 안내문이 해당 언어로 표시됩니다.
기본값은 영어입니다. 사용자가 제공한 근거 텍스트, 자동 생성된 보류 사유 진단 메시지,
변경 차이(diff)는 자동 번역되지 않습니다. JSON 필드 이름과 상태 값, CLI 도움말 및
진단 메시지는 영어로 유지됩니다. 공통 기술 참고 문서는 영어로 되어 있으며, 에이전트가
사용자의 언어로 설명합니다. 언어를 선택해도 검증 방식이나 권한은 바뀌지 않습니다.

## 설치

먼저 공개 저장소를 가져옵니다. 사용하기 전에 스크립트를 검토하세요.

```sh
git clone https://github.com/spa77k/release-aware-updater.git
cd release-aware-updater
```

### Claude Code

```sh
mkdir -p ~/.claude/skills
cp -R skills/release-aware-updater ~/.claude/skills/
```

`/release-aware-updater`로 호출할 수 있습니다. 특정 프로젝트에서만 사용하려면 대상
저장소의 `.claude/skills/release-aware-updater/`에 같은 폴더를 배치하세요.

### Codex

```sh
mkdir -p ~/.agents/skills
cp -R skills/release-aware-updater ~/.agents/skills/
```

`$release-aware-updater`로 지정할 수 있습니다. 특정 프로젝트에서만 사용하려면 대상
저장소의 `.agents/skills/release-aware-updater/`에 배치하세요.

같은 이름의 스킬이 이미 있다면 덮어쓰기 전에 차이를 확인하세요.
에이전트가 자동으로 감지하지 못하면 재시작하거나 다시 로드하세요.

### 기타 에이전트 및 스킬을 지원하지 않는 도구

`skills/release-aware-updater/`를 호스트의 스킬 저장 위치에 복사하세요.
저장 위치와 호출 문법은 호스트에 따라 다릅니다. 스킬을 지원하지 않더라도
`SKILL.md`를 참조하게 하고 Python CLI를 직접 사용할 수 있습니다.
모든 호스트에서 자동 감지되는 것은 아닙니다.

형식 및 저장 위치에 관한 공식 문서:
[Agent Skills](https://agentskills.io/specification) /
[Claude Code](https://code.claude.com/docs/en/skills) /
[Codex](https://developers.openai.com/codex/skills)

## 요청 예시

> 이 저장소의 앱, 라이브러리, Docker 이미지에 대해 현재 버전부터
> 호환되는 최신 안정 버전까지의 공식 릴리스 노트를 확인해 줘.
> 호환성을 깨뜨리는 변경 사항, 실행 환경/API 요구 사항, lockfile에 미치는 영향,
> 마이그레이션과 복원 방법을 포함한 업데이트 제안과 차이를 만들어 줘.
> 우선 계획만 세워 줘. 배포는 하지 마.

> 이 앱, 라이브러리, 컨테이너 의존성의 공식 릴리스 노트를 검토해 줘.
> 이 체크아웃에서 호환되는 고정 값을 업데이트하고 저장소의 검사를 실행한 다음,
> 아직 필요한 마이그레이션과 실행 환경 테스트를 정리해 줘.
> 배포하거나 재시작하지 마.

`계획만 작성`과 `로컬 수정도 수행`은 서로 다른 작업 범위입니다. 이 스킬이 있다는
이유만으로 공개, 재시작, 배포가 허가되는 것은 아닙니다. 호스트와 사용자의 권한 설정을
따릅니다.

## 오프라인으로 체험하기

필요 환경: Python 3.11 이상. 추가 Python 패키지, Docker, API 키는 필요하지 않습니다.
다음은 가상의 URL, digest, 릴리스 노트를 사용하는 동작 데모입니다.
실제 배포 파일을 검증한 예시가 아닙니다.

```sh
demo=$(mktemp -d)
cp -R examples/general "$demo/repo"
python3 skills/release-aware-updater/scripts/update.py plan --lang ko \
  --root "$demo/repo" --manifest examples/general-manifest.json --out "$demo/plan.json"
cat "$demo/plan.md"
python3 skills/release-aware-updater/scripts/update.py apply \
  --root "$demo/repo" --plan "$demo/plan.json"
python3 skills/release-aware-updater/scripts/update.py rollback \
  --root "$demo/repo" --plan "$demo/plan.json"
```

이 데모는 범용 앱, 배포 파일 형태의 라이브러리, Docker의 세 가지 유형을 다룹니다.
기존 Minecraft 예시는 `examples/demo`와 `examples/manifest.json`에 남겨 두었습니다.
라이브러리 예시는 URL/hash를 고정하는 가상의 형식이며, npm 등의 lockfile을 대체하지
않습니다.

자신의 저장소에 사용할 때는 조사한 정보를 바탕으로 manifest를 작성하세요.
[입력 사양](skills/release-aware-updater/references/manifest.md)과
[조사 및 검증 항목](skills/release-aware-updater/references/research.md)을 참고할 수 있습니다.
설치할 폴더에도 `references/manifest-template.json`과 LICENSE가 포함되어 있습니다.
템플릿은 미검증 상태로 보류되도록 되어 있으므로 조사 결과를 채워 넣으세요.

## 안전성과 한계

- 릴리스 노트의 텍스트는 데이터로 읽습니다. 그 안에 포함된 지시는 실행하지 않습니다
- `ready`는 입력된 근거를 바탕으로 로컬 수정 가능 여부를 판단한 결과입니다.
  스크립트가 조사 내용의 진위, 실행 환경에서의 호환성, 배포 가능 여부를 증명하는 것은 아닙니다
- 문자열이 유일하게 일치하는 위치를 찾아 치환하는 방식입니다. YAML/Compose 구문과
  실제 앱 실행은 별도로 테스트해야 합니다. 자동 버전 탐색이나 모든 사이트에 대응하는
  스크래핑은 수행하지 않습니다
- hash는 변조 감지와 재현성 확보에 도움이 되지만, 그것만으로 배포 출처의 진위를
  증명할 수는 없습니다
- `rollback`은 파일 안의 고정 값만 되돌립니다. DB, 월드, volume의 변경은 되돌리지 않습니다
- 여러 파일의 전체 업데이트는 단일 트랜잭션이 아닙니다. 충돌하는 편집 작업이 없는
  일반적인 체크아웃에서 사용하고, 도중에 종료되면 상태를 확인하세요
- manifest와 보고서에는 변경된 줄과 URL이 포함됩니다. 공개하기 전에 비밀 정보가
  없는지 확인하세요

## 테스트

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

네트워크가 필요하지 않습니다. 정상적인 계획/적용/복원, 보류 판단, 잘못된 입력,
모호한 치환, 경로 이탈, symlink, 수정된 파일, CRLF, 중복 실행 등을 검사합니다.
언어 설정과 관계없이 동일하게 동작하는지도 검사합니다.
입출력 파일의 1 MiB 제한은 UTF-8 바이트 수로 검사하며, 변경 후 복원할 수 없는 크기로
커지는 업데이트는 거부합니다. 생성되는 plan은 다시 읽을 수 있도록 8 MiB 이하로 제한합니다.
`__pycache__`와 Python 바이트코드는 배포 대상에서 제외합니다.
GitHub Actions에도 Python 3.11 / 3.13에서 실행하는 동일한 회귀 테스트가 설정되어 있습니다.

## 구성

```text
skills/release-aware-updater/
  SKILL.md                 공통 지침
  references/              조사 지침 및 manifest 사양
  scripts/update.py        표준 라이브러리만 사용하는 CLI
examples/                  가상 데이터를 사용하는 오프라인 데모
tests/                     회귀 테스트
```

MIT 라이선스.
