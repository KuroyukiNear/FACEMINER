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
# Download image
# ============================================================

def download_image():
    response = requests.get(
        IMAGE_URL,
        timeout=30,
    )

    response.raise_for_status()

    image_data = response.content

    # Verify that the downloaded data is a valid image.
    try:
        image = Image.open(io.BytesIO(image_data))
        image.verify()
    except Exception:
        raise RuntimeError(
            "The downloaded data is not a valid image."
        )

    return image_data


# ============================================================
# Save image
# ============================================================

def save_image(image_data):
    sha256 = hashlib.sha256(image_data).hexdigest()

    image_path = IMAGE_DIR / f"{sha256}.jpg"

    if image_path.exists():
        return image_path, sha256, True

    with open(image_path, "wb") as file:
        file.write(image_data)

    return image_path, sha256, False


# ============================================================
# Get a unique image
# ============================================================

def get_new_image():
    while True:
        image_data = download_image()

        image_path, sha256, duplicate = save_image(
            image_data
        )

        if not duplicate:
            return image_path, sha256

        print("Duplicate image received. Trying again...")

        time.sleep(1)


# ============================================================
# Create Obsidian note
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

    with open(
        note_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(content)

    return note_path


# ============================================================
# Save JSON
# ============================================================

def save_json(image_path, sha256, labels):

    if JSON_FILE.exists():
        try:
            with open(
                JSON_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                dataset = json.load(file)
        except json.JSONDecodeError:
            dataset = []
    else:
        dataset = []

    # Prevent duplicate records.
    for entry in dataset:
        if entry.get("sha256") == sha256:
            return

    record = {
        "sha256": sha256,
        "image": str(image_path),
        **labels,
    }

    dataset.append(record)

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            dataset,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# Main application
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


    # ========================================================
    # Build GUI
    # ========================================================

    def build_interface(self):

        # ----------------------------------------------------
        # Main layout
        # ----------------------------------------------------

        main = tk.Frame(self.root)
        main.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        # Image side
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

        # ----------------------------------------------------
        # Controls side
        # ----------------------------------------------------

        controls_outer = tk.Frame(main)

        controls_outer.pack(
            side="right",
            fill="y",
        )

        # Use a canvas + scrollbar because the ethnicity list
        # can make the controls quite tall.
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

        canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        canvas.pack(
            side="left",
            fill="y",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = tk.Label(
            controls,
            text="FACEMINER",
            font=("Segoe UI", 18, "bold"),
        )

        title.pack(
            pady=(0, 10),
        )

        self.image_info = tk.Label(
            controls,
            text="",
            font=("Segoe UI", 9),
            wraplength=350,
            justify="left",
        )

        self.image_info.pack(
            anchor="w",
            pady=(0, 15),
        )

        # ----------------------------------------------------
        # Label groups
        # ----------------------------------------------------

        self.create_label_group(
            controls,
            "Age group",
            "age_group",
        )

        self.create_label_group(
            controls,
            "Hair colour",
            "hair_colour",
        )

        self.create_label_group(
            controls,
            "Eye colour",
            "eye_colour",
        )

        self.create_label_group(
            controls,
            "Gender",
            "gender",
        )

        self.create_label_group(
            controls,
            "Perceived ethnicity",
            "perceived_ethnicity",
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_frame = tk.Frame(controls)

        button_frame.pack(
            fill="x",
            pady=(20, 10),
        )

        self.save_button = tk.Button(
            button_frame,
            text="Save & Next",
            command=self.save_and_next,
            font=("Segoe UI", 11, "bold"),
            height=2,
        )

        self.save_button.pack(
            fill="x",
            pady=3,
        )

        self.skip_button = tk.Button(
            button_frame,
            text="Skip",
            command=self.skip_image,
            height=2,
        )

        self.skip_button.pack(
            fill="x",
            pady=3,
        )

        self.quit_button = tk.Button(
            button_frame,
            text="Quit",
            command=self.quit,
            height=2,
        )

        self.quit_button.pack(
            fill="x",
            pady=3,
        )


    # ========================================================
    # Create a group of radio buttons
    # ========================================================

    def create_label_group(
        self,
        parent,
        title,
        key,
    ):

        frame = tk.LabelFrame(
            parent,
            text=title,
            padx=8,
            pady=5,
        )

        frame.pack(
            fill="x",
            pady=5,
        )

        variable = tk.StringVar(
            value=""
        )

        self.label_vars[key] = variable

        for option in LABEL_OPTIONS[key]:

            radio = tk.Radiobutton(
                frame,
                text=option.replace("_", " ").title(),
                value=option,
                variable=variable,
                anchor="w",
            )

            radio.pack(
                anchor="w",
            )


    # ========================================================
    # Load next image
    # ========================================================

    def load_next_image(self):

        self.clear_labels()

        self.image_label.config(
            image="",
            text="Downloading image...",
        )

        self.image_info.config(
            text="Downloading..."
        )

        self.root.update_idletasks()

        try:
            image_path, sha256 = get_new_image()

        except Exception as error:
            messagebox.showerror(
                "Download Error",
                str(error),
            )

            self.image_label.config(
                text="Download failed."
            )

            return

        self.current_image_path = image_path
        self.current_sha256 = sha256

        self.image_number += 1

        # ----------------------------------------------------
        # Load image
        # ----------------------------------------------------

        try:
            image = Image.open(image_path)

            image.thumbnail(
                (
                    MAX_IMAGE_WIDTH,
                    MAX_IMAGE_HEIGHT,
                ),
                Image.Resampling.LANCZOS,
            )

            self.current_photo = ImageTk.PhotoImage(
                image
            )

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

        # ----------------------------------------------------
        # Display information
        # ----------------------------------------------------

        self.image_info.config(
            text=(
                f"Image #{self.image_number}\n\n"
                f"SHA-256:\n"
                f"{sha256}"
            )
        )


    # ========================================================
    # Clear current selections
    # ========================================================

    def clear_labels(self):

        for variable in self.label_vars.values():
            variable.set("")


    # ========================================================
    # Get labels
    # ========================================================

    def get_labels(self):

        labels = {}

        for key, variable in self.label_vars.items():

            value = variable.get()

            if not value:
                return None

            labels[key] = value

        return labels


    # ========================================================
    # Save current image
    # ========================================================

    def save_and_next(self):

        labels = self.get_labels()

        if labels is None:

            messagebox.showwarning(
                "Missing labels",
                "Please select an option for every category.",
            )

            return

        # ----------------------------------------------------
        # Save Obsidian note
        # ----------------------------------------------------

        try:

            note_path = create_note(
                self.current_image_path,
                self.current_sha256,
                labels,
            )

            # ------------------------------------------------
            # Save JSON
            # ------------------------------------------------

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

        # ----------------------------------------------------
        # Load next image
        # ----------------------------------------------------

        self.load_next_image()


    # ========================================================
    # Skip current image
    # ========================================================

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


    # ========================================================
    # Quit
    # ========================================================

    def quit(self):
        answer = messagebox.askyesnocancel(
            "Quit",
            "What should happen to the current image?\n\n"
            "Yes = Delete current image and quit\n"
            "No = Keep current image and quit\n"
            "Cancel = Continue labeling"
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
# Start program
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = FACEMINER(root)

    root.mainloop()