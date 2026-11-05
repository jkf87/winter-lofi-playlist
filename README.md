# winter-lofi-playlist

**말 한마디로 「코딩할 때 듣기 좋은 겨울밤 lofi 플레이리스트」 영상을 만드는 에이전트 스킬.**

수노(Suno) 공식 MCP로 가사 없는 곡을 여러 개 만들고 → 크로스페이드로 한 플리로 잇고 →
실사풍 눈 오는 창가 그림 위에 눈·불빛·김이 움직이는 **이음새 없는 루프**를 얹어 →
곡 제목이 뜨는 플레이리스트 영상(mp4)과 유튜브 타임스탬프까지 뽑습니다.

![장면 예시](docs/still.jpg)

```
수노 MCP ─ 곡 8개(2분 30초 안팎) ─ 고르기·다운로드 ─┐
                                                   ├─ mix.py ──── playlist.mp3 · timestamps.txt
codex 이미지 생성(또는 내 사진) ─ scene.json ─ render_loop.py ── loop.mp4 (30초, 처음·끝 프레임 일치)
                                                   └─ assemble.py ─ playlist.mp4 · thumbnail.jpg
```

## 무엇이 들어 있나
| 파일 | 하는 일 |
|---|---|
| `SKILL.md` | 에이전트가 따라 하는 절차(점검 → 곡 목록 → 생성 → 다운로드 → 믹스 → 그림 → 장면 표시 → 루프 → 합치기) |
| `scripts/check_env.py` | numpy·Pillow·ffmpeg(+필터·인코더)·codex 확인 |
| `scripts/mix.py` | 곡들을 크로스페이드로 잇고 −14 LUFS로 맞춤, 곡 시작 시각표·설명란 타임스탬프 |
| `scripts/scene_preview.py` | scene.json(눈 내리는 창·가리는 물건·불빛·김 자리)을 그림 위에 그려 확인 |
| `scripts/render_loop.py` | 사진 + scene.json → 눈·불빛 흔들림·김·카메라 숨쉬기 루프. 모든 움직임이 루프 길이 안에서 정수 번 돌아 처음·끝 프레임이 같다(`--check`로 검사) |
| `scripts/assemble.py` | 루프를 음원 길이만큼 잇고 곡 제목(번호 / 전체 · ♪ 제목)을 띄움, 페이드, 썸네일용 장면 |
| `references/prompts.md` | 곡 목록 견본(공통 스타일 + 악기·BPM), 배경 그림 프롬프트, 설명란 견본 |
| `examples/` | 견본 그림 `window_night.png` + 맞춰 둔 `scene.json` — 바로 돌려 볼 수 있다 |

다른 의존(모션 프레임워크·브라우저·Node)은 없습니다. Python + numpy + Pillow + ffmpeg면 됩니다.

## 설치
Claude Code:
```bash
git clone https://github.com/jkf87/winter-lofi-playlist.git
mkdir -p ~/.claude/skills
ln -s "$PWD/winter-lofi-playlist/skills/winter-lofi-playlist" ~/.claude/skills/winter-lofi-playlist
python3 -m pip install numpy Pillow   # ffmpeg는 brew/apt/winget으로
```
또는 `npx skills add jkf87/winter-lofi-playlist`.

수노 MCP 연결(얼리 액세스 신청 필요, https://suno.com/mcp):
```bash
claude mcp add --transport http suno https://api.suno.com/mcp
```
그다음 Claude Code에서 `/mcp` → suno → 로그인. Claude 앱은 설정 → 커넥터 → 커스텀 커넥터 추가에 같은 주소.

## 쓰기
```
코딩할 때 듣기 좋은 겨울밤 lofi 플레이리스트 8곡 만들어서 플리 영상까지 뽑아 줘
```
곡 없이 루프만 먼저 보고 싶으면:
```bash
S=skills/winter-lofi-playlist/scripts
python3 $S/render_loop.py skills/winter-lofi-playlist/examples/scene.json --check -o check/
python3 $S/render_loop.py skills/winter-lofi-playlist/examples/scene.json -o loop.mp4
```

## 알아 둘 것
- **크레딧**: 만들 때 무료 계정에서 잰 값은 곡 요청 1번 = 테이크 2개 = 10크레딧입니다. 한도·다운로드 크레딧은 요금제마다 달라서 스킬이 매번 `account-usage`로 읽고, 다운로드 크레딧은 쓸 때마다 허락을 받습니다.
- **시간**: 30초 루프 렌더 약 1분, 플리 영상 합치기는 1080p에서 플리 길이의 0.5~1배(M 시리즈 맥 기준).
- **권리**: 수노 무료 플랜으로 만든 곡은 상업적으로 쓸 수 없습니다(수익 창출 유튜브 포함). 유료 플랜 구독 중에 만든 곡이어야 하고, 나중에 결제해도 예전 곡에는 소급되지 않는다는 것이 수노 안내입니다. 올리기 전에 직접 확인하세요.
- **하지 않는 것**: 비공개 곡 주소 긁기, 공개 전환 후 스트리밍 주소로 받기, 차단 우회. 다운로드는 수노 MCP의 `audio-download`로만.
- 견본 그림 `examples/window_night.png`는 이 저장소를 위해 이미지 생성으로 만든 것입니다. 자유롭게 써도 됩니다.
- 처음 시연은 [huashu-motion 한국어판](https://github.com/jkf87/huashu-motion-ko)으로 루프를 만들었고, 이 스킬은 의존 없이 같은 효과를 내도록 파이썬으로 다시 짰습니다.

## English (short)
An agent skill that turns one sentence into a "winter night coding lofi" playlist video: generate instrumental tracks with the official Suno MCP, crossfade them into one mix (−14 LUFS, YouTube timestamps), and render a seamless snow / light-flicker / steam loop over a photoreal window image, then assemble an mp4 with now-playing titles. Pure Python (numpy, Pillow) + ffmpeg. Songs made on Suno's free plan are not licensed for commercial use.

MIT License.
