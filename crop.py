import hashlib
import io
import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import requests
from PIL import Image, ImageTk


# ============================================================
# Configuration
# ============================================================

IMAGE_URL = "https://thispersondoesnotexist.com/random-person.jpeg"

IMAGE_DIR = Path("images")
NOTE_DIR = Path("notes")
JSON_FILE = Path("dataset.json")

MAX_IMAGE_WIDTH = 650
MAX_IMAGE_HEIGHT = 750

# Number of pixels cropped from the bottom of each image.
CROP_BOTTOM_PIXELS = 19

IMAGE_DIR.mkdir(exist_ok=True)
NOTE_DIR.mkdir(exist_ok=True)


# ============================================================
# Label options
# ============================================================

LABEL_OPTIONS = {
    "age_group": [
        "child",
        "young_adult",
        "adult",
        "middle_aged",
        "elderly",
        "unknown",
    ],
    "hair_colour": [
        "black",
        "brown",
        "blonde",
        "red",
        "gray",
        "white",
        "other",
        "unknown",
    ],
    "eye_colour": [
        "brown",
        "hazel",
        "green",
        "blue",
        "gray",
        "amber",
        "other",
        "unknown",
    ],
    "gender": [
        "male",
        "female",
        "unknown",
    ],
    "perceived_ethnicity": [
        "east_asian",
        "southeast_asian",
        "south_asian",
        "central_asian",
        "west_asian",
        "north_african",
        "sub_saharan_african",
        "european",
        "indigenous_american",
        "indigenous_oceanian",
        "mixed_or_multiracial",
        "other",
        "unknown",
    ],
}


# ============================================================
# Download
# ============================================================

def download_image():
    response = requests.get(IMAGE_URL, timeout=30)
    response.raise_for_status()

    image_data = response.content

    try:
        image = Image.open(io.BytesIO(image_data))
        image.verify()
    except Exception:
        raise RuntimeError("The downloaded data is not a valid image.")

    return image_data


# ============================================================
# Crop bottom watermark
# ============================================================

def crop_watermark(image_data):
    try:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        width, height = image.size

        if CROP_BOTTOM_PIXELS <= 0:
            return image_data

        if CROP_BOTTOM_PIXELS >= height:
            raise ValueError(
                "CROP_BOTTOM_PIXELS is larger than the image height."
            )

        cropped = image.crop(
            (0, 0, width, height - CROP_BOTTOM_PIXELS)
        )

        output = io.BytesIO()
        cropped.save(output, format="JPEG", quality=95)

        return output.getvalue()

    except Exception as error:
        raise RuntimeError(f"Could not crop image: {error}")


# ============================================================
# Save image
# ============================================================

def save_image(image_data):
    sha256 = hashlib.sha256(image_data).hexdigest()
    image_path = IMAGE_DIR / f"{sha256}.jpg"

    if image_path.exists():
        return image_path, sha256, True

    image_path.write_bytes(image_data)
    return image_path, sha256, False


def get_new_image():
    while True:
        image_data = download_image()
        image_data = crop_watermark(image_data)

        image_path, sha256, duplicate = save_image(image_data)

        if not duplicate:
            return image_path, sha256

        time.sleep(1)


# ============================================================
# Obsidian note
# ============================================================

def create_note(image_path, sha256, labels):
    note_path = NOTE_DIR / f"{sha256}.md"

    content = f"""---
sha256: {sha256}
age_group: {labels["age_group"]}
hair_colour: {labels["hair_colour"]}
eye_colour: {labels["eye_colour"]}
gender: {labels["gender"]}
perceived_ethnicity: {labels["perceived_ethnicity"]}
cover: [[images/{image_path.name}]]
---

```
age_group: {labels["age_group"]}
hair_colour: {labels["hair_colour"]}
eye_colour: {labels["eye_colour"]}
gender: {labels["gender"]}
perceived_ethnicity: {labels["perceived_ethnicity"]}
```

![[images/{image_path.name}]]
"""

    note_path.write_text(content, encoding="utf-8")
    return note_path


# ============================================================
# JSON
# ============================================================

