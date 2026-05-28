"""Download all Pushing Daisies PDF scripts."""
import os
import requests
from tqdm import tqdm

BASE_URL = "https://tvwriting.co.uk/tv_scripts/Collections/Drama/Pushing_Daisies/"

SCRIPTS = [
    ("1x01", "Pie-Lette",                    "Pushing_Daisies_1x01_-_Pie-Lette.pdf"),
    ("1x02", "Dummy",                         "Pushing_Daisies_1x02_-_Dummy.pdf"),
    ("1x03", "The Fun In Funeral",            "Pushing_Daisies_1x03_-_The_Fun_In_Funeral.pdf"),
    ("1x04", "Pigeon",                        "Pushing_Daisies_1x04_-_Pigeon.pdf"),
    ("1x05", "Girth",                         "Pushing_Daisies_1x05_-_Girth.pdf"),
    ("1x06", "Bitches",                       "Pushing_Daisies_1x06_-_Bitches.pdf"),
    ("1x07", "Smell Of Success",              "Pushing_Daisies_1x07_-_Smell_Of_Success.pdf"),
    ("1x08", "Bitter Sweets",                 "Pushing_Daisies_1x08_-_Bitter_Sweets.pdf"),
    ("1x09", "Corpsicle",                     "Pushing_Daisies_1x09_-_Corpsicle.pdf"),
    ("2x01", "Bzzzzzzzzz",                    "Pushing_Daisies_2x01_-_Bzzzzzzzzz.pdf"),
    ("2x02", "Circus Circus",                 "Pushing_Daisies_2x01_-_Circus_Circus.pdf"),
    ("2x03", "Bad Habits",                    "Pushing_Daisies_2x03_-_Bad_Habits.pdf"),
    ("2x04", "Frescorts",                     "Pushing_Daisies_2x04_-_Frescorts.pdf"),
    ("2x05", "Dim Sum Lose Some",             "Pushing_Daisies_2x05_-_Dim_Sum_Lose_Some.pdf"),
    ("2x06", "Oh Oh Oh Its Magic",            "Pushing_Daisies_2x06_-_Oh_Oh_Oh_Its_Magic.pdf"),
    ("2x07", "Robbing Hood",                  "Pushing_Daisies_2x07_-_Robbing_Hood.pdf"),
    ("2x08", "Comfort Food",                  "Pushing_Daisies_2x08_-_Comfort_Food.pdf"),
    ("2x09", "The Legend Of Merle Mcquoddy",  "Pushing_Daisies_2x09_-_The_Legend_Of_Merle_Mcquoddy.pdf"),
    ("2x10", "The Norwegians",                "Pushing_Daisies_2x10_-_The_Norwegians.pdf"),
    ("2x11", "Window Dressed To Kill",        "Pushing_Daisies_2x11_-_Window_Dressed_To_Kill.pdf"),
    ("2x12", "Water Power",                   "Pushing_Daisies_2x12_-_Water_Power.pdf"),
    ("2x13", "Kerplunk",                      "Pushing_Daisies_2x13_-_Kerplunk.pdf"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs")


def download_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer":    "https://sites.google.com/site/tvwriting/us-drama/us-drama-collections/pushing-daisies",
        "Accept":     "application/pdf,*/*",
    }

    for ep_id, title, filename in tqdm(SCRIPTS, desc="Downloading PDFs"):
        dest = os.path.join(OUT_DIR, filename)
        if os.path.exists(dest):
            print(f"  [skip] {ep_id} already exists")
            continue
        url = BASE_URL + filename
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"  [ok]   {ep_id} — {title}")
        except Exception as e:
            print(f"  [fail] {ep_id} — {e}")


if __name__ == "__main__":
    download_all()
