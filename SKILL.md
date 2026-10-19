---
name: "bloodborne-character-sliders"
description: "Recreate a Bloodborne character (from slider screenshots, an Imgur album or r/bloodbornesliders post, a slider list, or one of 37 built-in NPC faces) by writing it straight into an in-game Favourite slot in an unencrypted (shadPS4/bbport/decrypted) save."
---

# Bloodborne sliders → Favourite slot

Use this when someone gives Bloodborne appearance values (screenshots, an r/bloodbornesliders post, a typed list), or asks for an NPC's face, and wants that character in game.

The main method writes the values straight into one of the 8 **Favourite** slots in the system save `userdata0010`, using `scripts/bb_favourite.py`. It takes seconds and was checked in game in Oct 2026:
- It reproduces a game-written favourite byte for byte.
- The Iosefka preset matches the game's own face file byte for byte.
- Gender, age and clouded eyes load correctly.

Driving the in-game editor is a slow fallback, covered at the end.

## Files
Everything sits in this skill's folder, which is also the repository https://github.com/rona953/bloodborne-favourites. Paths below are relative to that folder, so run the commands from it (or with its full path).
- `scripts/bb_favourite.py`, the writer: Python 3, no dependencies. Run `python3 scripts/bb_favourite.py -h` for the field notes.
- `example_preset.json`, a complete player preset.
- `presets/`, 37 NPC presets plus FromSoftware's default face, built from Herne's "Bloodborne NPC Face Data Compilation" (linked from bloodborne-wiki.com/p/sliders.html). `presets/INDEX.md` lists them.
- `scripts/herne_to_presets.py`, which rebuilds `presets/` from that spreadsheet.
- `presets_user/`, characters transcribed from posts (for example `grumpy_grandpa.json`).
- If the files are missing, clone that repository or ask the user for it. Don't rebuild the script from memory, because its template bytes have to be exact.

