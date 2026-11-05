---
name: winter-lofi-playlist
description: 수노(Suno) 공식 MCP로 가사 없는 겨울밤 lofi 곡 여러 개를 만들고, 크로스페이드로 한 플리로 이은 뒤, 실사풍 눈 오는 창가 그림 위에 눈·불빛·김이 움직이는 이음새 없는 루프를 얹어 곡 제목이 뜨는 플레이리스트 영상(mp4)과 유튜브 타임스탬프까지 만든다. "겨울밤 플리 만들어 줘", "코딩할 때 듣는 lofi 플레이리스트 영상", "수노로 플리 영상", "눈 오는 lofi 플리", "winter lofi playlist", "lofi playlist video" 요청에 사용. 다른 계절·장소(비 오는 밤 등)의 무가사 플리도 같은 절차로 만든다.
---

# 겨울밤 lofi 플리 영상

말 한마디로 **곡 생성 → 고르기·다운로드 → 크로스페이드 믹스 → 배경 그림 → 눈 루프 → 플리 영상**까지 간다.
스크립트는 이 스킬 폴더의 `scripts/`에 있다(아래 `$S`). 작업 폴더는 사용자가 정하지 않으면 지금 폴더의 `winter-playlist/`(아래 `$W`).

```
$W/tracks/  NN_제목.mp3      ← 수노에서 받은 곡
$W/out/     playlist.mp3 · tracklist.json · timestamps.txt · loop.mp4 · playlist.mp4 · thumbnail.jpg
$W/bg/      prompt.txt · bg.png · scene.json · preview.png · check/
```

## 0. 준비 점검 (먼저, 매번)
1. `python3 $S/check_env.py` — numpy·Pillow·ffmpeg(libx264·libmp3lame·acrossfade·loudnorm)가 있어야 한다. 없으면 알려 준 설치 명령을 사용자에게 보여 준다.
2. 수노 MCP가 연결돼 있는지 본다(`account-usage` 같은 수노 도구). 없으면 멈추고 안내한다: 신청 https://suno.com/mcp, 서버 주소 `https://api.suno.com/mcp` (Claude 앱: 설정 → 커넥터 → 커스텀 커넥터 추가 / Claude Code: `claude mcp add --transport http suno https://api.suno.com/mcp` 후 `/mcp`에서 로그인).
3. `account-usage`로 **요금제·남은 생성 크레딧·다운로드 한도**를 읽어 사용자에게 한 줄로 알린다.
   - 읽을 칸: `credits_remaining`(생성), `download_credits_remaining`(다운로드), `allowed_models`. 한도와 충전 주기는 요금제·계정마다 다르니 숫자를 외워 두지 말고 매번 읽는다.
   - 이 스킬을 만들 때 무료 계정에서 잰 값: 곡 요청 1번 = 테이크 2개 = 10크레딧(6번 요청에 60크레딧).
   - **권리**: 무료 플랜으로 만든 곡은 상업적으로 쓸 수 없다(수익 창출 유튜브 포함). 유료 플랜 구독 중에 만든 곡이어야 한다 — 나중에 결제해도 예전 곡에 소급되지 않는다. 수익 창출 채널에 올릴 거면 시작 전에 이걸 말한다.

## 1. 곡 목록 (사용자와 짧게)
- 정할 것: 곡 수(기본 8), 곡 길이(기본 150초), 분위기(기본 「코딩할 때 듣기 좋은 겨울밤 lofi」). 사용자가 이미 말했으면 묻지 않는다.
- `references/prompts.md` 1절대로 **공통 스타일 고정 + 악기·BPM만 바꾼** 곡 목록 표를 만들어 보여 주고, 들 크레딧(곡 수 × 10 안팎)을 함께 적는다.

## 2. 생성
- 곡마다 `audio-create`: `instrumental: true`, `title`, `style`(공통 + 악기 + BPM), `duration`(15~360초), **`duration_strict: false`**(켜져 있으면 길이 상한에서 곡이 뚝 끊긴다 — 크로스페이드 플리에 나쁨). `description`과 `style`을 같이 보내면 400이다.
- **한꺼번에 많이 보내지 않는다** — 8개를 동시에 보냈더니 2개만 시작됐다. 2곡씩 보내고 `audio-wait`(`ids`로 묶어서, `until: "complete"`)로 기다린 뒤 다음 2곡.
- 받은 clip id를 곡별로 `$W/tracks/clips.json`에 적는다: `[{"n":1,"title":"Snowfall Terminal","style":"…","ids":["테이크1","테이크2"]}, …]`(1번 테이크가 기본, 2번은 교체용).
- 결과를 표로 보여 준다: 번호 · 제목 · 길이 · suno.com 링크. 들어 보고 바꿀 곡이 있으면 그 곡만 다시 만든다.

## 3. 고르기·다운로드
- 다운로드할 곡 = 기본은 각 곡의 1번 테이크. 다운로드 크레딧이 모자라면 몇 곡만 받을지 사용자에게 묻는다(가장 느린 곡을 마지막에).
- `audio-download`는 **먼저 `confirm` 없이** 부른다. `requires_credit`이 오면 "다운로드 크레딧 N개를 씁니다"라고 묻고, 허락받은 뒤에만 `confirm: true`. 한 번 허락은 그 곡들에만.
- 받은 `url`을 `$W/tracks/NN_Title_With_Underscores.mp3`로 저장한다(`curl -L -o`).
- **하지 말 것**: 비공개 곡 cdn 주소를 긁거나, 곡을 공개로 바꿔 스트리밍 주소로 받거나, 브라우저 흉내 헤더로 차단을 피하는 것. 다운로드는 `audio-download`로만. 크레딧이 없으면 남은 만큼만 쓰거나 다음 날(재충전) 이어서 한다.

