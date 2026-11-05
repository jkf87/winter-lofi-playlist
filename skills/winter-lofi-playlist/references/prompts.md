# 프롬프트·곡 목록 견본

## 1. 곡 목록 짜기 (기본 8곡, 곡마다 2분 30초 안팎)

모든 곡에 **같은 분위기 키워드**를 넣고, **악기와 템포만** 바꾼다. 그래야 한 플리로 이어 들어도 튀지 않는다.

공통 스타일(모든 곡 앞에 붙임):
```
lofi hip hop, instrumental, winter night, snowfall, cozy, warm vinyl crackle, soft tape saturation, mellow, relaxing, coding music
```

| # | 제목 | 악기·질감 (공통 스타일 뒤에 붙임) | BPM |
|---|---|---|---|
| 1 | Snowfall Terminal | soft rhodes, brushed drums, warm sub bass | 72 |
| 2 | Frosted Window | nylon guitar, gentle chimes, dusty boom bap | 76 |
| 3 | Midnight Streetlamp | jazz piano, upright bass, swing drums | 80 |
| 4 | Quiet Drift | music box, ambient pad, distant wind | 66 |
| 5 | Hot Cocoa Debug | warm bass, wurlitzer keys, loose groove | 74 |
| 6 | Blue Hour Commit | dreamy synth arpeggio, slightly brighter beat | 84 |
| 7 | Icicle Loop | glockenspiel, bells, minimal percussion | 70 |
| 8 | Last Train Home | slow piano, string pad, nostalgic ending | 62 |

`audio-create` 한 번 = 곡 하나(테이크 2개). 인자:
```json
{"instrumental": true, "title": "Snowfall Terminal",
 "style": "lofi hip hop, instrumental, winter night, snowfall, cozy, warm vinyl crackle, soft tape saturation, mellow, relaxing, coding music, soft rhodes, brushed drums, warm sub bass, 72 bpm",
 "duration": 150, "duration_strict": false}
```
마지막 곡은 가장 느린 곡으로 두면 끝맺음이 자연스럽다.

다른 계절·장소로 바꿀 때는 공통 스타일의 `winter night, snowfall`과 배경 그림 프롬프트만 바꾼다
(예: `rainy night, rain on window` / `autumn evening, falling leaves`). 눈 대신 비라면 scene.json의
`snow.size`를 0.6, `speed`를 2로 두고 `count`를 늘린다.

## 2. 배경 그림 (codex 이미지 생성)

`$W/bg/prompt.txt`로 저장하고 codex에 넘긴다:
```
이미지 생성 도구를 바로 호출해서 그림 1장을 만들고 bg.png(16:9 가로, 1920x1080 이상)로 이 폴더에 저장하세요. 다른 파일은 만들지 마세요.
실사 사진처럼(시네마틱, 35mm, 얕은 심도, 자연스러운 노이즈). 글자·로고·워터마크·사람은 넣지 마세요.
장면: 눈 오는 겨울밤, 실내에서 큰 창밖을 본다. 창밖 가로등 아래로 눈이 내리고, 멀리 눈 덮인 집 몇 채에 따뜻한 창불.
창가 나무 책상 위에 코드가 떠 있는 노트북(화면은 오른쪽을 향해 비스듬히), 따뜻한 놋쇠 스탠드 불빛, 김이 나는 머그컵.
창유리 가장자리에 성에. 색은 짙은 남색 밤 + 주황 불빛. 창이 화면 가로 60% 이상을 차지하게.
```
실행:
```bash
codex exec --skip-git-repo-check -s workspace-write -C "$W/bg" - < "$W/bg/prompt.txt"
```
그림을 만들지 않고 계획만 말하고 끝나면 첫 줄에 「설명하지 말고 다음 행동으로 이미지 생성 도구를 호출하라」를 붙여 한 번 더 돌린다.
codex가 없으면 사용자에게 그림을 받는다(직접 찍은 사진이나 쓸 권리가 있는 그림만).

## 3. 사용자에게 보여 줄 플리 영상 설명란 견본

```
코딩할 때 듣기 좋은 겨울밤 lofi 플레이리스트 ❄️

{timestamps.txt}

음악: Suno로 생성(가사 없는 연주곡) · 영상: 생성 이미지 + 직접 만든 눈·불빛 루프
```