## Requirements
- **An unencrypted save:** shadPS4, bbport, or a PS4 save that has already been decrypted (Noxde's editor wiki has a PS4 decryption guide). An encrypted PS4 save won't work.
- **The save folder:** `…/savedata/<user>/<GAMEID>/SPRJ0005/`, where GAMEID is CUSA00207, CUSA00900, CUSA03173 or CUSA01363.
  - On bbport it is `<install>\user\savedata\1\CUSA00207\SPRJ0005`.
  - `userdata0010` is the system file and holds the favourites.
- **The game closed:** it keeps favourites in memory and writes `userdata0010` when it quits, which wipes any edit made while it was running.
  - Ask the user to close it first. On bbport you can also check that `<install>\user\last_run.log` hasn't changed for a few minutes and ends with "Quit to Desktop".
  - After writing, wait a few seconds and check that the file's modified time is still yours.
  - Favourites made in game only reach the disk when the game saves, for example when the contract is finished. A script-written favourite is on disk straight away.

## Workflow
1. **Get values.**
   - For an NPC, use `presets/<name>.json`.
   - For an Imgur link, read the photos through the browser pane (see "Reading an Imgur album" below).
   - A Reddit link can't be opened: web fetch refuses reddit.com and the browser pane blocks it for safety. Don't route around this with another browser. Ask the user to paste the post's image link (usually Imgur) or attach the screenshots.
   - Otherwise, transcribe page by page using the menu labels. Ask the user to confirm blurry numbers.
   - Choices picked from a colour palette (often pupil, tattoo or glasses colour) show no RGB numbers. Estimate them and say so. Swatches render darker than the real colour, so a pixel sample is only a rough guide.
2. **Write a preset JSON** in the format of `example_preset.json`.
   - Keys are the in-game labels; case and punctuation don't matter. Sliders run 0–255.
   - Unknown keys make the script stop, which catches typos.
   - Save it in `presets_user/<name>.json` so it can be shared.
3. **With the game closed**, run `python3 scripts/bb_favourite.py list SAVE`, then `python3 scripts/bb_favourite.py write SAVE preset.json [--slot N] [--force]`.
   - Without `--slot` it uses the first free slot.
   - It backs up to `userdata0010.bak-*` next to the save, writes, and reads back to check.
   - Fields the preset leaves out come from FromSoftware's default face (`BASE_PRESET` in the script), and the script lists them. `--base template` instead keeps the raw template, which is the author's own character, so use it only to reproduce a full dump exactly.
   - On a linked PC, run it with the device shell on the mounted folder.
4. **Tell the user** to open New Game → Appearance → Load Favourite and pick that slot. Gender and age come with the favourite; the voice doesn't.
   - Tell them which voice to pick under Appearance → Voice. The script prints a suggestion: the preset's `voice` key if set, otherwise a guess from age (young → Youthful, mature → Mature, aged → Aged, nudged by a very high or low Apparent Age).
   - Pass on the script's list of fields that used the default face, and any colours you estimated.
5. **Other commands:**
   - `dump SAVE --slot N` exports a favourite as preset JSON, which is good for sharing.
   - `delete SAVE --slot N` frees a slot.
   - Old `.bak` files pile up next to the save; offer to tidy them.

## Reading an Imgur album
Imgur can't be reached from the shells (the network allowlist returns 403) or from web fetch (site blocked). The built-in browser pane on the user's PC can open it.
- Imgur is a high-risk site there: `request_access` grants only one load or action at a time, even with scope "site". Call it before each browser call on imgur.com, and tell the user to expect one approval prompt per step.
- Opening `i.imgur.com/<id>.jpeg` directly redirects to the Imgur home page, so view the photos from inside the gallery page:
  1. Open the album URL with `preview_start`, or `navigate` an existing tab.
  2. In one `javascript_tool` call:
     - Read the list from `window.postDataJSON`, a JSON string with `title` and `media[]` (`id`, `url`, `width`, `height`, `metadata.description`). This is the full list; the `<img>` tags are lazy-loaded.
     - Replace the page with `document.open(); document.write('<body style="margin:0;background:#000">'); document.close();`, store the list in `window.media`, and define `window.grid(start, n=6, cx=0, cy=120, cw=1200, ch=880, cols=2)`.
     - `grid` lays out `n` photos, two per row. Each is cropped to the region (`cx`, `cy`, `cw`, `ch`) in source pixels and scaled to fit the viewport. Do the crop with an `overflow:hidden` box and an absolutely positioned `<img>` whose width is the photo's native width × scale (from `media[i].width`). Label each photo with its number, and await every `onload` before returning.
  3. Take a `computer` screenshot. Then call `grid(6)`, screenshot, and so on: two approvals per six photos.
- The default crop fits clean 1920×1080 captures. It keeps the menu labels and the slider panel and drops the character preview. Album `QPKCr` (32 captures) took 12 prompts, and every number was readable at a scale of about 0.33.
- Photos of a TV (album `ptTAG`: 3264×2448 phone photos) are framed unpredictably. Show them uncropped, one or two per view, with `grid(i, 2, 0, 0, w, h, 1)`.
- Picker grids show the selection as a brighter frame. Read the row and column from it, and remember the beard grid scrolls.
- Photos of a TV are often blurry or at an angle. Ask the user to confirm doubtful digits rather than guessing.

## Preset keys
- **Sliders:**
  - Features, every Face Shape page ("Vert./Horiz. Facial Spacing" or the full "Vertical/Horizontal" form both work), and Scale Adjustment (Head, Chest, Abdomen, Arms, Legs).
  - Skin Colour: Skin Tone, Skin Colour Layer 1–3, Nose Bridge Colour, Cheek Colour, Laugh Lines.
  - Eye Area (6), Lipstick 1/2, and Nostrils → Nasal Size.
  - Tweak Tattoo/Mark: Position (Horizontal), Position (Vertical), Angle, Expansion.
  - Nose Slant reads "Up–Down" in the UK English text but "Down–Up" in some screenshots. Use the number as shown.
- **`gender`** (female/male) and **`age`** (young/mature/aged).
- **`voice`** (youthful/mature/aged): a reminder only, printed after writing, because favourites can't store it. Every NPC preset has one (from Herne's sheet for Henryk, guessed from age for the rest).
- **Grid choices:** `Hair`, `Brow`, `Beard`, `Eyelashes`, `Glasses`, `Tattoo/Mark`.
  - Each takes a 0-based position read left to right then top to bottom, a 1-based `"row,col"`, or text like "5th down, 3rd across".
  - For Hair the script converts the position to the game's id (position if 10 or less, otherwise position + 90). `Hair ID` sets the raw id.
- **Pupils:** `Pupil Size` (both eyes) or `Left`/`Right Pupil Size` take medium/small/large/clouded or 0–5, where 3–5 are the clouded versions the player can't pick. `Pupil Colour` sets both pupils; `Left`/`Right Pupil Colour` set one each.
- **Colours** ([R,G,B]): Hair, Brow, Beard, Eyelash, Colour of Glasses, Tattoo/Mark. `Base Skin Colour` takes RGB or a 1-based palette position `"row,col"` (5 across × 8 down). Row 1 and (2,1) of the palette are exact; the rest are close approximations.
- **Not covered:** Voice (see above), Build presets, and the hidden "face deformation" bytes. The script exposes those bytes as `Hidden Deformation 1–4`; they're unverified, so leave them at 128.