## 4. 믹스
```bash
python3 $S/mix.py $W/tracks/*.mp3 -o $W/out --xfade 3
```
`playlist.mp3`(−14 LUFS), `tracklist.json`, `timestamps.txt`가 나온다. 제목을 파일 이름과 다르게 띄우려면 `--titles titles.txt`.

## 5. 배경 그림
- 사용자가 그림을 주면 그걸 쓴다(쓸 권리가 있는 것만). 아니면 `references/prompts.md` 2절 프롬프트로 codex 이미지 생성 → `$W/bg/bg.png`.
- 그림을 직접 열어 본다: 글자·워터마크가 없는지, 창이 넓게 보이는지, 16:9인지. 아니면 다시 만든다.

## 6. 장면 표시 (scene.json) — 눈이 어디 내리고 무엇이 가리는지
그림을 보고 `$W/bg/scene.json`을 쓴다. 좌표는 **원본 그림 픽셀**. 견본: `examples/scene.json`(+ `examples/window_night.png`).
- `snow.region`: 눈이 보이는 유리창 다각형. `count` 300~700, `size` 1, `speed` 1(정수).
- `occluders`: 유리 **앞에** 선 물건 다각형(노트북·스탠드 갓·머그·화분…). `occluder_lines`: 가는 막대 `[x1,y1,x2,y2,굵기]`(스탠드 팔).
- `lights`: 불빛 `{x,y,r,color,alpha,sx,sy,flicker:{amount,waves:[[주기수,위상,무게]]}}`. 가로등은 `lights_snow: true`(그 근처 눈이 밝아짐), 바닥에 번진 빛은 `sx:1.8, sy:0.45` 타원. alpha는 0.06~0.2 — 세면 사진이 뿌옇게 뜬다.
- `steam`: 김 나는 자리(머그 입구) `{x,y}`. 없으면 빈 배열.
- `camera`: `zoom` 1.02~1.04, `drift` 10~16px. 고정하려면 `zoom: 1, drift: 0`.

확인 — 눈으로 맞춘다:
```bash
python3 $S/scene_preview.py $W/bg/scene.json -o $W/bg/preview.png --grid   # 처음엔 --grid로 좌표 읽기
```
`preview.png`를 열어 청록(눈 창)·빨강(가림)·노랑(불빛)·흰 점(김)이 그림과 맞는지 본다. 어긋나면 고쳐 다시. 처음 좌표를 잡을 때는 `--grid` 눈금을 읽어 정한다.

## 7. 루프 렌더
```bash
python3 $S/render_loop.py $W/bg/scene.json --check -o $W/bg/check     # 정지 화면 3장 + 이음새 검사
python3 $S/render_loop.py $W/bg/scene.json -o $W/out/loop.mp4         # 30초 루프(1080p 30fps, 수 분)
```
- `--check` 출력의 `seam_ok`가 true여야 한다(모든 움직임이 30초에 정수 번 돌아 처음·끝 프레임이 같다).
- 정지 화면을 열어 본다: 눈이 물건 앞에 그려지지 않았는지, 창틀 밖으로 새지 않았는지, 불빛이 과하지 않은지. 이상하면 6으로.
- 느리면 `--size 1280x720`으로 먼저 본다. `--seconds × --fps`는 정수여야 한다.
- 그림이 16:9가 아니면 위아래(또는 양옆)가 잘린다. 정지 화면으로 잘린 모습을 확인한다.

## 8. 플리 영상
```bash
python3 $S/assemble.py --loop $W/out/loop.mp4 --mix $W/out -o $W/out/playlist.mp4 --label "Winter Night Coding"
```
- 루프를 음원 길이만큼 잇고, 왼쪽 아래에 「번호 / 전체 · ♪ 곡 제목」을 곡마다 띄운다(`--title-secs 12`면 곡 시작 12초만). 처음 2초·끝 3초 페이드.
- 시간이 든다: 1080p에서 대략 플리 길이의 0.5~1배(10분 플리 ≈ 5~10분). 백그라운드로 돌리고 기다린다.
- 한글 제목이면 한글 글꼴이 필요하다(mac은 자동, 리눅스는 Noto CJK, 없으면 `--font`).
- 다 되면 `ffprobe`로 길이가 `tracklist.json`의 total과 맞는지, 중간·곡 바뀌는 지점 프레임을 한두 장 뽑아 제목이 맞게 바뀌는지 본다.

## 9. 넘겨줄 것
- 파일: `playlist.mp4`, `thumbnail.jpg`(글자 없는 장면 — 썸네일 문구는 따로), `timestamps.txt`(설명란용).
- 한 줄 요약: 곡 수·총 길이·쓴 생성 크레딧·다운로드 크레딧.
- 권리 한 줄: 요금제가 무료였으면 "상업 이용(수익 창출 채널 포함) 불가"를 다시 적는다. 유튜브에 올릴 때 AI 생성 음악이라고 설명란에 밝히기를 권한다.
