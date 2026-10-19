#!/usr/bin/env python3
"""
bb_favourite.py - write a Bloodborne character appearance into an in-game
"Favourite" slot, directly in an unencrypted save (shadPS4 / bbport / any
decrypted PS4 save).

    python bb_favourite.py list   SAVE
    python bb_favourite.py write  SAVE preset.json [--slot N] [--force] [--base default|template]
    python bb_favourite.py dump   SAVE --slot N  > preset.json
    python bb_favourite.py delete SAVE --slot N

SAVE is the SPRJ0005 save folder or its userdata0010 file.
The game must be CLOSED: it keeps favourites in memory and overwrites
userdata0010 on quit. Every write makes a timestamped backup first.

Preset format: JSON (see example_preset.json / presets/). Keys are the in-game
menu labels (case/spacing/punctuation-insensitive). Sliders are 0-255.
Grid choices (Hair, Brow, Beard, Eyelashes, Glasses, Tattoo/Mark) take either a
number (0-based position in the 3-wide grid, read left-to-right, top-to-bottom;
for Hair this is converted to the game's hair id) or "row,col" (1-based).
Base Skin Colour takes [R,G,B] or a palette position "row,col" (5-wide grid;
palette RGB values are approximate except the first row).
Unknown keys are rejected so typos are caught.
Fields the preset leaves out come from FromSoftware's default face (presets/fromsoft_default.json,
embedded below as BASE_PRESET); --base template keeps the raw template's values instead.
Voice is not stored in favourites; a 'voice' key (youthful/mature/aged) is only printed as a reminder.

Format (reverse-engineered Oct 2026; verified in game and against 37 NPCs):
  userdata0010 @0x88: u32 0x1000, u32 0xFACE, u32 0x800, then 8 slots x 0x100 @0x94
  slot: [01, gender?, 00, 00] then 12 zero bytes, then a FACE block (0xF0)
  FACE+0x0C u32 age?  +0x10 hair id  +0x14 left pupil  +0x18 right pupil
      +0x1C brow  +0x20 beard  +0x24 glasses  +0x28 tattoo/mark  +0x2C eyelashes
  FACE+0x30 9 x RGBA: base skin, hair, left pupil, right pupil, brow, beard,
      glasses, tattoo/mark, eyelash
  FACE+0x54 tattoo tweak: horizontal, vertical, angle, expansion
  FACE+0x58 body scale x5, FACE+0x70 64 face-shape bytes, FACE+0xB0 64 texture bytes
  Hair id = grid position for positions 0-10, position + 90 from 11 on.
  Pupil "size": 0 medium, 1 small, 2 large, 3/4/5 = clouded medium/small/large.
"""
import argparse, json, os, re, shutil, struct, sys, time

SLOT_BASE, SLOT_SIZE, NSLOTS = 0x94, 0x100, 8
F = 0x10                      # FACE magic offset inside a slot

# A complete slot written by the game (female); fields a preset omits keep these values.
TEMPLATE_HEX = (
 "010100000000000000000000000000004641434503000000f0000000000000006a000000"
 "0100000001000000030000000000000007000000000000000400000096877dfff5d7d2ff"
 "d0ae64ffd0ae64ff000000ff7c3c0aff000000ff141414ff000000ffb4640028ff0aa400"
 "a10000000000000000000000000000000000000000d76e80ff86867360b9ff96ba965894"
 "9a42d450af9ba77f00805ab9949b8087a28073e18c64f51404ff005926bad05dc76c3c91"
 "1d697a6e7cff7b887c8d4138808080808080806db47580808080808080808082a0a5a380"
 "8094806e6e8c71b780fd72f55d8080808080808080808080808080808080808080808080"
 "80808000")

def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