def save_json(image_path, sha256, labels):
    if JSON_FILE.exists():
        try:
            dataset = json.loads(JSON_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dataset = []
    else:
        dataset = []

    for entry in dataset:
        if entry.get("sha256") == sha256:
            return

    dataset.append({
        "sha256": sha256,
        "image": str(image_path),
        **labels,
    })

    JSON_FILE.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================
# GUI
# ============================================================

class FACEMINER:
    def __init__(self, root):
        self.root = root
        self.root.title("FACEMINER")
        self.root.geometry("1200x850")
        self.root.minsize(900, 700)

        self.current_image_path = None
        self.current_sha256 = None
        self.current_photo = None
        self.image_number = 0
        self.label_vars = {}

        self.build_interface()
        self.load_next_image()

    def build_interface(self):
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        image_frame = tk.Frame(
            main,
            relief="sunken",
            borderwidth=1,
        )
        image_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10),
        )

        self.image_label = tk.Label(
            image_frame,
            text="Loading image...",
            anchor="center",
        )
        self.image_label.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        controls_outer = tk.Frame(main)
        controls_outer.pack(side="right", fill="y")

        canvas = tk.Canvas(
            controls_outer,
            width=380,
            highlightthickness=0,
        )

        scrollbar = tk.Scrollbar(
            controls_outer,
            orient="vertical",
            command=canvas.yview,
        )

        controls = tk.Frame(canvas)

        controls.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        canvas.create_window(
            (0, 0),
            window=controls,
            anchor="nw",
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="y", expand=True)
        scrollbar.pack(side="right", fill="y")

        title = tk.Label(
            controls,
            text="FACEMINER",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(pady=(0, 10))

        self.image_info = tk.Label(
            controls,
            text="",
            font=("Segoe UI", 9),
            wraplength=350,
            justify="left",
        )
        self.image_info.pack(anchor="w", pady=(0, 15))

        self.create_label_group(
            controls, "Age group", "age_group"
        )
        self.create_label_group(
            controls, "Hair colour", "hair_colour"
        )
        self.create_label_group(
            controls, "Eye colour", "eye_colour"
        )
        self.create_label_group(
            controls, "Gender", "gender"
        )
        self.create_label_group(
            controls, "Perceived ethnicity", "perceived_ethnicity"
        )

        button_frame = tk.Frame(controls)
        button_frame.pack(fill="x", pady=(20, 10))

        tk.Button(
            button_frame,
            text="Save & Next",
            command=self.save_and_next,
            font=("Segoe UI", 11, "bold"),
            height=2,
        ).pack(fill="x", pady=3)

        tk.Button(
            button_frame,
            text="Skip",
            command=self.skip_image,
            height=2,
        ).pack(fill="x", pady=3)

        tk.Button(
            button_frame,
            text="Quit",
            command=self.quit,
            height=2,
        ).pack(fill="x", pady=3)

    def create_label_group(self, parent, title, key):
        frame = tk.LabelFrame(
            parent,
            text=title,
            padx=8,
            pady=5,
        )
        frame.pack(fill="x", pady=5)

        variable = tk.StringVar(value="")
        self.label_vars[key] = variable

        for option in LABEL_OPTIONS[key]:
            tk.Radiobutton(
                frame,
                text=option.replace("_", " ").title(),
                value=option,
                variable=variable,
                anchor="w",
            ).pack(anchor="w")

    def clear_labels(self):
        for variable in self.label_vars.values():
            variable.set("")

    def load_next_image(self):
        self.clear_labels()

        self.image_label.config(
            image="",
            text="Downloading image...",
        )
        self.image_info.config(text="Downloading...")
        self.root.update_idletasks()

        try:
            image_path, sha256 = get_new_image()
        except Exception as error:
            messagebox.showerror(
                "Download Error",
                str(error),
            )
            self.image_label.config(text="Download failed.")
            return

        self.current_image_path = image_path
        self.current_sha256 = sha256
        self.image_number += 1

        try:
            image = Image.open(image_path)
            image.thumbnail(
                (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT),
                Image.Resampling.LANCZOS,
            )

            self.current_photo = ImageTk.PhotoImage(image)

            self.image_label.config(
                image=self.current_photo,
                text="",
            )

        except Exception as error:
            messagebox.showerror(
                "Image Error",
                str(error),
            )
            return

        self.image_info.config(
            text=(
                f"Image #{self.image_number}\n\n"
                f"SHA-256:\n{sha256}"
            )
        )

    def get_labels(self):
        labels = {}

        for key, variable in self.label_vars.items():
            value = variable.get()

            if not value:
                return None

            labels[key] = value

        return labels

    def save_and_next(self):
        labels = self.get_labels()

        if labels is None:
            messagebox.showwarning(
                "Missing labels",
                "Please select an option for every category.",
            )
            return

        try:
            create_note(
                self.current_image_path,
                self.current_sha256,
                labels,
            )

            save_json(
                self.current_image_path,
                self.current_sha256,
                labels,
            )

        except Exception as error:
            messagebox.showerror(
                "Save Error",
                str(error),
            )
            return

        self.load_next_image()

    def skip_image(self):
        if self.current_image_path is None:
            return

        answer = messagebox.askyesno(
            "Skip image",
            "Skip this image?\n\n"
            "The downloaded image will be deleted.",
        )

        if not answer:
            return

        try:
            if self.current_image_path.exists():
                self.current_image_path.unlink()
        except Exception as error:
            messagebox.showerror(
                "Error",
                str(error),
            )
            return

        self.load_next_image()

    def quit(self):
        answer = messagebox.askyesnocancel(
            "Quit",
            "What should happen to the current image?\n\n"
            "Yes = Delete current image and quit\n"
            "No = Keep current image and quit\n"
            "Cancel = Continue labeling",
        )

        if answer is None:
            return

        if answer:
            try:
                if (
                    self.current_image_path
                    and self.current_image_path.exists()
                ):
                    self.current_image_path.unlink()
            except Exception as error:
                messagebox.showerror(
                    "Error",
                    f"Could not delete the image:\n\n{error}",
                )
                return

        self.root.destroy()


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = FACEMINER(root)
    root.mainloop()
