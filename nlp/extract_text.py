"""Extract structured text from Pushing Daisies PDF scripts.

Screenplay format detection:
  - SCENE HEADINGS: lines starting with INT. / EXT.
  - CHARACTER NAMES: short ALLCAPS lines (centred in PDF) before dialogue
  - DIALOGUE: lines immediately below a character name
  - ACTION: everything else
"""
import json
import os
import re
import pdfplumber

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

SCRIPTS = [
    ("1", "1", "Pie-Lette",                   "Pushing_Daisies_1x01_-_Pie-Lette.pdf"),
    ("1", "2", "Dummy",                        "Pushing_Daisies_1x02_-_Dummy.pdf"),
    ("1", "3", "The Fun In Funeral",           "Pushing_Daisies_1x03_-_The_Fun_In_Funeral.pdf"),
    ("1", "4", "Pigeon",                       "Pushing_Daisies_1x04_-_Pigeon.pdf"),
    ("1", "5", "Girth",                        "Pushing_Daisies_1x05_-_Girth.pdf"),
    ("1", "6", "Bitches",                      "Pushing_Daisies_1x06_-_Bitches.pdf"),
    ("1", "7", "Smell Of Success",             "Pushing_Daisies_1x07_-_Smell_Of_Success.pdf"),
    ("1", "8", "Bitter Sweets",                "Pushing_Daisies_1x08_-_Bitter_Sweets.pdf"),
    ("1", "9", "Corpsicle",                    "Pushing_Daisies_1x09_-_Corpsicle.pdf"),
    ("2", "1", "Bzzzzzzzzz",                   "Pushing_Daisies_2x01_-_Bzzzzzzzzz.pdf"),
    ("2", "2", "Circus Circus",                "Pushing_Daisies_2x01_-_Circus_Circus.pdf"),
    ("2", "3", "Bad Habits",                   "Pushing_Daisies_2x03_-_Bad_Habits.pdf"),
    ("2", "4", "Frescorts",                    "Pushing_Daisies_2x04_-_Frescorts.pdf"),
    ("2", "5", "Dim Sum Lose Some",            "Pushing_Daisies_2x05_-_Dim_Sum_Lose_Some.pdf"),
    ("2", "6", "Oh Oh Oh Its Magic",           "Pushing_Daisies_2x06_-_Oh_Oh_Oh_Its_Magic.pdf"),
    ("2", "7", "Robbing Hood",                 "Pushing_Daisies_2x07_-_Robbing_Hood.pdf"),
    ("2", "8", "Comfort Food",                 "Pushing_Daisies_2x08_-_Comfort_Food.pdf"),
    ("2", "9", "The Legend Of Merle Mcquoddy", "Pushing_Daisies_2x09_-_The_Legend_Of_Merle_Mcquoddy.pdf"),
    ("2","10", "The Norwegians",               "Pushing_Daisies_2x10_-_The_Norwegians.pdf"),
    ("2","11", "Window Dressed To Kill",       "Pushing_Daisies_2x11_-_Window_Dressed_To_Kill.pdf"),
    ("2","12", "Water Power",                  "Pushing_Daisies_2x12_-_Water_Power.pdf"),
    ("2","13", "Kerplunk",                     "Pushing_Daisies_2x13_-_Kerplunk.pdf"),
]

_SCENE_RE = re.compile(r"^\s*(INT\.|EXT\.|INT/EXT\.|EXT/INT\.)", re.IGNORECASE)
_CHAR_RE  = re.compile(r"^[A-Z][A-Z\s'\-\.]{1,30}$")
_CONT_RE  = re.compile(r"\(CONT'D\)", re.IGNORECASE)


def _is_character_name(text: str) -> bool:
    clean = _CONT_RE.sub("", text).strip()
    if not clean:
        return False
    if _CHAR_RE.match(clean) and len(clean) <= 35:
        if not _SCENE_RE.match(clean):
            return True
    return False


def parse_script(pdf_path: str, season: str, episode: str, title: str) -> dict:
    scenes = []
    current_scene = {"heading": "OPENING", "lines": []}
    last_char = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue
            page_width = page.width
            lines_by_y = {}
            for w in words:
                y = round(w["top"], 0)
                lines_by_y.setdefault(y, []).append(w)

            for y in sorted(lines_by_y):
                ws = sorted(lines_by_y[y], key=lambda w: w["x0"])
                text = " ".join(w["text"] for w in ws).strip()
                if not text:
                    continue

                x0 = ws[0]["x0"]
                line_width = ws[-1]["x1"] - x0

                if _SCENE_RE.match(text):
                    scenes.append(current_scene)
                    current_scene = {"heading": text, "lines": []}
                    last_char = None
                elif _is_character_name(text) and x0 > page_width * 0.3 and line_width < page_width * 0.5:
                    last_char = _CONT_RE.sub("", text).strip()
                    current_scene["lines"].append({"type": "character", "name": last_char})
                elif last_char and x0 > page_width * 0.2:
                    current_scene["lines"].append({"type": "dialogue", "character": last_char, "text": text})
                else:
                    current_scene["lines"].append({"type": "action", "text": text})
                    last_char = None

    scenes.append(current_scene)
    return {
        "season": season,
        "episode": episode,
        "title": title,
        "episode_id": f"S{season.zfill(2)}E{episode.zfill(2)}",
        "scenes": [s for s in scenes if s["lines"]],
    }


def extract_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    for season, episode, title, filename in SCRIPTS:
        pdf_path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(pdf_path):
            print(f"[skip] {filename} not found — run download.py first")
            continue
        print(f"[parse] S{season}E{episode} — {title}")
        data = parse_script(pdf_path, season, episode, title)
        out_path = os.path.join(OUT_DIR, f"S{season.zfill(2)}E{episode.zfill(2)}.json")
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        results.append(data)
        print(f"        {len(data['scenes'])} scenes extracted")
    return results


if __name__ == "__main__":
    extract_all()