SHAPE, TEX, SCALE, TWEAK = 0x70, 0xB0, 0x58, 0x54
SHAPE_FIELDS = [  # face-shape byte index -> (section, label)
 ("features","Apparent Age"),("features","Facial Aesthetic"),("features","Form Emphasis"),
 ("hidden","Hidden Deformation 1"),
 ("brow ridge","Brow Ridge Height"),("brow ridge","Inner Brow Ridge"),("brow ridge","Outer Brow Ridge"),
 ("cheeks","Cheekbone Height"),("cheeks","Cheekbone Depth"),("cheeks","Cheekbone Width"),
 ("cheeks","Cheekbone Protrusion"),("cheeks","Cheek Thickness"),
 ("chin","Chin Tip Position"),("chin","Chin Length"),("chin","Chin Protrusion"),("chin","Chin Depth"),
 ("chin","Chin Size"),("chin","Chin Height"),("chin","Chin Width"),
 ("eyes","Eye Position"),("eyes","Eye Size"),("eyes","Eye Slant"),("eyes","Eye Spacing"),
 ("facial balance","Nose Size"),("facial balance","Nose/Forehead Ratio"),
 ("hidden","Hidden Deformation 2"),
 ("facial balance","Face Protrusion"),("facial balance","Vertical Facial Spacing"),
 ("facial balance","Facial Feature Slant"),("facial balance","Horizontal Facial Spacing"),
 ("hidden","Hidden Deformation 3"),
 ("forehead/glabella","Forehead Depth"),("forehead/glabella","Forehead Protrusion"),
 ("hidden","Hidden Deformation 4"),
 ("jaw","Jaw Protrusion"),("jaw","Jaw Width"),("jaw","Lower Jaw"),("jaw","Jaw Contour"),
 ("lips","Lip Shape"),("lips","Mouth Expression"),("lips","Lip Fullness"),("lips","Lip Size"),
 ("lips","Lip Protrusion"),("lips","Lip Thickness"),
 ("mouth","Mouth Protrusion"),("mouth","Mouth Slant"),("mouth","Occlusion"),("mouth","Mouth Position"),
 ("mouth","Mouth Width"),("mouth","Mouth-Chin Distance"),
 ("nose ridge","Nose Ridge Depth"),("nose ridge","Nose Ridge Length"),("nose ridge","Nose Position"),
 ("nose ridge","Nose Tip Height"),
 ("nostrils","Nostril Slant"),("nostrils","Nostril Size"),("nostrils","Nostril Width"),
 ("nose ridge","Nose Protrusion"),
 ("forehead/glabella","Nose Bridge Height"),("forehead/glabella","Bridge Protrusion 1"),
 ("forehead/glabella","Bridge Protrusion 2"),("forehead/glabella","Nose Bridge Width"),
 ("nose ridge","Nose Height"),("nose ridge","Nose Slant"),
]
TEX_FIELDS = {7:("skin colour","Cheek Colour"), 8:("eye area","Tone Around Eyes"),
 9:("eye area","Eye Socket Brightness"), 19:("eye area","Eyelid Brightness"),
 20:("eye area","Eyelid Colour"), 21:("eye area","Eyeliner"), 22:("eye area","Eye Shadow"),
 27:("lipstick","Lipstick 1"), 28:("lipstick","Lipstick 2"), 29:("skin colour","Laugh Lines"),
 30:("nostrils","Nasal Size"), 31:("skin colour","Nose Bridge Colour"), 33:("skin colour","Skin Tone"),
 34:("skin colour","Skin Colour Layer 1"), 35:("skin colour","Skin Colour Layer 2"),
 36:("skin colour","Skin Colour Layer 3")}
SCALE_FIELDS = ["Head","Chest","Abdomen","Arms","Legs"]
TWEAK_FIELDS = ["Position (Horizontal)","Position (Vertical)","Angle","Expansion"]
GRID_ITEMS = {"Hair":0x10, "Brow":0x1C, "Beard":0x20, "Glasses":0x24, "Tattoo/Mark":0x28, "Eyelashes":0x2C}
PUPILS = {"Left Pupil Size":0x14, "Right Pupil Size":0x18}
COLOURS = {"Base Skin Colour":0x30, "Hair Colour":0x34, "Left Pupil Colour":0x38,
           "Right Pupil Colour":0x3C, "Brow Colour":0x40, "Beard Colour":0x44,
           "Colour of Glasses":0x48, "Tattoo/Mark Colour":0x4C, "Eyelash Colour":0x50}
