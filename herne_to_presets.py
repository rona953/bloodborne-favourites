#!/usr/bin/env python3
"""Convert Herne's 'Bloodborne NPC Face Data Compilation.xlsx' into bb_favourite presets.
usage: herne_to_presets.py npc.xlsx outdir/"""
import json, os, re, sys
import openpyxl

COLOUR_HEADERS = {"Hair/Brow/Beard Colour": ["Hair Colour", "Brow Colour", "Beard Colour"],
    "Hair Colour": ["Hair Colour"], "Brow Colour": ["Brow Colour"], "Beard Colour": ["Beard Colour"],
    "Eyelash Colour": ["Eyelash Colour"], "Colour of Pupils": ["Pupil Colour"],
    "Right Pupil Colour": ["Right Pupil Colour"], "Left Pupil Colour": ["Left Pupil Colour"],
    "Tattoo/Mark Colour": ["Tattoo/Mark Colour"], "Colour of Glasses": ["Colour of Glasses"]}
GRID = {"Hair": "Hair", "Brow": "Brow", "Beard": "Beard", "Eyelashes": "Eyelashes",
        "Tattoo": "Tattoo/Mark", "Glasses": "Glasses"}
PUPIL = {"Size of Pupils": "Pupil Size", "Right Pupil Size": "Right Pupil Size", "Left Pupil Size": "Left Pupil Size"}
SECTIONS = {"SCALE ADJUSTMENT", "SKIN COLOUR", "FEATURES", "FACIAL BALANCE", "FOREHEAD/GLABELLA",
    "BROW RIDGE", "EYES", "NOSE RIDGE", "NOSTRILS", "CHEEKS", "LIPS", "MOUTH", "CHIN", "JAW",
    "EYE AREA", "LIPSTICK", "HAIR/FACIAL HAIR", "PUPILS", "TATTOO/MARK/GLASSES", "TWEAK TATTOO/MARK"}

def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def pupil(v):
    s = str(v).lower()
    if "unav" in s: return "clouded"
    return s.strip()

def main(xlsx, out):
    ws = openpyxl.load_workbook(xlsx, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    npcs = [(c, n) for c, n in enumerate(rows[0]) if n]
    alt = {c: rows[1][c] for c, _ in npcs if rows[1][c]}
    os.makedirs(out, exist_ok=True); index = []
    for c, name in npcs:
        p = {"name": name, "source": "Herne's Bloodborne NPC Face Data Compilation (via bloodborne-wiki.com/p/sliders.html)"}
        if c in alt: p["notes"] = f"also used by: {alt[c]}"
        notes = []; section = "misc"; i = 0
        while i < len(rows):
            label, v = rows[i][0], rows[i][c]
            i += 1
            if not label: continue
            label = str(label).strip()
            if label in SECTIONS: section = label.lower(); continue
            if label in COLOUR_HEADERS:
                rgb = [rows[i + k][c] for k in range(3)]; i += 3
                if all(x is not None for x in rgb):
                    for tgt in COLOUR_HEADERS[label]:
                        p.setdefault("colours", {})[tgt] = [int(x) for x in rgb]
                continue
            if v is None: continue
            if label == "GENDER": p["gender"] = str(v).lower(); continue
            if label == "AGE": p["age"] = str(v).lower(); continue
            if label == "VOICE": p["voice"] = str(v); notes.append(f"voice: {v} (set in game)"); continue
            if label == "BASE SKIN COLOUR":
                p.setdefault("colours", {})["Base Skin Colour"] = str(v); continue
            if label in GRID: p.setdefault("items", {})[GRID[label]] = str(v); continue
            if label in PUPIL:
                p.setdefault("items", {})[PUPIL[label]] = pupil(v)
                if "unav" in str(v).lower(): notes.append("clouded eyes (not available in the normal editor)")
                continue
            if isinstance(v, (int, float)):
                p.setdefault(section, {})[label] = int(v)
            else:
                notes.append(f"{label}: {v}")
        if "voice" not in p:  # the sheet rarely lists it; guess from age (favourites can't store it anyway)
            p["voice"] = {"young": "Youthful", "mature": "Mature", "aged": "Aged"}.get(p.get("age", "young"), "Youthful")
            notes.append(f"voice: {p['voice']} (guessed from age; set in game)")
        items = p.setdefault("items", {})
        for k in ("Beard", "Glasses", "Tattoo/Mark"): items.setdefault(k, 0)
        if notes: p["notes"] = "; ".join(filter(None, [p.get("notes")] + notes))
        fn = slug(name) + ".json"
        json.dump(p, open(os.path.join(out, fn), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        index.append((name, fn, p.get("gender"), p.get("age"), p.get("voice")))
    with open(os.path.join(out, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("# NPC presets\n\nSource: Herne's Bloodborne NPC Face Data Compilation (bloodborne-wiki.com/p/sliders.html).\n\n")
        f.write("Voice is not stored in favourites; pick it in Appearance -> Voice after loading.\n\n")
        for n, fn, g, a, vo in index: f.write(f"- {n} ({g}, {a}, {vo} voice): `{fn}`\n")
    print(f"wrote {len(index)} presets to {out}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
