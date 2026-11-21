# YouTube Creator Skills

OfflineYouTubeStudio includes eleven creator workflows inspired by the public
[youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill)
project. The source project is MIT-licensed; its license and attribution are
included in creator_skills/SOURCE_LICENSE_MIT.txt. The Python integration in
this repository is independently implemented.

## Included workflows

| Skill | What it does | Input |
|---|---|---|
| yt-audit | Finds the single biggest channel improvement from evidence, while noting what already works and what not to change yet. | Recent titles, thumbnail notes, opening transcripts, upload dates and real analytics |
| yt-chapters | Creates chapter timestamps and validates YouTube's 00:00 start, three-chapter minimum and 10-second minimum per chapter. | SRT, VTT or Whisper JSON |
| yt-comment | Sorts comments into questions, corrections, praise and bait; drafts short replies and suggests one pinned comment. | Comments and optional creator voice/context |
| yt-edit | Produces an edit decision list for dead air, filler-only cues and likely repeated starts. | SRT, VTT or Whisper JSON |
| yt-package | Generates ten title/thumbnail pairings, ranks three and checks for overlap, vague wording and length. | Topic, audience, promise and evidence |
| yt-plan | Plans a realistic week or month using actual available hours and work already in progress. | Capacity, unfinished work, audience and formats |
| yt-retention | Reports opening loss, steep drops and average mid-video decline from a retention export. | YouTube Studio CSV; duration if the position axis is percent |
| yt-script | Creates five hook approaches, editorial hook scores and a beat-by-beat script with on-screen directions. | Idea, viewer, duration, evidence and voice |
| yt-seo | Creates a search-aligned description, focused tags and target query checks. | Topic, viewer, title, target keywords and links |
| yt-shorts | Finds self-contained 20–55 second excerpts and proposes fresh hooks and vertical framing. | Timestamped transcript |
| yt-viral | Ranks candidate videos by views divided by their own channel's median views. | JSON video records; four or more videos per channel |

## Run them in the browser

1. Start the local Studio with ONE_CLICK.bat start.
2. Open http://127.0.0.1:8765.
3. Scroll to YouTube Creator Skills.
4. Choose a skill, paste the evidence in its requested format and click Run selected skill locally.
5. Review the result and edit it before using it.

API endpoints:
- GET /api/creator/skills — list available workflows and model guidance.
- POST /api/creator/run — run one workflow. JSON body: {"skill":"yt-script","input":"your creator brief"}.

## AI model and offline behavior

Language tasks call the local Ollama HTTP endpoint at OLLAMA_URL; there is no
hosted LLM fallback and no paid API key. Deterministic transcript and analytics
workflows run in Python and do not need an LLM. The default model is qwen3:4b.

Install Ollama separately, then download the model once:

~~~bash
ollama pull qwen3:4b
~~~

The project cannot silently install Ollama itself. To use another installed
model, set OLLAMA_MODEL before starting Studio. For example, in Windows
Command Prompt:

~~~bat
set OLLAMA_MODEL=qwen3:4b
ONE_CLICK.bat start
~~~

Qwen3 4B is the recommended starting point for this class of hardware, not a
guarantee that all layers will fit in 4 GB of VRAM. Ollama may use system RAM
for CPU offload. On a 4 GB GPU, close other GPU-heavy applications, start with
short inputs, and use a smaller local model if generation is too slow or runs
out of memory. The official Ollama library lists the Qwen3 4B artifact at
about 2.5 GB: https://ollama.com/library/qwen3.

Once Ollama and the model are installed, prompts are processed locally. The
first Ollama model download requires internet access; the skills do not call
Gemini, OpenAI, ElevenLabs or other cloud inference services.

## Evidence and safety boundaries

- These workflows do not guarantee a viral result, view count, CTR, ranking or audience-retention improvement.
- yt-audit does not scrape a channel URL or access private YouTube Studio data. Paste evidence or exports yourself.
- yt-retention analyzes the CSV values you provide. It does not connect to your YouTube account.
- yt-viral ranks a manually supplied dataset. It does not scrape competitors or infer why a video succeeded.
- yt-edit produces suggested cuts only. It does not modify source media.
- yt-comment drafts replies only. It never posts, hearts or pins comments.
- yt-chapters, yt-retention, yt-edit and yt-viral use deterministic checks. yt-audit, yt-comment, yt-package, yt-plan, yt-script, yt-seo and yt-shorts use the selected local Ollama model.
- The model can still make mistakes. Check all factual claims, citations, timestamps, title promises and channel-specific recommendations before publishing.

## Tests

Run:

~~~bat
TEST.bat
~~~

The creator skill tests cover transcript parsing, chapter validation, edit cues,
retention summaries, relative-view outlier calculations and skill dispatch.