PUPIL_NAMES = {"medium":0, "normal":0, "small":1, "large":2, "clouded":3, "cloudedmedium":3,
               "cloudedsmall":4, "cloudedlarge":5}
AGES = {"young":0, "mature":1, "aged":2}
# Base skin palette, 8 rows x 5 cols. Row 1 and (2,1) are exact; the rest were
# sampled from an in-game screenshot and are approximate (within a few units).
PALETTE = [
 [(140,125,115),(145,130,120),(150,135,125),(155,140,130),(160,145,135)],
 [(90,87,83),(99,93,87),(111,101,90),(117,106,95),(121,110,100)],
 [(126,117,101),(134,121,104),(140,126,110),(145,131,114),(149,136,119)],
 [(126,108,93),(137,119,103),(148,130,113),(158,140,124),(167,149,132)],
 [(119,100,92),(129,110,102),(140,121,113),(149,129,122),(159,140,131)],
 [(110,100,91),(120,110,101),(130,121,111),(140,130,121),(149,140,130)],
 [(89,84,80),(104,99,94),(119,114,110),(134,129,125),(148,144,140)],
 [(101,95,85),(111,106,95),(121,117,105),(131,126,116),(141,136,124)]]

SLIDERS = {}
for i, f in enumerate(SHAPE_FIELDS): SLIDERS[norm(f[1])] = SHAPE + i
for i, f in TEX_FIELDS.items(): SLIDERS[norm(f[1])] = TEX + i
for i, n in enumerate(SCALE_FIELDS): SLIDERS[norm(n)] = SCALE + i
for i, n in enumerate(TWEAK_FIELDS): SLIDERS[norm(n)] = TWEAK + i

ALIASES = {"vertfacialspacing":"verticalfacialspacing", "horizfacialspacing":"horizontalfacialspacing",
           "positionverticle":"positionvertical", "tattoo":"tattoomark", "sizeofpupils":"pupilsize",
           "colourofpupils":"pupilcolour", "glassescolour":"colourofglasses", "hairstyle":"hair"}

def canon(key):
    k = norm(key).replace("color", "colour")
    return ALIASES.get(k, k)

def grid_index(val, cols):
    """number -> index; 'r,c' or 'Nth down, Mth across' -> (r-1)*cols+(c-1)."""
    if isinstance(val, int): return val
    s = str(val).strip().lower()
    if re.fullmatch(r"\d+", s): return int(s)
    m = re.fullmatch(r"(\d+)\s*,\s*(\d+)", s)
    if m: return (int(m[1]) - 1) * cols + int(m[2]) - 1
    r = re.search(r"(\d+)\w*\s*down", s); c = re.search(r"(\d+)\w*\s*across", s)
    if r or c or s.startswith("1st"):
        return ((int(r[1]) - 1) if r else 0) * cols + ((int(c[1]) - 1) if c else 0)
    raise ValueError(f"can't read grid position {val!r}")

def hair_id(idx): return idx if idx <= 10 else idx + 90
def hair_index(hid): return hid if hid <= 10 else hid - 90

def find_file(path):
    if os.path.isdir(path): path = os.path.join(path, "userdata0010")
    if not os.path.isfile(path): sys.exit(f"not found: {path}")
    return path

def load(path):
    d = bytearray(open(path, "rb").read())
    if struct.unpack_from("<III", d, 0x88) != (0x1000, 0xFACE, 0x800):
        sys.exit("favourites header not found - not an unencrypted Bloodborne userdata0010?")
    return d

def slot_off(i): return SLOT_BASE + i * SLOT_SIZE
def used(d, i): return d[slot_off(i)] == 1 and d[slot_off(i)+F:slot_off(i)+F+4] == b"FACE"

