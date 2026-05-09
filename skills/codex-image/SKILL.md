---
name: codex-image
description: Use when generating or editing raster images and the built-in image_gen tool is not exposed in the current Codex session, when Codex is running in API key mode, or when the user explicitly asks for codex-image, saved PNG/JPEG/WebP output, Images API, custom OPENAI_BASE_URL, exact output path, exact size, aspect ratio, or local image CLI workflow.
---

# Codex Image Skill

Local saved-file raster image workflow backed by `scripts/codex_image.py`, shell launchers, and thin OpenAI-compatible image HTTP calls.

## Core rules

- Use built-in/system `imagegen` first when the current session actually exposes `image_gen` and the user wants the normal native image workflow: current-turn image context, fastest simple generation/editing, or natural multi-turn follow-up without explicit local file/output-path control.
- Use this skill as the fallback when built-in `image_gen` is absent, hidden, unavailable, already ruled out by the user, or failed before producing an image.
- This skill is CLI-only. Do not describe it as built-in image support.
- Use the installed launcher path directly, not a repo-relative path: on POSIX `bash "${CODEX_HOME:-$HOME/.codex}/skills/codex-image/scripts/codex-image"`; on Windows use `%CODEX_HOME%\skills\codex-image\scripts\codex-image.cmd` or `%USERPROFILE%\.codex\skills\codex-image\scripts\codex-image.cmd`.
- Once this skill is selected, usually run the installed launcher first. Preflight config, auth, or `--help` only when the launcher is missing or its failure still leaves a real decision to make.
- When a launcher call fails with a deterministic local parse or input-shape error and the safe retry is obvious, retry once immediately in the same turn before sending commentary.
- Do not fall back to SVG, Pillow sketches, screenshots, or one-off scripts unless the user explicitly wants code-native graphics.
- `OPENAI_BASE_URL` or provider `base_url` must exist in API-key mode.
- Never silently downgrade the model or transport. Switching from `gpt-image-2` to `gpt-image-1.5`, from Images API to Responses, or disabling `input_fidelity` requires explicit user confirmation unless the user already named the target model/transport in the current request.
- Always close out a task by reporting three things: the final saved path(s), the final prompt or prompt set, and the mode used (`generate` / `edit` / `generate-batch` plus the transport).
- Pass non-ASCII / multi-line / quoted prompts directly via `--prompt "..."`. Windows argv is Unicode-safe (CreateProcessW / GetCommandLineW), so preemptively writing the prompt to a temp file is unnecessary. Use `--prompt-file` only after a real argv encoding failure has actually occurred.
- Do not silently set `--input-fidelity` for `gpt-image-2`; it is a no-op there. Only pass `--input-fidelity` when the active model is `gpt-image-1.5` or another model that documents the field, and only with explicit user agreement (because routing to `gpt-image-1.5` is a model downgrade per the rule above).

## When to use

- Generate a new raster image and save it to disk
- Edit one or more real input images through `/v1/images/edits`
- Use exact output paths, exact sizes, aspect ratios, PNG/JPEG/WebP, or custom provider endpoints
- Use this path in API-key mode, with custom `OPENAI_BASE_URL`, or for direct Images API workflows even if built-in `image_gen` is exposed
- Use explicit Responses API image-generation state only when the caller really needs it
- Batch-generate many prompts through `generate-batch`

## When not to use

- The built-in/system `imagegen` path is available and the user wants the normal built-in experience
- The user wants native current-turn image context or the fastest simple multi-turn image follow-up and does not need explicit local file/output-path control
- The task is better solved as SVG, HTML/CSS, canvas, or another code-native asset
- The task is extending an existing repo-native icon or illustration system

## Intent rules

