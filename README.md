# Bloodborne character sliders: a Claude skill

Give Claude a character from an Imgur album, a YouTube slider video or a few screenshots, and it puts that character into one of your **Favourite** slots. Then open the character creator and choose **Load Favourite**. No copying 100+ sliders by hand.

Under the hood, Claude reads the slider values from the images and writes them straight into your save file. It also comes with 37 NPC faces ready to use.

## What you can ask

- "Make this character: https://imgur.com/a/…"
- "Make the character from this video: https://www.youtube.com/watch?v=…"
- *(attach screenshots)* "Put this character in a favourite slot."
- "Give me Djura's face." / "Which NPC presets are there?"
- "Export my favourite in slot 1 so I can share it."
- "Delete favourite slot 8."

Claude reads every slider page (or video frame), checks pickers that scroll, and asks you about blurry digits. It writes the favourite (with a backup first) and tells you:
- which slot it went into;
- which voice to pick, because favourites don't store the voice;
- which values it had to estimate or fill in from the default face.

## Requirements

- **An unencrypted Bloodborne save:** shadPS4, bbport, or a PS4 save that has already been decrypted. Encrypted PS4 saves won't work.
- **Claude able to reach your save folder and run Python 3:** Claude Code, or the Claude desktop app with your Bloodborne folder connected.
- **The game closed while Claude writes.** The game keeps favourites in memory and overwrites the save file when it quits.
- **For Imgur links:** the Claude desktop app's built-in browser. Imgur counts as a high-risk site there, so you approve each step; expect about 2 prompts per 6 screenshots.
- **For YouTube links:** the same built-in browser. No approval prompts. Claude scans the video's frames in the page, keeps one per menu page, and reads them; nothing is downloaded. A 3-minute video takes a few minutes.
- **Reddit links don't work:** Claude can't open reddit.com. Paste the post's Imgur link, or attach the screenshots instead.

## Install

**Claude Code:** clone into your skills folder.

```sh
git clone https://github.com/rona953/bloodborne-favourites ~/.claude/skills/bloodborne-character-sliders
```

**Claude app:**
1. Download this repo as a ZIP.
2. Rename the folder inside to `bloodborne-character-sliders`, keeping `SKILL.md` at its top level.
3. Zip that folder and upload it as a custom skill in the app's settings.

Then just ask, for example "make this Bloodborne character: <link>". Your save folder is usually `…/savedata/<user>/CUSA00207/SPRJ0005`; Claude asks for it if it isn't sure.

## What's inside

| Path | What it is |
|---|---|
| `SKILL.md` | The skill: how Claude reads sliders, writes favourites and handles edge cases. |
| `scripts/bb_favourite.py` | The writer Claude runs: list, write, dump and delete favourites. Python 3, no dependencies. |
| `presets/` | 37 NPC faces plus FromSoftware's default face, from Herne's *Bloodborne NPC Face Data Compilation*. See `presets/INDEX.md`. |
| `presets_user/` | Player characters transcribed from posts. Each one links its source. |
| `example_preset.json` | A complete player preset that shows the format. |
| `scripts/herne_to_presets.py` | Rebuilds `presets/` from Herne's spreadsheet (needs `openpyxl`). |

## Sharing characters

Transcribed a character? Add it to `presets_user/` with a `source` link to the original post and open a pull request. To export a character you made yourself, ask Claude to dump that favourite slot.

## Without Claude

The script works on its own. Presets are JSON keyed by the in-game menu labels, and `-h` explains the format.

```sh
python3 scripts/bb_favourite.py list   SAVE
python3 scripts/bb_favourite.py write  SAVE presets/iosefka.json [--slot N] [--force]
python3 scripts/bb_favourite.py dump   SAVE --slot 1 > my_character.json
python3 scripts/bb_favourite.py delete SAVE --slot 8
```

## How it was verified (Oct 2026, bbport)

- A favourite saved by the game is reproduced byte for byte.
- The Iosefka preset matches the game's own face data byte for byte.
- Gender, age and clouded eyes load correctly in game.
- Voice is confirmed not to be part of a favourite.

## Credits

- **Herne:** *Bloodborne NPC Face Data Compilation* (linked from [bloodborne-wiki.com/p/sliders.html](https://www.bloodborne-wiki.com/p/sliders.html)), the source of `presets/`.
- **[Noxde/Bloodborne-save-editor](https://github.com/Noxde/Bloodborne-save-editor):** face-blob import/export, which confirmed the field layout.
- **Zullie the Witch:** research into face data.
- **Slider posts:** the characters in `presets_user/` are by their original posters on r/bloodbornesliders and Imgur.