def backup(path):
    base = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"; dst, n = base, 1
    while os.path.exists(dst): dst = f"{base}-{n}"; n += 1
    shutil.copy2(path, dst); return dst

def put_u32(slot, off, v): struct.pack_into("<I", slot, F + off, int(v))

# FromSoftware's default face (Herne's sheet), applied before the preset so missing fields are neutral.
# Beard colour, tattoo colour and tattoo tweak are left to the template: its values there are the game's
# own defaults (they make Iosefka match the game's face file byte for byte), while the sheet's look off.
BASE_PRESET = json.loads(r'''{"gender": "male", "age": "young", "colours": {"Base Skin Colour": "2nd across", "Hair Colour": [150, 145, 140], "Brow Colour": [150, 145, 140], "Eyelash Colour": [150, 145, 130], "Pupil Colour": [120, 90, 90]}, "scale adjustment": {"Head": 128, "Chest": 128, "Abdomen": 128, "Arms": 128, "Legs": 128}, "skin colour": {"Skin Tone": 128, "Skin Colour Layer 1": 128, "Skin Colour Layer 2": 113, "Skin Colour Layer 3": 255, "Nose Bridge Colour": 128, "Cheek Colour": 128, "Laugh Lines": 128}, "features": {"Apparent Age": 138, "Facial Aesthetic": 128, "Form Emphasis": 128}, "facial balance": {"Nose Size": 127, "Nose/Forehead Ratio": 127, "Face Protrusion": 127, "Vertical Facial Spacing": 127, "Facial Feature Slant": 127, "Horizontal Facial Spacing": 127}, "forehead/glabella": {"Forehead Depth": 127, "Forehead Protrusion": 127, "Nose Bridge Height": 127, "Bridge Protrusion 1": 127, "Bridge Protrusion 2": 127, "Nose Bridge Width": 127}, "brow ridge": {"Brow Ridge Height": 127, "Inner Brow Ridge": 127, "Outer Brow Ridge": 127}, "eyes": {"Eye Position": 127, "Eye Size": 127, "Eye Slant": 127, "Eye Spacing": 127}, "nose ridge": {"Nose Ridge Depth": 127, "Nose Ridge Length": 127, "Nose Position": 127, "Nose Tip Height": 127, "Nose Protrusion": 127, "Nose Height": 127, "Nose Slant": 127}, "nostrils": {"Nostril Slant": 127, "Nostril Size": 127, "Nostril Width": 127, "Nasal Size": 128}, "cheeks": {"Cheekbone Height": 127, "Cheekbone Depth": 127, "Cheekbone Width": 127, "Cheekbone Protrusion": 127, "Cheek Thickness": 127}, "lips": {"Lip Shape": 127, "Mouth Expression": 127, "Lip Fullness": 127, "Lip Size": 127, "Lip Protrusion": 127, "Lip Thickness": 127}, "mouth": {"Mouth Protrusion": 127, "Mouth Slant": 127, "Occlusion": 127, "Mouth Position": 127, "Mouth Width": 127, "Mouth-Chin Distance": 127}, "chin": {"Chin Tip Position": 127, "Chin Length": 127, "Chin Protrusion": 127, "Chin Depth": 127, "Chin Size": 127, "Chin Height": 127, "Chin Width": 127}, "jaw": {"Jaw Protrusion": 127, "Jaw Width": 127, "Lower Jaw": 127, "Jaw Contour": 127}, "eye area": {"Tone Around Eyes": 128, "Eye Socket Brightness": 128, "Eyelid Brightness": 128, "Eyelid Colour": 128, "Eyeliner": 128, "Eye Shadow": 128}, "lipstick": {"Lipstick 1": 128, "Lipstick 2": 128}, "items": {"Hair": "2nd down", "Brow": "2nd across", "Beard": "2nd down, 2nd across", "Eyelashes": "2nd across", "Pupil Size": "medium", "Tattoo/Mark": "2nd across", "Glasses": 0}}''')