- If the model must see any real image input, treat the task as `edit`.
- If the user only describes references in text and provides no image files, treat the task as `generate`.
- Prefer `--prompt` over a long trailing positional prompt when shell quoting would be awkward.
- For simple one-shot `generate`, keep the prompt close to the user's wording. Only expand it into a longer art brief when the user explicitly asks for richer art direction or stricter visual constraints.
- `generate` and `edit` default to the Images API. Use `--transport responses` only for explicit multi-turn image-generation state such as `--previous-response-id` or `--response-image-id`.
- In `responses` mode, `edit` may omit local image inputs when the follow-up should continue from prior response state alone.
- Attachment placeholders and image-set selectors only work inside a Codex thread with `CODEX_THREAD_ID` or `CODEX_SESSION_ID`.
- These placeholders are an explicit local thread workflow, not the same thing as built-in `imagegen`'s native current-turn runtime image context.
- In that Codex-thread mode, `[Image #N]` resolves against the most recent attachment-bearing user turn. It is the current turn only when the current turn actually carries attachments; otherwise treat it as a historical reference, not native current-turn image context.
- Previous attachment-bearing turns can be referenced as `[Turn -K Image #N]`.
- Stable thread-wide attachment numbering can be referenced as `[Thread Image #N]`.
- The previous saved result for the thread can be referenced as `[Last Output]` or `[Last Output #N]`.
- After a follow-up that adds only one new attachment, that new file is `[Image #1]`. Older images do not remain addressable as `[Image #2]` or `[Image #3]`; switch to `[Turn -1 Image #N]`, `[Thread Image #N]`, or explicit `--image-set`.
- In that Codex-thread mode, the active image set is the previous `edit` call's resolved input image list for the thread, not prior generated outputs.
- Use `--image-set last-output` when the user wants to continue refining the previously generated result image itself.
- Attachment placeholders resolve only from rollout-recorded paths for that turn; they do not fall back to the current shell working directory.
- Use `--image-set` to select `active`, `last-output`, `latest-turn`, `turn:-K`, or `thread:1,2,5` explicitly.
- `edit` does not implicitly inherit prior thread state. Reuse requires explicit `--image-set active` or explicit image references.
- Harmless placeholder variants such as `[Image#1]` and `[image # 1]` are normalized automatically.
- If `generate` is called with `--image`, the CLI emits a warning and reroutes it to `edit`.
- For `edit`, list invariants explicitly in the prompt (`change only X; keep Y unchanged`) and repeat them on every iteration. Do not rely on implicit memory across calls.
- For multi-image inputs, label every image's role in the prompt: `reference image`, `edit target`, or `supporting insert/style/compositing input`. Placeholders such as `[Image #N]` resolve *which* file; the role label resolves *what to do with it*.
- Iterate one change at a time. After each call, re-validate the result, then ship the next single change in a new call. Bundling multiple unrelated changes in one prompt makes drift hard to localize.

## Output rules

- Default output base is `${CODEX_HOME:-~/.codex}/generated_images/`.
- Inside Codex, the default subdirectory uses `CODEX_THREAD_ID` or `CODEX_SESSION_ID`.
- Outside Codex, the default subdirectory is `manual/`.
- Use `--out` for an exact final path.
- Use `--out-dir` for batch or multi-output jobs.
- Use `--name` for a readable prefix with an automatic random suffix.
- Successful `responses` calls record the latest response ids under the thread output directory for follow-up reuse.

### Save-path precedence

Apply top-down, taking the first match:

1. The user named a destination (file path, directory, or workspace location). Move or copy the selected output there.
2. The asset is meant to be consumed by the current project (the request mentions a repo file, component, or page). Move or copy the final image into the workspace before finishing. Never leave a project-referenced asset only at the default `${CODEX_HOME}/generated_images/...` path.
3. The asset is preview-only or for brainstorming. Render inline; the underlying file may stay at the default path.

### Naming and overwrite

- Default to non-destructive saves. Do not overwrite an existing file unless the user explicitly asked to replace or overwrite it.
- When a target name is taken, write a sibling versioned name such as `hero.png` -> `hero-v2.png`, `item-icon.png` -> `item-icon-edited.png`.

## Transparent image requests

codex-image is CLI-only and has no built-in `image_gen` to fall back on, so transparent backgrounds are produced in this order:

1. **Default: chroma-key + local matte removal.**
   - Generate the subject on a perfectly flat solid chroma-key background. Default key color is `#00ff00`; use `#ff00ff` for green-dominant subjects, and avoid `#0000ff` for blue subjects.
   - Run the bundled `scripts/remove_chroma_key.py` helper on the saved file to convert the key color to alpha. Recommended flags: `--auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill`.
   - Validate the result has an alpha channel, transparent corners, and no key-color fringe.
2. **Fallback: model-native transparent output.** Only use this after explicit user confirmation, because it requires switching to a model that supports `background=transparent` (for example `gpt-image-1.5`) — this is a model downgrade.

Trigger the confirmation prompt when chroma-key removal is unlikely to produce a clean cutout: hair, fur, feathers, smoke, glass, liquids, translucent or reflective materials, soft cast shadows, or subjects whose colors conflict with every practical key color.

Confirmation message template:

```text
This request likely needs native transparency. The default codex-image path uses a chroma-key background plus local matte removal; native transparency requires switching to a model that supports background=transparent (for example gpt-image-1.5), which is a model downgrade. Should I proceed?
```

Transparent prompt template:

