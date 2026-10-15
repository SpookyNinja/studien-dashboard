"""Startdatei des Studien-Dashboards.

Aufruf:  python main.py                (nutzt daten/studium.txt)
         python main.py meine_daten.txt

Gibt es daten/studium.txt noch nicht, wird sie beim ersten Start aus den
Beispieldaten (daten/beispiel_studium.txt) angelegt.
"""

import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from controller import DashboardController
from speicher import TextDateiSpeicher
from view import DashboardApp

ORDNER = Path(__file__).resolve().parent
STANDARD_DATEI = ORDNER / "daten" / "studium.txt"
BEISPIEL_DATEI = ORDNER / "daten" / "beispiel_studium.txt"


def datendatei_ermitteln() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    if not STANDARD_DATEI.exists():
        shutil.copy(BEISPIEL_DATEI, STANDARD_DATEI)
    return STANDARD_DATEI


def main():
    # Unter Windows sonst unscharf auf Bildschirmen mit Skalierung > 100 %
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass

    try:
        controller = DashboardController(TextDateiSpeicher(datendatei_ermitteln()))
    except (OSError, ValueError) as fehler:
        # Fenster nur für die Fehlermeldung, damit man den Fehler auch sieht,
        # wenn das Programm per Doppelklick gestartet wurde
        wurzel = tk.Tk()
        wurzel.withdraw()
        messagebox.showerror("Studien-Dashboard",
                             f"Daten konnten nicht geladen werden:\n{fehler}")
        wurzel.destroy()
        sys.exit(1)

    DashboardApp(controller).mainloop()


if __name__ == "__main__":
    main()