## Format notes (for maintainers)
- `userdata0010` at 0x88 holds u32 0x1000, u32 0xFACE, u32 0x800. Eight slots of 0x100 bytes follow, starting at 0x94.
- Each slot starts with `[01, gender (1 female / 0 male), 00, 00]`, then 12 zero bytes, then a FACE block (`FACE`, version 3, 0xF0 bytes).
- FACE offsets:
  - u32 values: +0x0C age (0/1/2), +0x10 hair, +0x14 left pupil, +0x18 right pupil, +0x1C brow, +0x20 beard, +0x24 glasses, +0x28 tattoo, +0x2C eyelashes.
  - +0x30 nine RGBA colours: base skin, hair, left pupil, right pupil, brow, beard, glasses, tattoo, eyelash.
  - +0x54 tattoo tweak (horizontal, vertical, angle, expansion; the default is 180, 100, 0, 40).
  - +0x58 five scale bytes.
  - +0x70 64 face-shape bytes; the order is in `SHAPE_FIELDS`. Bytes 3, 25, 30 and 33 are the hidden deformation values.
  - +0xB0 64 texture bytes. Texture byte 25 is 148 for female and 128 for male; the script sets it from `gender`.
- Layering in `write`:
  - It starts from `TEMPLATE_HEX`, a game-written favourite (the author's character), which supplies the structure and hidden bytes.
  - Then it applies `BASE_PRESET` (FromSoftware's default face), then the preset.
  - The base leaves out beard colour, tattoo colour and the tattoo tweak. The template's values there are the game's own defaults (Iosefka matched the game's face file with them), and the default-face sheet's values look wrong.
  - All NPC presets except 9 come out byte for byte the same with or without the base. Those 9 lack hair, brow or eyelash colour in the sheet and now get neutral defaults instead of the template's white hair.
- Voice is **not** in favourites. Tested Oct 2026: with the voice set to Mature, loading favourites of any age (including aged Djura) and slots with header bytes 2, 4 or 8 changed never changed it. It's stored per character only.
- Character slots (`userdata0000`–`0009`) contain the same block. Noxde's Bloodborne Save Editor imports whole blobs there and reportedly works. Our one early test of that seemed to have no effect but wasn't conclusive, so prefer favourites.
- Prior art:
  - Noxde/Bloodborne-save-editor (whole-blob import and export, 4 NPC faces).
  - Herne's NPC spreadsheet.
  - Zullie the Witch's face-data videos.
  - Hapfel's Elden Ring Save Manager, the model this preset JSON follows.

## Fallback: drive the in-game editor (slow, about 20 min)
Only use this when the save can't be edited.

**Setup (example: bbport on Windows):**
- Computer use with "Play Bloodborne" (the launcher) and "bb-probe.exe". Resolve it by that exact name; it lives in `<install>\bin\` and owns the game window, which shows as a grey mask until it's granted.
- Click into the game first, and if the desktop shell has focus, request File Explorer click access.
- Keys (bbport defaults from `input.ini`; check yours): space = OK, left shift = back, I/K/J/L = d-pad, 1/3 = ±10, Enter = skip cutscene.

**Getting to the editor:** title → Play Offline → New Game → Enter → Contract → Gender → Appearance.
- The Appearance menu is: Gender, Age, Voice, Build, Scale Adjustment, Base Skin Colour, Skin Colour, Face Details, Load Favourite, Save to Favourites, Default. Menus don't wrap reliably, so move down with K and zoom in to check where the cursor is.
- Face Details is: Face Presets, Similar Face, Features, Face Shape (11 pages), Skin Colour/Makeup, Hair/Facial Hair, Pupils, Tattoo/Mark/Glasses.

**Pacing:**
- Each press is `hold_key` for 0.05 s, then a 0.6 s wait. Wait at least 1.2 s before reading values.
- Keep batches to about 55 presses or fewer, because each must finish within 60 s.
- Work closed-loop: read each page, send the presses, read again, and fix any differences.

**Saving:**
- Colour pages and picker grids need OK to stick.
- Save to Favourites, then finish the contract (ask first; it creates a throwaway character) so the favourite reaches the disk.