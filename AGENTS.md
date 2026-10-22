# AGENTS.md

This project generates "interview practice" YouTube videos with Manim: a question
and answer appear on screen, narrated by TTS, text revealing word-by-word in sync
with the narration. This file is the map for any agent picking the project back up.

A second, experimental video type (documentary/history-style "timeline" videos)
lives under `timeline_video/` — see its own section below. It's a separate
pipeline sharing only the TTS/theme/branding code described here.

## Environment (Windows)

- Python venv at `./venv` — always call `venv/Scripts/python.exe`, never a bare `python`.
- ffmpeg is installed via winget but is NOT on PATH in a fresh shell. Before running
  any `manim` or `ffmpeg` command, prepend its bin dir for that shell session:
  ```
  export PATH="/c/Users/NIS/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin:$PATH"
  ```
- MiKTeX (LaTeX) is installed, so `MathTex`/`Tex` work.
- `manim-voiceover`, `gtts`, and `edge-tts` are installed in the venv.
- SoX is installed via winget (as `sox_ng`, a maintained fork — the original
  `ChrisBagwell.SoX` winget package's Windows build lacks MP3 support, i.e.
  `libmad`, and can't read the mp3s edge-tts produces) but is NOT on PATH in a
  fresh shell, and manim-voiceover's `global_speed` narration-speed feature
  (used by the `narration_speed` config key in both pipelines) hard-depends on
  a binary literally named `sox`/`sox.exe` being found on PATH — the `sox`
  Python package shells out to that exact name, not `sox_ng`. The winget
  install only ships `sox_ng.exe`, so `sox.exe` here is a copy of it placed in
  the same folder (argv0 dispatch makes it identify itself as `sox` either
  way). Before any render that uses narration speed adjustment, prepend this
  dir too:
  ```
  export PATH="/c/Users/NIS/AppData/Local/Microsoft/WinGet/Packages/sox_ng.sox_ng_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
  ```
  With `narration_speed` left at the default `1.0`, SoX is never invoked and
  its absence is harmless — `manim_voiceover` just logs a "SoX could not be
  found!" warning at import and the `global_speed != 1` check short-circuits.
  Setting `narration_speed` to anything else without a working SoX used to
  crash the render outright with a bare `FileNotFoundError: [WinError 2]`
  (confirmed by testing) — `edge_tts_service.resolve_narration_speed()` now
  guards this: it does a real functional probe (synthesizes a tiny mp3 and
  round-trips it through SoX's `tempo` effect, not just `shutil.which("sox")`
  — the ChrisBagwell.SoX build above passed a plain existence check and still
  couldn't decode mp3) and falls back to `1.0` with a stderr warning instead
  of letting the crash happen. Both `interview_simulation.py` and
  `timeline_video/timeline_simulation.py` route `narration_speed` through it
  before constructing `EdgeTTSService`.

## Rendering

```
venv/Scripts/python.exe -m manim -ql interview_simulation.py InterviewSimulation --disable_caching
```
Quality flags: `-ql` (480p15, fast iteration) · `-qm` (720p30) · `-qh` (1080p60) · `-qk` (2160p60, final export).
Drop `--disable_caching` for real runs once a scene is stable — it's there to force
a clean re-render while testing animation changes.

**Visual verification pattern** used throughout this project (manim has no visual
test runner, so this is how every change actually gets checked): render at `-ql`,
then extract a frame and look at it:
```
ffmpeg -y -ss <seconds> -i <output.mp4> -frames:v 1 -update 1 "<scratchpad>/check.png"
```
then read that PNG with the Read tool. Never declare an animation change "done"
without having actually looked at a rendered frame.

## Architecture

`interview_simulation.py` is the entry point (`InterviewSimulation(VoiceoverScene)`).
`construct()`:
1. Loads `gui_config.json` (see schema below) via `load_gui_config()`, falling back
   to `DEFAULT_CONFIG` for anything missing, and to `interview_script.txt` if no
   `script_text` is set.
2. Sets the TTS voice (`edge_tts_service.EdgeTTSService`).
3. Draws the background — either the chosen theme's gradient (`themes.py`) or a
   user-supplied image (`background_image` config key), with a dark overlay for
   text legibility over a photo. If `background_video` is set instead, this step
   is skipped entirely (see "Background video" below) so the render has nothing
   opaque behind the Q&A content.
4. Plays the intro card if enabled (`branding.py`).
5. Parses the Q&A pairs and dispatches to the chosen **reveal style** (see below).
6. Plays the outro card if enabled.

### Reveal styles (pluggable)

How the Q&A text actually appears is a swappable module, selected by
`gui_config["reveal_style"]` through `STYLE_REGISTRY` in `interview_simulation.py`.

**Contract**: a file `style_<name>.py` exporting one function:
```python
def render(scene, pairs, theme):
    ...
```
- `scene` — the `VoiceoverScene` instance. Speech service is already set. A
  background is already drawn UNLESS your style has its own fixed look (see
  `style_terminal.py` for the pattern: draw your own full-frame `Rectangle` at
  `z_index=-10` at the top of `render()` to cover the caller's background).
- `pairs` — list of `(question, answer)` string tuples, in order.
- `theme` — dict from `themes.get_theme(name)`: `bg_colors`, `question_color`,
  `answer_color`, `accent_color`. A style with its own fixed palette (terminal,
  sticky notes, whiteboard) mostly ignores these; a style meant to adapt to any
  theme (chat bubbles, split screen, stacked) should use them.

Reuse `reveal_common.py` for anything text-reveal related — don't reimplement
voiceover-synced timing:
- `build_paragraph(text, font_size, max_width, color, font=None)` → word-wrapped
  `VGroup` of per-line `Text` mobjects + an ordered list of word-level reveal
  targets (geometric glyph groups of those line `Text`s, not separate `Text`
  instances — see the baseline/word-splitting notes below).
- `speak_and_reveal(scene, text, words)` → runs the `with scene.voiceover(...) as
  tracker:` block, reveals `words` via a word-by-word `LaggedStart(FadeIn(...))`
  timed to `tracker.duration` exactly (natural per-word jitter already applied),
  and waits out any leftover audio. **This is the only way text should be
  revealed** — it's what keeps visuals in sync with real spoken narration.
- `THINKING_PAUSE` — recommended pause between a question finishing and the
  answer starting.
- `speak_and_reveal(scene, text, words, voice=None)` — pass a
  `manim_voiceover` `SpeechService` instance to switch the narrator before
  this block (e.g. a different voice for the answer than the question).
  `interview_simulation.py` builds `scene.question_voice` / `scene.answer_voice`
  once in `construct()` from `gui_config`'s `voice`/`answer_voice` keys; every
  style's two call sites pass `voice=scene.question_voice` /
  `voice=scene.answer_voice`. A new style must do the same for multi-voice
  support to work.

`build_paragraph` also parses inline markdown-style emphasis in the source
text — `**bold**`/`__bold__`, `*italic*`, `==highlight==` (rendered in
`DEFAULT_HIGHLIGHT_COLOR`, overridable via the `highlight_color` kwarg) —
and strips the markers from the displayed words. Any style that calls
`build_paragraph` gets this for free. `style_terminal.py` and
`style_whiteboard.py` need a non-default font (Consolas / a handwriting font),
which `build_paragraph` itself doesn't take a `font=` kwarg for historically —
they call `reveal_common.build_styled_paragraph` (the shared implementation
behind `build_paragraph`) directly with `font=...`, rather than keeping their
own copy of the word-wrap logic. If you need a style with its own font, do
the same instead of reimplementing word-wrapping again.

**Baseline gotcha (hit once already, cosmetic but easy to reintroduce)**:
`build_styled_paragraph` renders each *line* as a single `Text` mobject
(markdown spans applied via per-word `t2c`/`t2w`/`t2s` index ranges), not one
`Text` per word. Don't go back to building independent per-word `Text`
mobjects and `VGroup(...).arrange(RIGHT, buff=...)`-ing them — Manim centers
each mobject's own bounding box when arranging, and words have different
bounding-box heights depending on whether they contain ascenders/descenders
(e.g. "a" has none, "with" has an ascender, "years" has a descender), so
centering them together visibly floats short words up or down off the line's
real baseline. One `Text` per line gets a correct shared baseline from Pango
for free.

**Word-splitting gotcha (hit once already, NOT cosmetic — silently drops
words/characters, easy to reintroduce)**: word-level reveal targets for a
line are produced by `_split_line_into_words(line_mobj, n_words)`, which
groups `line_mobj`'s rendered glyphs by detecting the horizontal gaps between
them (a word-separating space is a much bigger gap than normal kerning). Do
**not** replace this with `line_mobj[start:end]` character-index slicing,
even though it looks like the obvious approach and Manim's own `Text`
docstring describes indexing into "the rendered characters, i.e. the text
with whitespace removed". That promise doesn't hold in practice: Manim/Pango
does not guarantee one raw submobject per logical character. Confirmed by
direct measurement — a 44-character line rendered as 49 raw submobjects with
`disable_ligatures=True` (needed to stop "fi"/"fl"/"ffi" from merging into
one glyph, which would instead UNDER-count), because a dotted letter like "i"
renders as two disjoint paths (dot + stem) when ligatures are off. A fixed
per-word offset computed from word lengths then drifts out of alignment with
the real glyph positions as soon as a line contains a character like that,
quietly handing part of one word's reveal animation to its neighbor — in
testing this permanently hid "years of", most of "services,", "teams to",
and "to end." from one rendered sentence, while a correctness check that only
measured slice *lengths* (not actual glyph identity) passed, because a
Python slice always returns exactly `end - start` items regardless of
whether they're the right ones. Verify any change here by actually
color-coding each returned word group and rendering a static frame (see
git history around this note for the exact throwaway script), not by
asserting on lengths.

Current styles: `style_stacked.py` (default — Q shrinks to a top banner, A below),
`style_terminal.py` (green-on-black, Q/A as command/output, accumulates and
auto-scrolls). Shortlisted but not yet implemented as of this writing: chat
bubbles, split screen, sticky notes, whiteboard — check `STYLE_REGISTRY` in
`interview_simulation.py` for what's actually wired in before assuming a style
exists.

When adding a new style, give it its own `style_<name>.py` file (never edit
another style's file or `reveal_common.py`'s contract) so styles can be built in
parallel without merge conflicts, then add one line to `STYLE_REGISTRY`.

### Orientation (landscape / portrait)

`gui_config["orientation"]` is `"landscape"` (default, 16:9) or `"portrait"` (9:16,
for Shorts/Reels/TikTok). `InterviewSimulation.construct()` applies it FIRST,
before any mobject is created: for portrait it keeps `config.pixel_height` and
`config.frame_height` exactly as the `-ql`/`-qm`/`-qh`/`-qk` quality flag set
them, and derives a narrower `config.pixel_width`/`config.frame_width` from
them (`* 9 / 16`) — so quality flags still control output resolution, only the
aspect ratio changes. `frame_height` is never touched, which means any
layout constant measured along the Y axis (vertical positions, margins) is
automatically correct in both orientations; only X-axis / width-based
constants (max text width, bubble/panel/avatar horizontal positions, left/right
margins) need to react to orientation.

**Convention for any style (existing or new): never hardcode a width-based
layout constant as an absolute number.** Compute it from `config.frame_width`
inside `render()` (or another function called from `render()`), not as a
module-level constant — module-level constants are bound at import time,
before `construct()` has had a chance to set portrait's `frame_width`.
`reveal_common.py` has two small helpers for this:
- `build_paragraph(text, font_size, max_width=None, ...)` — omit `max_width`
  to get a sensible frame-relative default (`~0.77 * config.frame_width`,
  which equals the original hardcoded `11` in landscape).
- `is_portrait()` / `font_size_for(base_size)` — `font_size_for` shrinks a
  landscape-tuned font size for the narrower portrait frame (no-op in
  landscape).
See `style_chat_bubbles.py`, `style_split_screen.py`, `style_terminal.py`,
`style_podcast.py` for the pattern of branching a width constant (or, for
split_screen, the whole layout) on `config.frame_width < config.frame_height`.

**Gotcha already hit twice** (style_chat_bubbles.py's bubbles, style_sticky_notes.py's
notes): if a style wraps text to some `max_width` and then draws a background
shape around it sized as `text_width + 2 * PAD`, the frame-relative budget
passed as `max_width` must already have `2 * PAD` subtracted — otherwise the
background shape (text + padding) can still exceed the frame even though the
text itself fit. Always verify the full drawn shape's width against
`config.frame_width`, not just the wrapped text's width.

### Background video

`gui_config["background_video"]` (absolute path, default `null`) plays a looping
video behind the Q&A content instead of the theme gradient or `background_image`.
Manim has no live video-playback-inside-a-Scene primitive, so this is built as a
two-stage pipeline instead of a mobject:

1. **Render manim with a transparent background.** When `background_video` is
   set, `InterviewSimulation.construct()` skips drawing *any* opaque background
   layer (no gradient `Rectangle`, no `background_image` `ImageMobject`, no dark
   overlay) — see the `bg_video_path` branch in `construct()`. That alone does
   **not** make the output transparent; manim still encodes an opaque video
   unless told otherwise. The render command also needs manim's own
   `-t`/`--transparent` CLI flag (equivalently, `config.transparent = True`):
   ```
   venv/Scripts/python.exe -m manim -ql -t interview_simulation.py InterviewSimulation --disable_caching
   ```
   **Whoever wires this up in `app.py` must add `-t` to the manim invocation
   whenever `gui_config["background_video"]` is set** — the GUI's "background
   video" picker is meaningless without it. With `-t`, this manim/ffmpeg install
   (manim 0.22.0) writes a `.mov` using the `qtrle` codec and `argb` pixel format
   (confirmed via `ffprobe`) — not `.mp4` and not a `webm`+VP9 alpha variant,
   because manim only picks the VP9/webm route if the output format is
   explicitly set to webm; left at the default it always produces `.mov`/`qtrle`
   for transparent output. Nothing drawn where there's no mobject reads back as
   fully transparent (verified by compositing a test render over a solid red
   `color=red` frame with ffmpeg and seeing the red show through everywhere
   except the text/shapes).
2. **Composite with `add_background_video.py`** (standalone post-process script,
   modeled on `add_background_music.py`): takes that transparent `.mov` and the
   user's background video file, loops the background (via `-stream_loop -1` on
   the input, same technique `add_background_music.py` uses for looping audio)
   if it's shorter than the manim render, scales it to the manim output's exact
   resolution (`scale2ref`), and layers the manim content on top with ffmpeg's
   `overlay` filter (`format=auto` so the alpha channel is respected). Output is
   a normal opaque `.mp4` (`libx264`/`yuv420p`), narration audio passed through
   unchanged. `--no-loop` holds the background's last frame (via `tpad`) instead
   of looping once it runs out, rather than cutting to black.
   ```
   venv/Scripts/python.exe add_background_video.py <manim_transparent_output.mov> <background_video> \
       [--output path] [--loop | --no-loop]
   ```
   Like `add_background_music.py`/`burn_subtitles.py`, this is not wired into
   the main render — `app.py` (or whatever drives the pipeline) shells out to it
   as a post-process step after the manim render finishes.

### `gui_config.json` (project root, gitignored)

Written by `app.py` (or by hand for testing); read fresh on every render.
```json
{
  "script_text": null,            // string in "Q: ...\nA: ...\n\n" format; null = read interview_script.txt
  "voice": "en-US-AndrewNeural",  // edge-tts voice name, used for questions (and answers, if answer_voice is unset)
  "answer_voice": null,           // optional edge-tts voice name for answers only; null = same as "voice"
  "narration_speed": 1.0,         // playback-speed multiplier for both voices, via manim_voiceover's global_speed (passed to EdgeTTSService); 1.0 = unchanged. Anything other than 1.0 needs SoX on PATH (see "Environment" above) or the render crashes
  "theme": "midnight",            // key into themes.THEMES
  "background_image": null,       // optional absolute path to an image file
  "background_video": null,       // optional absolute path to a video file; see "Background video" above - requires rendering manim with -t/--transparent and post-processing with add_background_video.py
  "reveal_style": "stacked",      // key into STYLE_REGISTRY
  "orientation": "landscape",     // "landscape" (16:9, default) or "portrait" (9:16)
  "add_fillers": false,           // inject natural filler words ("um", "well", ...) into answers only, via filler_words.add_fillers
  "filler_rate": 0.15,            // roughly the probability of a filler at each eligible point; ignored if add_fillers is false
  "show_intro": false,
  "channel_name": "",
  "episode_title": "",
  "show_outro": false,
  "outro_message": "Thanks for watching! Like and subscribe.",
  "handle": ""
}
```
`DEFAULT_CONFIG` in `interview_simulation.py` is the source of truth for defaults —
keep it in sync if the schema changes.

## Other files

- `themes.py` — `THEMES` dict (`midnight`, `charcoal`, `daylight`, `neon`) + `get_theme(name)`.
- `branding.py` — `build_intro_card(channel_name, episode_title=None)`, `build_outro_card(message, handle=None)`.
- `edge_tts_service.py` — `EdgeTTSService(SpeechService)`, wraps `edge-tts` (free, no API key) for manim-voiceover.
- `burn_subtitles.py` — hardcodes the auto-generated `.srt` onto an exported mp4. `--style` accepts `default`/`bold` (fixed presets) or `theme:<theme_name>` (derives caption color from that theme's `accent_color`). Standalone CLI, not wired into the main render — `app.py` shells out to it.
- `add_background_video.py` — composites a manim transparent-background render (`-t`, `gui_config["background_video"]` set) on top of a looping background video via ffmpeg's `overlay` filter. See "Background video" above for the full pipeline and exactly what CLI flag triggers transparent rendering. Standalone CLI, same conventions as `add_background_music.py`; `app.py` shells out to it when a background video is uploaded.
- `batch_render.py` — renders every `.txt` script in a folder in one go, into `batch_output/`.
- `generate_metadata.py` — generates a suggested YouTube title/description/duration estimate from a script, pure local heuristics, no API calls. Also generates a `CHAPTERS:` section (YouTube-style `MM:SS Qn: ...` timestamps, one per Q&A pair), estimated with the same words-per-minute heuristic as the duration estimate plus `THINKING_PAUSE` between Q and A. YouTube requires at least 3 chapters with the first at 0:00 to actually display them — with fewer than 3 Q&A pairs the output includes an explicit note about this instead of silently producing an invalid list.
- `export_bundle.py` — one-command pipeline for a single script: validates, renders, generates metadata, and zips video+srt+metadata.txt into `export_bundle_output/<script_name>/` (+ a `.zip`). Glue code around the tools above, not a replacement for them.
- `export_dual.py` — like `export_bundle.py` but renders a script in BOTH landscape and portrait in one command (`--quality ql|qm|qh|qk`, `--theme`, `--voice`, `--answer-voice`, `--reveal-style`, `--output-dir`), into `export_dual_output/<script_name>/{landscape,portrait}.mp4` (+ `.srt` each). `app.py`'s "Export Both Orientations" button shells out to it with a temp script file written from the live textarea.
- `generate_thumbnail.py` — standalone Pillow-based YouTube thumbnail generator. `generate_thumbnail(title, subtitle=None, theme_name="midnight", output_path=..., width=1280, height=720)` reads `themes.get_theme()` for colors (no separate hardcoded palette) so the thumbnail matches the video's theme; auto-fits/wraps the title font. `app.py`'s "Generate thumbnail" button calls this directly (not a subprocess) using the current video's label/channel name/theme.
- `question_bank.py` — `TEMPLATES` dict of ready-made Q&A scripts by role (Backend/Frontend/Data Scientist/PM/DevOps/EM/QA/Behavioral, 5 pairs each), `list_templates()`, `get_template(name)`. Every template is valid `qa_format.parse_qa_text()` input. `app.py`'s template picker (above the script textarea) loads one into `k_script_text` directly, importable for any other use too.
- `filler_words.py` — `add_fillers(text, rate=0.15, seed=None)`, pure text transform (no manim/TTS coupling) that inserts natural-sounding filler words ("um", "well", "you know", ...) at sentence/comma/clause boundaries. Markdown-safe (never inserts inside a `**bold**`/`*italic*`/`==highlight==` span). `interview_simulation.py` applies it to answers only, before building `pairs`, when `gui_config["add_fillers"]` is true — so the filler words show up in both the on-screen text and the narration/subtitles, since they're all derived from the same (now-modified) text.
- `app.py` — Streamlit GUI wrapping the manim CLI render (question/answer voice — now 22 voices across 9 languages, theme, reveal style, orientation, quality/format pickers, background image/video upload, background music upload with loop toggle, caption burn-in toggle with theme-matched style option, filler-word toggle, intro/outro toggles, a template picker, progress bar + collapsed render log, video preview+download, thumbnail generation, dual-orientation export). Also hosts the **"🕰️ Timeline (Testing)"** tab for the `timeline_video/` pipeline — see that pipeline's own section above for what it wires up. Run with `venv/Scripts/python.exe -m streamlit run app.py`. First run on a machine may hit Streamlit's one-time email-onboarding prompt, which hangs in a non-interactive shell — pre-empt it with `~/.streamlit/credentials.toml` containing `[general]\nemail = ""`.
  - **Render chain**: manim renders first (forced to `.mov` + `-t` instead of the user's chosen format if a background video was uploaded, since that's what transparent rendering requires — see "Background video" above). The success path then chains, in order: `add_background_video.py` (if a background video was uploaded) → `add_background_music.py` (if a music file was uploaded) → `burn_subtitles.py` (if captions were requested), each step operating on the PREVIOUS step's output (`final_path`), not the raw manim output (`output_path`) — `output_path` is only still used afterward to locate the sibling `.srt` file, which manim always writes next to its own raw output regardless of what gets composited on top of it later. The result is saved to history via `sessions.py` and shown through `st.session_state["_display_video_path"]`.
  - **GPU-accelerated encoding**: `detect_gpu_encoder()` (cached via `@st.cache_resource`, so it only runs once per server process) does a real tiny test encode with `h264_qsv` (Intel Quick Sync) rather than just checking whether ffmpeg *lists* the encoder — a listed encoder can still fail to initialize without a matching GPU/driver. If the probe succeeds, `use_gpu=True` for the rest of that process's lifetime and every encode step in the chain picks up GPU acceleration automatically, with no user-facing toggle: manim's own render gets `--video-codec h264_qsv --pixel-format nv12` (skipped when a background video forces a transparent `-t` render, since that's hardcoded to the alpha-only `qtrle` codec and can't use a GPU encoder), and `add_background_video.py`/`burn_subtitles.py` each get a `--gpu` flag that swaps their own `-c:v libx264` for `h264_qsv`. `add_background_music.py` needs no such flag — it only re-encodes audio (`-c:v copy` on the video stream), so there's nothing to accelerate. Measured ~40% faster wall-clock on this machine's Intel Iris Xe iGPU (50.4s → 30.1s for the same render at `-qm`). If this project ever runs on hardware without Quick Sync, `detect_gpu_encoder()`'s probe simply returns `False` and everything falls back to the CPU path with no other code changes needed.
  - All inputs are bound to `st.session_state` via `key="k_..."` (see `WIDGET_DEFAULTS` in `app.py`), which is what makes three features possible: a **"🆕 New Video" button** that only clears the script text, video label, and displayed video (keeps every setting as-is, for generating another video with the same voice/theme/style/etc.); a separate **"♻️ Reset Settings" button** that resets every widget to `WIDGET_DEFAULTS` (the old "New Video" behavior — a full clean slate); and a **sidebar history list** (below) that can reload any past run's exact settings back into the live form.
  - **Gotcha**: Streamlit raises `StreamlitWidgetAlreadyInstantiatedError` if you write to `st.session_state[key]` after the widget with that `key` has already been instantiated *in the same script run* — even though a `st.rerun()` is about to happen right after. This is why the "New Video"/"Reset Settings" buttons, the history "Open" button, and the template-picker's "Load template" button (which all mutate `k_*` keys) are placed BEFORE any of the settings/script widgets they reset/restore/populate are created in the script. If you add a new resettable/restorable widget, add its key to `WIDGET_DEFAULTS` and to `_restore_session()`, and don't move those mutating blocks below the widgets they affect.
  - `sessions.py` — on-disk render history, independent of `gui_config.json`, shared by both the interview and timeline pipelines. `save_session(config, video_path, label, render_settings, kind="interview")` copies the final video into `sessions/<id>/` (copying matters: both pipelines' manim output path is always the same filename, so the next render would otherwise silently overwrite it) and appends an entry to `sessions/index.json`, tagged with `kind` ("interview" or "timeline") so the sidebar history list knows which restore function to call. `list_sessions()` (newest first), `get_video_path(entry)`, `delete_session(id)` round out the module. `config` is the exact `gui_config.json`/`timeline_config.json`-shaped dict used for that render; `render_settings` holds the app.py-only extras that never go in that config (quality/format pickers, caption burn-in choice) so they can still be restored. `sessions/` is gitignored, same as `gui_config.json`.
- `scene.py`, `text_scenes.py`, `graph_scenes.py`, `animation_scenes.py`, `complex_shapes.py`, `pythagorean_theorem.py` — unrelated Manim learning/demo scenes from earlier in the project, not part of the interview pipeline.

## Timeline / history video pipeline (`timeline_video/`, experimental)

A second, independent video type lives entirely under `timeline_video/` —
documentary/history-style videos (a date/chapter label + narrated story text
over a Ken Burns-panned image, crossfading scene to scene, with a progress
bar across the top) instead of the interview Q&A format. It reuses the
interview pipeline's TTS/theme/branding code but has its own entry point,
script format, and config file, and never edits `interview_simulation.py` or
any `style_*.py` file.

Render directly:
```
venv/Scripts/python.exe -m manim -ql timeline_video/timeline_simulation.py TimelineVideo --disable_caching
```
or via `app.py`'s **"🕰️ Timeline (Testing)"** tab (see the `app.py` bullet below).

- `timeline_video/timeline_format.py` — parser. Blank-line separated scenes,
  each an optional `LABEL:` line, an optional `IMAGE:` line (path resolved
  relative to `timeline_video/` if not absolute), then narration text
  (same inline markdown emphasis as the Q&A pipeline, rendered via
  `reveal_common.build_paragraph`).
- `timeline_video/timeline_simulation.py` — entry point
  (`TimelineVideo(VoiceoverScene)`). Inserts the project root onto `sys.path`
  at import time so it can reuse `reveal_common.py`, `themes.py`,
  `branding.py`, `edge_tts_service.py` unmodified from a subfolder. Per
  scene: builds a background (an `ImageMobject`, oversized by
  `IMAGE_OVERSCAN` and continuously panned/zoomed by a per-frame
  `add_updater` — `make_ken_burns_updater` — rather than a timed
  `scene.play()`, since the real narration duration isn't known until
  `speak_and_reveal`'s `with scene.voiceover(...)` block starts; falls back
  to the theme gradient if a scene has no image), a bottom-anchored caption
  panel (word-reveal via `speak_and_reveal`), a corner date/label card, and
  advances a marker along a persistent top progress bar.
- `timeline_video/timeline_config.json` (gitignored) /
  `timeline_video/timeline_script.txt` — same `DEFAULT_CONFIG`-with-fallback
  pattern as `gui_config.json`/`interview_script.txt`. Schema: `script_text`,
  `voice`, `narration_speed`, `theme`, `orientation`, `show_intro`,
  `channel_name`, `episode_title`, `show_outro`, `outro_message`, `handle`,
  `pexels_api_key`, `pixabay_api_key` — no `reveal_style` (only one visual
  exists so far) and no `answer_voice` (single narrator for the whole video).
  `narration_speed` behaves exactly as in `gui_config.json` (see interview
  pipeline's schema above) — needs SoX on PATH for anything other than `1.0`.
- `timeline_video/stock_fetch.py` — `fetch_stock_image(query, orientation,
  pexels_api_key, pixabay_api_key)`, used when a scene's `SEARCH:` line (see
  `timeline_format.py`'s docstring) is given instead of `IMAGE:`: tries
  Pexels then Pixabay, downloads+caches the result under
  `timeline_video/images/stock_cache/` (gitignored), returns `None` on no
  key/no match/failure — same as a scene with no image, falls back to the
  theme gradient. `app.py`'s Timeline tab has a "Stock photos (optional)"
  section with password-masked fields for both keys.
- `timeline_video/images/` — where user-supplied scene images go. This
  pipeline has no image-generation step of its own; images are generated
  externally (e.g. via Gemini's web UI) and dropped in here, referenced by
  the script's `IMAGE:` lines.
- Orientation follows the same convention as the interview pipeline
  (`reveal_common.is_portrait()`/`font_size_for()`, width-based constants
  computed inside `render_timeline()` from a live `config.frame_width`, never
  as a module-level literal) — including orientation-specific side margins
  (`CAPTION_SIDE_MARGIN_PORTRAIT`, `BAR_SIDE_MARGIN_PORTRAIT`). **Both gotchas
  below were caught by actually rendering a frame and looking at it, not by
  reading the code** — same verification discipline as the rest of this
  project:
  - The caption panel is anchored to the bottom edge via
    `to_edge(DOWN, buff=CAPTION_BOTTOM_GAP)`, not centered at a fixed Y. A
    fixed-center approach let a 3-line caption's box bottom edge run past the
    frame edge; anchoring to the edge plus a height cap
    (`CAPTION_MAX_HEIGHT`, scaling the caption down if it would be taller)
    keeps the box fully on-screen regardless of narration length.
  - Landscape-tuned side margins (`CAPTION_SIDE_MARGIN`, `BAR_SIDE_MARGIN`)
    eat proportionally far more of the much narrower portrait
    `config.frame_width`, which forced captions into many tiny wrapped lines
    and then an aggressive height-cap scale-down. Fixed the same way other
    styles handle this: separate `*_PORTRAIT` constants picked at the top of
    `render_timeline()` via `is_portrait()`.

**`app.py`'s "🕰️ Timeline (Testing)" tab**: the entire pre-existing interview
UI is wrapped unchanged in a `tab_interview`/`tab_timeline = st.tabs([...])`
pair (pure indentation, no logic changes — verified with
`streamlit.testing.v1.AppTest`, which actually executes the script headlessly
and surfaces exceptions, rather than just checking it imports) so the two
pipelines share one Streamlit process without interfering. The Timeline tab
has its own inline settings (script textarea, voice/theme/orientation,
intro/outro, background music, caption burn-in, quality) and deliberately
ignores the sidebar, which still belongs to the Interview tab. It reuses
`add_background_music.py`, `burn_subtitles.py`, `generate_thumbnail.py`, and
`sessions.py` the same way the interview tab does, through its own `k_tl_*`
session-state keys (see `TL_WIDGET_DEFAULTS`) and its own
`_restore_timeline_session()` instead of the interview tab's
`_restore_session()`. It calls `sessions.save_session(..., kind="timeline")`
so the sidebar history list can tell entries apart and dispatch "Open" to the
right restore function — an entry with no `kind` (saved before this field
existed) defaults to `"interview"`.

## Conventions

- No comments unless the WHY is genuinely non-obvious — this codebase mostly avoids them, keep it that way.
- Don't add config options, fallbacks, or abstractions beyond what's actually used.
- When several independent pieces of work don't touch the same file, prefer parallel
  agents (max 4 concurrent) over doing them serially — see git history / past
  sessions for the pattern: one file per agent, a shared read-only contract
  (like `reveal_common.py`), integration done by a single owner afterward.
- Never commit or push without being explicitly asked.
