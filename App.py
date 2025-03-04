from __future__ import annotations
import customtkinter as ctk
from ImageViewer import ImageViewer

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ImageViewer()
    app.mainloop()
