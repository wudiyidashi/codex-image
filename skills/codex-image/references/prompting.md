# Prompting best practices

These prompting principles are shared across the generate and edit flows in this skill.

This file is about prompt structure and iteration. API controls such as `quality`, `background`, `output_format`, `output_compression`, `mask`, and `input_fidelity` are execution settings, not prompt content.

## Structure

- Use a consistent order: scene/backdrop -> subject -> key details -> constraints -> output intent.
- For complex requests, use short labeled lines instead of one long paragraph.
- Include intended use when it affects polish or composition, such as wallpaper, poster, hero image, sticker, infographic, or UI mockup.

## Use-case taxonomy

Classify each request into exactly one slug and keep that slug consistent across the prompt scaffolding (`Use case:`) and any iteration follow-ups.

**Generate**

- `photorealistic-natural` — candid/editorial lifestyle scenes with real texture and natural lighting
- `product-mockup` — product/packaging shots, catalog imagery, merch concepts
- `ui-mockup` — app/web interface mockups and wireframes; specify the desired fidelity
- `infographic-diagram` — diagrams/infographics with structured layout and text
- `scientific-educational` — classroom explainers, scientific diagrams, learning visuals with required labels and accuracy constraints
- `ads-marketing` — campaign concepts and ad creatives with audience, brand position, scene, and exact tagline/copy
- `productivity-visual` — slide, chart, workflow, and data-heavy business visuals
- `logo-brand` — logo/mark exploration; vector-friendly
- `illustration-story` — comics, children's book art, narrative scenes
- `stylized-concept` — style-driven concept art, 3D / stylized renders
- `historical-scene` — period-accurate / world-knowledge scenes

**Edit**

- `text-localization` — translate / replace in-image text, preserve layout
- `identity-preserve` — try-on, person-in-scene; lock face / body / pose
- `precise-object-edit` — remove / replace a specific element (including interior swaps)
- `lighting-weather` — time-of-day / season / atmosphere changes only
- `background-extraction` — transparent background / clean cutout (use the chroma-key + `remove_chroma_key.py` workflow)
- `style-transfer` — apply reference style while changing subject / scene
- `compositing` — multi-image insert / merge with matched lighting and perspective
- `sketch-to-render` — drawing / line art to photoreal render

## Multi-image inputs

- Reference each image by index in the prompt: `Image 1: edit target; Image 2: style reference; Image 3: compositing insert`.
- Explicitly label every input's role. Use one of: `reference image`, `edit target`, `supporting insert/style/compositing input`. Placeholder syntax such as `[Image #N]` resolves *which* file; the role label resolves *what to do with it*.
- For edits, list the invariants for the `edit target` separately from any guidance about the references.

## Specificity policy

- If the user prompt is already detailed, normalize it into a cleaner spec.
- If the prompt is generic, add only the detail that materially improves the result.
- Treat the examples in `sample-prompts.md` as complete recipes, not the default amount of augmentation to add every time.

## Allowed augmentation

- composition and framing cues
- intended-use or polish-level hints
- practical layout guidance
- reasonable scene concreteness that supports the stated request

Do not add:

- extra characters, props, or objects not implied by the request
- brand palettes, slogans, or story beats not implied by the request
- arbitrary left/right placement without surrounding layout context

## Constraints and invariants

- State what must not change.
- For edits, say `change only X; keep Y unchanged`.
- Repeat invariants on every iteration to reduce drift.

## Text in images

- Put literal text in quotes and require verbatim rendering when text matters.
- Specify typography and placement when needed.
- For image-only requests, explicitly say `no text`.

## Direct-size guidance

- Prefer direct final sizes whenever the user provides an exact delivery size.
- When the user provides only a ratio like `16:9`, `9:16`, or `6:16`, let the skill convert it to the largest valid direct-request size.
- When the user provides both a ratio and a tier such as `9:16 1k`, `16:9 2k`, or `4k 9:16`, use the CLI ratio-tier syntax such as `--size '9:16@1k'` rather than passing the plain ratio.
- Keep the prompt explicit about the final canvas dimensions. The CLI adds this automatically for resolved direct sizes; do not contradict it with text such as "4K" when requesting `1k`.
- For explicit non-standard sizes, pass the user-requested `WIDTHxHEIGHT` to the API and describe that same final size in the prompt.
- If the generated result comes back with a materially different aspect ratio, do not silently distort it. Ask whether to retry through the model with stricter canvas wording or apply a chosen post-processing strategy.
- Do not plan on cropping, padding, or local upscaling after generation.

## Input images

- If actual image files are provided for the model to see, use `edit`, not `generate`, even when creating a new poster or mockup.
- Do not assume every provided image is a base image to modify; some inputs may be role references, product references, style references, or masks.
- For multi-image edits, label each input role clearly, for example `Input image 1 role: person reference` and `Input image 2 role: product reference`.
- Restate what must stay fixed from each input image.
- In Codex-thread attachment flows, `[Image #N]` only addresses the most recent attachment-bearing user turn. After a follow-up that adds one new image, use `[Image #1]` for that new image and switch older images to `[Turn -1 Image #N]`, `[Thread Image #N]`, or explicit `--image-set`.
- Prefer direct invocation of `python3 "$CODEX_IMAGE"` or the full bundled script path. Do not rely on a `codex-image` shell alias being present.

## Iteration

- Start with a clean base prompt.
- Change one thing at a time on follow-up iterations.
- Re-state the must-keep constraints every time.
- In follow-up turns that add new attachment images, restate the role of every carried-forward image explicitly so the command shape stays stable.

## Suggested shared schema

```text
Use case: <taxonomy slug>
Asset type: <where the image will be used>
Primary request: <main request>
Input images: <Image 1: role> (optional)
Scene/backdrop: <setting>
Subject: <main subject>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <wide/close/top-down; placement>
Lighting/mood: <lighting + mood>
Color palette: <palette notes>
Materials/textures: <surface details>
Text (verbatim): "<exact text>"
Constraints: <must keep/must avoid>
Avoid: <negative constraints>
```
