# AGENTS.md

This project generates "interview practice" YouTube videos with Manim: a question
and answer appear on screen, narrated by TTS, text revealing word-by-word in sync
with the narration. This file is the map for any agent picking the project back up.

## Environment (Windows)

- Python venv at `./venv` — always call `venv/Scripts/python.exe`, never a bare `python`.
- ffmpeg is installed via winget but is NOT on PATH in a fresh shell. Before running
  any `manim` or `ffmpeg` command, prepend its bin dir for that shell session:
  ```
  export PATH="/c/Users/NIS/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin:$PATH"
  ```
- MiKTeX (LaTeX) is installed, so `MathTex`/`Tex` work.
- `manim-voiceover`, `gtts`, and `edge-tts` are installed in the venv.

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
   text legibility over a photo.
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
- `build_paragraph(text, font_size, max_width, color)` → word-wrapped `VGroup` +
  ordered list of word mobjects.
- `speak_and_reveal(scene, text, words)` → runs the `with scene.voiceover(...) as
  tracker:` block, reveals `words` via a word-by-word `LaggedStart(FadeIn(...))`
  timed to `tracker.duration` exactly (natural per-word jitter already applied),
  and waits out any leftover audio. **This is the only way text should be
  revealed** — it's what keeps visuals in sync with real spoken narration.
- `THINKING_PAUSE` — recommended pause between a question finishing and the
  answer starting.

`build_paragraph` also parses inline markdown-style emphasis in the source
text — `**bold**`/`__bold__`, `*italic*`, `==highlight==` (rendered in
`DEFAULT_HIGHLIGHT_COLOR`, overridable via the `highlight_color` kwarg) —
and strips the markers from the displayed words. Any style that calls
`build_paragraph` gets this for free. `style_terminal.py` and
`style_whiteboard.py` use their own local word-builder helpers (for
Consolas/handwriting fonts) and do NOT currently support it — extend those
the same way (mirror `_parse_markdown_words` from reveal_common.py) if
needed.

Current styles: `style_stacked.py` (default — Q shrinks to a top banner, A below),
`style_terminal.py` (green-on-black, Q/A as command/output, accumulates and
auto-scrolls). Shortlisted but not yet implemented as of this writing: chat
bubbles, split screen, sticky notes, whiteboard — check `STYLE_REGISTRY` in
`interview_simulation.py` for what's actually wired in before assuming a style
exists.

When adding a new style, give it its own `style_<name>.py` file (never edit
another style's file or `reveal_common.py`'s contract) so styles can be built in
parallel without merge conflicts, then add one line to `STYLE_REGISTRY`.

### `gui_config.json` (project root, gitignored)

Written by `app.py` (or by hand for testing); read fresh on every render.
```json
{
  "script_text": null,            // string in "Q: ...\nA: ...\n\n" format; null = read interview_script.txt
  "voice": "en-US-AndrewNeural",  // edge-tts voice name
  "theme": "midnight",            // key into themes.THEMES
  "background_image": null,       // optional absolute path to an image file
  "reveal_style": "stacked",      // key into STYLE_REGISTRY
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
- `burn_subtitles.py` — hardcodes the auto-generated `.srt` onto an exported mp4 (`default`/`bold` caption styles). Standalone CLI, not wired into the main render.
- `batch_render.py` — renders every `.txt` script in a folder in one go, into `batch_output/`.
- `generate_metadata.py` — generates a suggested YouTube title/description/duration estimate from a script, pure local heuristics, no API calls.
- `app.py` — Streamlit GUI wrapping the manim CLI render (voice/theme/quality/format pickers, background image upload, intro/outro toggles, live render log, video preview+download). Run with `venv/Scripts/python.exe -m streamlit run app.py`.
- `scene.py`, `text_scenes.py`, `graph_scenes.py`, `animation_scenes.py`, `complex_shapes.py`, `pythagorean_theorem.py` — unrelated Manim learning/demo scenes from earlier in the project, not part of the interview pipeline.

## Conventions

- No comments unless the WHY is genuinely non-obvious — this codebase mostly avoids them, keep it that way.
- Don't add config options, fallbacks, or abstractions beyond what's actually used.
- When several independent pieces of work don't touch the same file, prefer parallel
  agents (max 4 concurrent) over doing them serially — see git history / past
  sessions for the pattern: one file per agent, a shared read-only contract
  (like `reveal_common.py`), integration done by a single owner afterward.
- Never commit or push without being explicitly asked.