def preset_keys(preset):
    """Canonical keys a preset sets (nested sections flattened)."""
    cols = {canon(a) for a in COLOURS}
    out = set()
    def walk(o):
        for k, v in o.items():
            if isinstance(v, dict) and canon(k) not in cols: walk(v)
            elif v is not None: out.add(canon(k))
    walk(preset); return out

def apply_preset(slot, preset):
    unknown, n = [], 0
    cols = {canon(a): o for a, o in COLOURS.items()}
    grids = {canon(a): (a, o) for a, o in GRID_ITEMS.items()}
    pupils = {canon(a): o for a, o in PUPILS.items()}
    def flat(obj):
        for k, v in obj.items():
            if isinstance(v, dict) and canon(k) not in cols: yield from flat(v)
            else: yield k, v
    for key, val in flat(preset):
        k = canon(key)
        if val is None or k in ("name", "notes", "source", "author", "voice", "tags"): continue
        if k in SLIDERS:
            v = int(val); assert 0 <= v <= 255, f"{key}={v} out of range"
            slot[F + SLIDERS[k]] = v
        elif k == "gender":
            slot[1] = {"female": 1, "male": 0}[norm(val)]
        elif k == "age":
            put_u32(slot, 0x0C, AGES[norm(val)] if isinstance(val, str) else int(val))
        elif k == "hairid":
            put_u32(slot, 0x10, int(val))
        elif k in grids:
            name, off = grids[k]
            idx = grid_index(val, 3)
            put_u32(slot, off, hair_id(idx) if name == "Hair" else idx)
        elif k in pupils or k == "pupilsize":
            v = PUPIL_NAMES[norm(val)] if isinstance(val, str) and not val.isdigit() else int(val)
            assert 0 <= v <= 5, f"{key}: pupil size 0-5"
            for o in ([pupils[k]] if k in pupils else PUPILS.values()): put_u32(slot, o, v)
        elif k in cols or k == "pupilcolour":
            if k == "baseskincolour" and isinstance(val, str):
                i = grid_index(val, 5); rgb = PALETTE[i // 5][i % 5]
            else:
                rgb = list(val.values()) if isinstance(val, dict) else list(val)
            assert len(rgb) == 3 and all(0 <= int(c) <= 255 for c in rgb), f"{key} needs [R,G,B]"
            for o in ([cols[k]] if k in cols else [COLOURS["Left Pupil Colour"], COLOURS["Right Pupil Colour"]]):
                slot[F + o:F + o + 3] = bytes(int(c) for c in rgb)
        else:
            unknown.append(key); continue
        n += 1
    if unknown: sys.exit("unknown keys in preset: " + ", ".join(unknown))
    # texture byte 25 is a hidden, gender-dependent value (148 female / 128 male in game data)
    if "gender" in {canon(k) for k, _ in flat(preset)}: slot[F + TEX + 25] = 148 if slot[1] == 1 else 128
    return n

VOICES = {"youthful": "Youthful Voice", "mature": "Mature Voice", "aged": "Aged Voice"}

def guess_voice(preset):
    """Favourites don't store the voice (checked in game: loading one never changes it),
    so this only suggests what to pick in Appearance -> Voice. An explicit "voice" key wins;
    otherwise it follows age, nudged by the Apparent Age slider."""
    v = preset.get("voice")
    if v:
        k = norm(v).replace("voice", "")
        k = {"0": "youthful", "1": "mature", "2": "aged"}.get(k, k)
        return VOICES.get(k, str(v)), "from preset"
    age = preset.get("age", "young")
    i = AGES[norm(age)] if isinstance(age, str) else int(age)
    app = (preset.get("features") or {}).get("Apparent Age", 128)
    try: app = int(app)
    except (TypeError, ValueError): app = 128
    if i == 0 and app >= 200: i = 1
    elif i == 1 and app >= 220: i = 2
    elif i == 1 and app <= 40: i = 0
    return list(VOICES.values())[min(2, i)], "guessed from age"

def dump(slot):
    out = {"gender": "female" if slot[1] == 1 else "male",
           "age": ["young", "mature", "aged"][min(2, struct.unpack_from("<I", slot, F+0x0C)[0])]}
    for i, f in enumerate(SHAPE_FIELDS): out.setdefault(f[0], {})[f[1]] = slot[F + SHAPE + i]
    for i, f in TEX_FIELDS.items(): out.setdefault(f[0], {})[f[1]] = slot[F + TEX + i]
    out["scale adjustment"] = {n: slot[F + SCALE + i] for i, n in enumerate(SCALE_FIELDS)}
    out["tweak tattoo/mark"] = {n: slot[F + TWEAK + i] for i, n in enumerate(TWEAK_FIELDS)}
    items = {}
    for n, o in GRID_ITEMS.items():
        v = struct.unpack_from("<I", slot, F + o)[0]
        items[n] = hair_index(v) if n == "Hair" else v
    for n, o in PUPILS.items(): items[n] = struct.unpack_from("<I", slot, F + o)[0]
    out["items"] = items
    out["colours"] = {n: list(slot[F + o:F + o + 3]) for n, o in COLOURS.items()}
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "write", "dump", "delete"])
    ap.add_argument("save"); ap.add_argument("preset", nargs="?")
    ap.add_argument("--slot", type=int, help="favourite slot 1-8 (write: default = first free)")
    ap.add_argument("--force", action="store_true", help="overwrite a used slot")
    ap.add_argument("--base", choices=["default", "template"], default="default",
                    help="where fields missing from the preset come from (default: FromSoftware's default face)")
    a = ap.parse_args()
    path = find_file(a.save); d = load(path)
    if a.cmd == "list":
        for i in range(NSLOTS): print(f"slot {i+1}: " + ("in use" if used(d, i) else "empty"))
        return
    if a.cmd == "dump":
        assert a.slot and used(d, a.slot - 1), "--slot must be a used slot"
        o = slot_off(a.slot - 1)
        print(json.dumps(dump(d[o:o + SLOT_SIZE]), indent=2)); return
    if a.cmd == "delete":
        assert a.slot, "--slot required"
        b = backup(path); o = slot_off(a.slot - 1)
        d[o:o + SLOT_SIZE] = bytes(SLOT_SIZE); open(path, "wb").write(d)
        print(f"deleted slot {a.slot} (backup: {b})"); return
    preset = json.load(open(a.preset, encoding="utf-8"))
    i = (a.slot - 1) if a.slot else next((j for j in range(NSLOTS) if not used(d, j)), None)
    if i is None: sys.exit("all 8 favourite slots are used - pass --slot N --force")
    if used(d, i) and not a.force: sys.exit(f"slot {i+1} is in use - add --force to overwrite")
    slot = bytearray.fromhex(TEMPLATE_HEX); assert len(slot) == SLOT_SIZE
    missing = []
    if a.base == "default":
        apply_preset(slot, BASE_PRESET)
        have = preset_keys(preset)
        if "pupilsize" in have: have |= {"leftpupilsize", "rightpupilsize"}
        if "pupilcolour" in have: have |= {"leftpupilcolour", "rightpupilcolour"}
        missing = sorted(k for k in preset_keys(BASE_PRESET) - have
                         if k not in ("pupilsize", "pupilcolour") or not ({"left" + k, "right" + k} <= have))
    n = apply_preset(slot, preset)
    b = backup(path); o = slot_off(i)
    d[o:o + SLOT_SIZE] = slot; open(path, "wb").write(d)
    assert open(path, "rb").read()[o:o + SLOT_SIZE] == bytes(slot), "read-back mismatch!"
    print(f"wrote {n} fields to favourite slot {i+1} ({preset.get('name','preset')}) - backup: {b}")
    if missing: print(f"{len(missing)} fields not in the preset used FromSoftware's default face: " + ", ".join(missing))
    print("Start the game -> New Game -> Appearance -> Load Favourite.")
    voice, why = guess_voice(preset)
    print(f"Voice isn't stored in favourites: pick '{voice}' under Appearance -> Voice ({why}).")

if __name__ == "__main__":
    main()