```text
Create the requested subject on a perfectly flat solid #00ff00 chroma-key background for background removal.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

## Decision tree

Treat each request as two independent questions:

1. **Intent: generate or edit?**
   - User provides image inputs only as references for style, composition, mood, or subject guidance: `generate`.
   - User wants to keep parts of an existing image and modify the rest: `edit`.
   - No image inputs at all: `generate`.
2. **Execution strategy: single asset, multi asset, or multi variant?**
   - Multiple distinct assets: issue one `generate` / `edit` call per asset, or one `generate-batch` job. Do not use `n` to substitute for distinct prompts.
   - Multiple variants of the *same* prompt: use `n`.
   - The bare word "batch" does not by itself mean `generate-batch`. Reserve that subcommand for explicit batch workflows (JSONL inputs, multi-prompt files, or the user explicitly asking for batch CLI control).

Default to `generate` unless the request clearly asks to change an existing image.

## Workflow

1. Decide `generate`, `edit`, or `generate-batch`.
1a. **Edit auto-size (default path)**: for `edit` just call `codex-image edit --image INPUT.png --prompt "..."` **without** `--size`. The CLI reads the input dimensions itself (PNG/JPEG/GIF/WebP/BMP via stdlib header parsing, no Pillow needed), picks the smallest valid 16-aligned `--size` with the same aspect ratio, and post-resizes the result back to the input dims (Pillow → sips → PowerShell System.Drawing fallbacks on each platform). **Do not pre-read dimensions in the agent**; that just adds steps. Use `codex-image inspect FILE` only when the user explicitly wants to see the chosen sizes before the call. Never let `--size` default to `1536x1024` for an `edit` against an arbitrary input.
2. Collect prompt, exact text, constraints, output target, and any input images.
3. If the user mainly wants the normal native image conversation path and does not need saved-file, exact output path, explicit placeholder references, or API/CLI control, do not use this skill; let built-in `imagegen` handle it.
4. Keep the default transport on the Images API. Reach for `--transport responses` only when explicit prior-response image state is part of the task.
5. In a Codex thread with `CODEX_THREAD_ID` or `CODEX_SESSION_ID`, use `[Image #N]` for the most recent attachment-bearing turn, `[Turn -K Image #N]` for earlier attachment-bearing turns, `[Thread Image #N]` for stable thread-wide references, `[Last Output]` for the previous saved result image, or `--image-set active` / `--image-set last-output` / `--image-set latest-turn` for explicit reuse.
   A follow-up that adds one new image should usually look like `[Turn -1 Image #1]`, `[Turn -1 Image #2]`, and `[Image #1]` rather than `[Image #1]`, `[Image #2]`, `[Image #3]`.
   A follow-up that says "use the last result as the base and refine it" should usually include `[Last Output]` or `--image-set last-output`, then describe that image as the base result to refine in the prompt.
6. Normalize the size request:
   - keep explicit `WIDTHxHEIGHT` unchanged
   - convert ratio forms such as `16:9` or `9:16@1k` into direct API sizes
   - preserve the requested final delivery size as the post-save target
7. Run the bundled launcher.
8. Validate four things on every output: subject, style/composition, text accuracy (when text is present), and invariants/avoid items (especially for edits).
9. Report the close-out triple: final saved path(s), final prompt or prompt set, and the mode used (`generate` / `edit` / `generate-batch` plus the transport).

## Size and post-processing policy

- Pass explicit non-standard sizes such as `1024x1792` to the API unchanged, but only if they satisfy the model's hard constraints. The CLI rejects invalid `WIDTHxHEIGHT` locally with the same rule descriptions the API would return.
- If the returned image has the same aspect ratio but different pixels, resize locally to the requested final size.
- If the returned aspect ratio differs materially, stop instead of stretching automatically.

### gpt-image-2 size constraints (hard-rejected locally before the API call)

- Maximum edge length must be `<= 3840px`.
- Both edges must be multiples of `16px`.
- Long edge to short edge ratio must not exceed `3:1`.
- Total pixels must be at least `655,360` and no more than `8,294,400`.

Recommended sizes (pick from these whenever possible to avoid rejection):

- `1024x1024` — fast square draft
- `1536x1024` / `1024x1536` — landscape / portrait
- `2048x2048` — 2K square
- `2048x1152` — 2K landscape
- `3840x2160` / `2160x3840` — 4K landscape / portrait
- `auto`

## Prompt guidance

- Structure prompts as backdrop -> subject -> details -> constraints.
- Quote exact text when text matters.
- Repeat invariants for edits.
- Add only useful detail; do not invent extra objects, brands, or layout constraints.

For prompt schema, taxonomy, examples, and CLI detail, use:

- `references/prompting.md`
- `references/sample-prompts.md`
- `references/cli.md`
- `references/image-api.md`
- `references/codex-network.md`
