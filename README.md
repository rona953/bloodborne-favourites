# bloodborne-favourites

Write a Bloodborne character's appearance straight into one of the game's 8 **Favourite** slots, so you can load it in the character creator (New Game → Appearance → Load Favourite) instead of copying 100+ sliders by hand.

It works on **unencrypted saves**: shadPS4, bbport, or a PS4 save that has already been decrypted. Encrypted PS4 saves won't work.

## What's included

| Path | What it is |
|---|---|
| `bb_favourite.py` | The writer: list, write, dump and delete favourite slots. Python 3, no dependencies. |
| `presets/` | 37 NPC faces plus FromSoftware's default face, converted from Herne's *Bloodborne NPC Face Data Compilation*. See `presets/INDEX.md`. |
| `presets_user/` | Player characters transcribed from r/bloodbornesliders posts. |
| `example_preset.json` | A complete player preset that shows the format. |
| `herne_to_presets.py` | Rebuilds `presets/` from Herne's spreadsheet (needs `openpyxl`). |
| `skill/bloodborne-character-sliders/` | A Claude skill: give Claude slider screenshots or an Imgur album and it writes the favourite for you. |

## Usage

**Close the game first.** It keeps favourites in memory and rewrites the save file when it quits, which would wipe your edit.

```sh
# SAVE is the SPRJ0005 folder, e.g. <bbport>/user/savedata/1/CUSA00207/SPRJ0005
python3 bb_favourite.py list   SAVE
python3 bb_favourite.py write  SAVE presets/iosefka.json            # first free slot
python3 bb_favourite.py write  SAVE presets_user/caroline.json --slot 7 --force
python3 bb_favourite.py dump   SAVE --slot 1 > my_character.json     # export to share
python3 bb_favourite.py delete SAVE --slot 8
```

Every write makes a timestamped `userdata0010.bak-*` backup next to the save, then reads the file back to check it.

Then start the game: **New Game → Appearance → Load Favourite**.

**Voice is not stored in favourites.** The game keeps it per character, not per favourite. After loading, set it under Appearance → Voice. The script prints a suggestion: the preset's `voice`, or a guess from the character's age.

## Preset format

Presets are JSON, and keys use the in-game menu labels (case and punctuation don't matter). Sliders run 0–255. Unknown keys are rejected, so typos get caught. A few rules:

- **Grid choices** (`Hair`, `Brow`, `Beard`, `Eyelashes`, `Glasses`, `Tattoo/Mark`) take any of:
  - a 0-based position, read left to right then top to bottom;
  - a 1-based `"row,col"`;
  - text like `"3rd down, 2nd across"`.
- **Base Skin Colour** takes `[R,G,B]` or a palette position `"row,col"`. The palette is 5 across × 8 down; row 1 is exact and the rest are close approximations.
- **Pupil size:** `medium`, `small`, `large` or `clouded`. Clouded is NPC-only, but it works.
- **Missing fields** fall back to FromSoftware's default face, and the script lists which ones it filled.

Run `python3 bb_favourite.py -h` for the full field notes and the reverse-engineered save layout.

## How it was verified (Oct 2026, bbport)

- A favourite saved by the game is reproduced byte for byte.
- The Iosefka preset matches the game's own face data byte for byte.
- Gender, age and clouded eyes load correctly in game.

## Credits

- **Herne:** *Bloodborne NPC Face Data Compilation* (linked from [bloodborne-wiki.com/p/sliders.html](https://www.bloodborne-wiki.com/p/sliders.html)), the source of `presets/`.
- **[Noxde/Bloodborne-save-editor](https://github.com/Noxde/Bloodborne-save-editor):** face-blob import/export, which confirmed the field layout.
- **Zullie the Witch:** research into face data.
- **Slider posts:** the characters in `presets_user/` are by their original posters on r/bloodbornesliders and Imgur; each file's `source` links back.
