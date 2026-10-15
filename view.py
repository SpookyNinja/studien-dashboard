"""Präsentation: die grafische Oberfläche des Dashboards (Tkinter + Matplotlib).

Aufbau wie in der Skizze aus Phase 1:
    oben     Titel, "Semester abschließen" und "Save"
    Mitte    Piechart (StatusDiagramm), Notendurchschnitt und ECTS / Zeitplan
    unten    bis zu drei Modulkarten und die Karte zum Hinzufügen eines Moduls

Die Oberfläche rechnet selbst nichts aus. Sie gibt alle Aktionen an den
DashboardController weiter und zeigt danach dessen Kennzahlen an.
"""

from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod
from collections.abc import Callable
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from controller import DashboardController
from model import Modul, ModulStatus

# Farben aus der Dashboard-Skizze
HINTERGRUND = "#ffffff"
FELD = "#f2f2f2"
RAHMEN = "#14273e"
KARTE = "#d9f2d0"
KARTE_PLUS = "#f3f9f1"
GRUEN = "#2e7d32"
ORANGE = "#d97706"
ROT = "#c62828"
BUTTON_BLAU = "#1f5f99"
SAVE_LILA = "#e3a0dc"
PIE_FARBEN = {
    ModulStatus.ABGESCHLOSSEN: "#7fbf7f",
    ModulStatus.IN_BEARBEITUNG: "#f5c26b",
    ModulStatus.OFFEN: "#c0e3f5",
}

# Segoe UI ist die Standardschrift unter Windows. Auf anderen Systemen wird
# in DashboardApp eine vorhandene Ersatzschrift gewählt.
SCHRIFT = "Segoe UI"
ERSATZSCHRIFTEN = ["Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial", "Helvetica"]
PRUEFUNGSARTEN = ["Klausur", "Portfolio", "Hausarbeit", "Fallstudie",
                  "Projektbericht", "Workbook", "Advanced Workbook"]


def note_als_text(note: float) -> str:
    """1.8 -> '1,8' (deutsche Schreibweise)."""
    return f"{note:.1f}".replace(".", ",")


class StatusDiagramm(tk.Frame):
    """Piechart mit der Anzahl offener, laufender und abgeschlossener Module."""

    def __init__(self, master):
        super().__init__(master, bg=HINTERGRUND)
        tk.Label(self, text="Modulstatus", bg=HINTERGRUND,
                 font=(SCHRIFT, 13)).pack()
        self._figur = Figure(figsize=(4.4, 2.6), dpi=90)
        self._figur.patch.set_facecolor(HINTERGRUND)
        self._achse = self._figur.add_subplot()
        self._canvas = FigureCanvasTkAgg(self._figur, master=self)
        self._canvas.get_tk_widget().pack()

    def aktualisieren(self, werte: dict):
        anzahl = werte["anzahl_status"]
        reihenfolge = [ModulStatus.ABGESCHLOSSEN, ModulStatus.IN_BEARBEITUNG,
                       ModulStatus.OFFEN]
        zahlen = [anzahl[s] for s in reihenfolge]

        self._achse.clear()
        if sum(zahlen) == 0:
            self._achse.text(0.5, 0.5, "keine Module", ha="center")
            self._achse.axis("off")
        else:
            stuecke, _ = self._achse.pie(
                zahlen, colors=[PIE_FARBEN[s] for s in reihenfolge],
                startangle=90, counterclock=False,
                wedgeprops={"edgecolor": RAHMEN, "linewidth": 1})
            self._achse.legend(
                stuecke, [f"{z} {s.value}" for z, s in zip(zahlen, reihenfolge)],
                loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
                fontsize=11)
            self._achse.set_aspect("equal")
        self._figur.subplots_adjust(left=0.02, right=0.55, top=0.98, bottom=0.02)
        self._canvas.draw()


class KennzahlFeld(tk.Frame, ABC):
    """Abstrakte Oberklasse für die beiden Felder, die die Ziele anzeigen.

    Jedes Feld hat einen Titel, einen großen Wert, eine Zeile mit dem
    Zielwert und eine farbige Bewertung. Was genau angezeigt wird, legen die
    Unterklassen in aktualisieren() fest.
    """

    def __init__(self, master, titel: str):
        super().__init__(master, bg=FELD, highlightbackground=RAHMEN,
                         highlightthickness=2, width=250, height=190)
        self.pack_propagate(False)  # feste Größe, damit beide Felder gleich sind
        self._titel = titel
        tk.Label(self, text=titel, bg=FELD, font=(SCHRIFT, 13)).pack(pady=(10, 4))
        self._wert_label = tk.Label(self, bg=FELD, font=(SCHRIFT, 26))
        self._wert_label.pack()
        self._extra = tk.Frame(self, bg=FELD)  # Platz für Zusatzelemente
        self._extra.pack()
        self._ziel_label = tk.Label(self, bg=FELD, font=(SCHRIFT, 10))
        self._ziel_label.pack(pady=(2, 2))
        self._bewertung_label = tk.Label(self, bg=FELD, font=(SCHRIFT, 11, "bold"))
        self._bewertung_label.pack()

    @abstractmethod
    def aktualisieren(self, werte: dict):
        ...


class NotenFeld(KennzahlFeld):
    """Ziel 1: Notendurchschnitt von 2,0 oder besser."""

    def __init__(self, master):
        super().__init__(master, "Notendurchschnitt")

    def aktualisieren(self, werte: dict):
        schnitt = werte["notendurchschnitt"]
        ziel = werte["ziel_note"]
        self._ziel_label.config(text=f"Ziel: {note_als_text(ziel)} oder besser")
        if schnitt is None:
            self._wert_label.config(text="–", fg=RAHMEN)
            self._bewertung_label.config(text="noch keine Note", fg=RAHMEN)
        elif schnitt <= ziel:
            self._wert_label.config(text=note_als_text(schnitt), fg=GRUEN)
            self._bewertung_label.config(text="im Ziel", fg=GRUEN)
        else:
            self._wert_label.config(text=note_als_text(schnitt), fg=ROT)
            self._bewertung_label.config(text="nicht im Ziel", fg=ROT)


class EctsFeld(KennzahlFeld):
    """Ziel 2: Abschluss in Regelstudienzeit, gemessen über Ist- und Soll-ECTS."""

    BALKEN_BREITE = 200
    BALKEN_HOEHE = 18

    def __init__(self, master):
        super().__init__(master, "ECTS / Zeitplan")
        self._balken = tk.Canvas(self._extra, width=self.BALKEN_BREITE + 2,
                                 height=self.BALKEN_HOEHE + 2, bg=FELD,
                                 highlightthickness=0)
        self._balken.pack(pady=(2, 2))
        self._wert_label.config(font=(SCHRIFT, 20))

    def aktualisieren(self, werte: dict):
        ist, soll = werte["erreichte_ects"], werte["soll_ects"]
        gesamt = werte["gesamt_ects"]
        self._wert_label.config(text=f"{ist} / {gesamt} ECTS", fg=RAHMEN)
        self._ziel_label.config(
            text=f"Semester {werte['aktuelles_semester']} von "
                 f"{werte['regelstudienzeit']} · Soll: {soll} ECTS")
        self._balken_zeichnen(ist, soll, gesamt)

        differenz = ist - soll
        if differenz < 0:
            self._bewertung_label.config(text=f"{-differenz} ECTS hinter Plan",
                                         fg=ORANGE)
        elif differenz > 0:
            self._bewertung_label.config(text=f"{differenz} ECTS vor Plan",
                                         fg=GRUEN)
        else:
            self._bewertung_label.config(text="im Plan", fg=GRUEN)

    def _balken_zeichnen(self, ist: int, soll: int, gesamt: int):
        b, h = self.BALKEN_BREITE, self.BALKEN_HOEHE
        self._balken.delete("all")
        self._balken.create_rectangle(1, 1, b, h, fill="white", outline=RAHMEN)
        if ist > 0:
            self._balken.create_rectangle(1, 1, 1 + b * min(ist / gesamt, 1), h,
                                          fill=PIE_FARBEN[ModulStatus.ABGESCHLOSSEN],
                                          outline=RAHMEN)
        # senkrechte Linie = Soll-Wert laut Zeitplan
        x = 1 + b * min(soll / gesamt, 1)
        self._balken.create_line(x, 0, x, h + 2, fill=RAHMEN, width=2)


class ModulKarte(tk.Frame):
    """Karte für ein Modul in Bearbeitung mit Noteneingabe und beenden-Button."""

    def __init__(self, master, modul: Modul,
                 on_beenden: Callable[[Modul, str, str], None]):
        super().__init__(master, bg=KARTE, highlightbackground=RAHMEN,
                         highlightthickness=2, width=250, height=215)
        self.pack_propagate(False)
        self._modul = modul
        self._on_beenden = on_beenden

        tk.Label(self, text=modul.name, bg=KARTE, font=(SCHRIFT, 11, "bold"),
                 wraplength=225, justify="center").pack(pady=(10, 0))
        tk.Label(self, text=f"{modul.ects} ECTS", bg=KARTE, fg="#555555",
                 font=(SCHRIFT, 10)).pack()

        zeile = tk.Frame(self, bg=KARTE)
        zeile.pack(pady=(8, 0))
        self._art_auswahl = ttk.Combobox(zeile, values=PRUEFUNGSARTEN,
                                         width=13, state="readonly")
        self._art_auswahl.set(PRUEFUNGSARTEN[0])
        self._art_auswahl.pack(side="left", padx=(0, 6))
        tk.Label(zeile, text="Note:", bg=KARTE, font=(SCHRIFT, 10)).pack(side="left")
        self._noten_eingabe = tk.Entry(zeile, width=5, justify="center")
        self._noten_eingabe.pack(side="left")
        self._noten_eingabe.bind("<Return>", lambda _e: self._beenden())

        tk.Button(self, text="beenden", bg=BUTTON_BLAU, fg="white",
                  activebackground=RAHMEN, activeforeground="white",
                  font=(SCHRIFT, 10), width=10,
                  command=self._beenden).pack(side="bottom", pady=12)

    def _beenden(self):
        self._on_beenden(self._modul, self._art_auswahl.get(),
                         self._noten_eingabe.get())


class DashboardApp(tk.Tk):
    """Hauptfenster. Besteht aus Piechart, zwei Kennzahlfeldern und Modulkarten."""

    def __init__(self, controller: DashboardController):
        super().__init__()
        self._schrift_waehlen()
        self._controller = controller
        self.title("Studien-Dashboard")
        self.configure(bg=HINTERGRUND, padx=20, pady=15)
        self.resizable(False, False)

        self._kopf_bauen()

        mitte = tk.Frame(self, bg=HINTERGRUND)
        mitte.pack(fill="x", pady=(10, 0))
        self._diagramm = StatusDiagramm(mitte)
        self._diagramm.pack(side="left", padx=(0, 20))
        # Beide Felder werden als KennzahlFeld behandelt (Polymorphie)
        self._felder: list[KennzahlFeld] = [NotenFeld(mitte), EctsFeld(mitte)]
        for feld in self._felder:
            feld.pack(side="left", padx=8, anchor="n", pady=(25, 0))

        tk.Label(self, text=f"Module in Bearbeitung (max. "
                            f"{DashboardController.MAX_IN_BEARBEITUNG})",
                 bg=HINTERGRUND, font=(SCHRIFT, 13)).pack(anchor="w", pady=(10, 6))
        self._karten_bereich = tk.Frame(self, bg=HINTERGRUND)
        self._karten_bereich.pack(fill="x")

        self.protocol("WM_DELETE_WINDOW", self._on_schliessen)
        self.aktualisieren()

    def _schrift_waehlen(self):
        global SCHRIFT
        vorhanden = {f.lower() for f in tkfont.families(self)}
        SCHRIFT = next((f for f in ERSATZSCHRIFTEN if f.lower() in vorhanden),
                       "Helvetica")

    def _kopf_bauen(self):
        kopf = tk.Frame(self, bg=HINTERGRUND)
        kopf.pack(fill="x")
        tk.Label(kopf, text="Studien-Dashboard", bg=HINTERGRUND, fg=RAHMEN,
                 font=(SCHRIFT, 18)).pack(side="left")
        self._studiengang_label = tk.Label(kopf, bg=HINTERGRUND, fg="#555555",
                                           font=(SCHRIFT, 11))
        self._studiengang_label.pack(side="left", padx=12, pady=(6, 0))
        tk.Button(kopf, text="Save", bg=SAVE_LILA, font=(SCHRIFT, 12), width=8,
                  command=self._on_save).pack(side="right")
        tk.Button(kopf, text="Semester abschließen", font=(SCHRIFT, 10),
                  command=self._on_semester_abschliessen).pack(side="right", padx=10)

    def aktualisieren(self):
        """Holt die aktuellen Kennzahlen und zeichnet alles neu."""
        werte = self._controller.kennzahlen()
        stern = " *" if self._controller.geaendert else ""
        self.title(f"Studien-Dashboard{stern}")
        self._studiengang_label.config(text=werte["studiengang"])
        self._diagramm.aktualisieren(werte)
        for feld in self._felder:
            feld.aktualisieren(werte)
        self._karten_neu_aufbauen()

    def _karten_neu_aufbauen(self):
        for kind in self._karten_bereich.winfo_children():
            kind.destroy()
        laufend = self._controller.module_in_bearbeitung()
        for modul in laufend:
            ModulKarte(self._karten_bereich, modul,
                       self._on_beenden).pack(side="left", padx=(0, 15))
        if len(laufend) < DashboardController.MAX_IN_BEARBEITUNG:
            self._plus_karte_bauen()

    def _plus_karte_bauen(self):
        """Karte mit "+" zum Starten eines offenen Moduls."""
        karte = tk.Frame(self._karten_bereich, bg=KARTE_PLUS, width=250,
                         height=215, highlightbackground=RAHMEN,
                         highlightthickness=2)
        karte.pack_propagate(False)
        karte.pack(side="left")

        offene = self._controller.offene_module()
        if not offene:
            tk.Label(karte, text="Keine offenen Module mehr", bg=KARTE_PLUS,
                     font=(SCHRIFT, 10)).pack(expand=True)
            return
        self._auswahl_module = offene
        self._modul_auswahl = ttk.Combobox(
            karte, state="readonly", width=27,
            values=[f"{m.name} ({m.ects} ECTS)" for m in offene])
        self._modul_auswahl.set("Modul auswählen ...")
        self._modul_auswahl.pack(pady=(18, 4))
        tk.Button(karte, text="+", fg="#7b2d8b", bg=KARTE_PLUS, bd=0,
                  activebackground=KARTE_PLUS, font=(SCHRIFT, 40),
                  relief="flat", highlightthickness=0, cursor="hand2",
                  command=self._on_plus).pack()
        tk.Label(karte, text="Modul hinzufügen", bg=KARTE_PLUS, fg="#555555",
                 font=(SCHRIFT, 11)).pack()

    # ---- Aktionen des Nutzers --------------------------------------------

    def _on_plus(self):
        index = self._modul_auswahl.current()
        if index < 0:
            messagebox.showinfo("Modul hinzufügen",
                                "Bitte zuerst ein Modul aus der Liste auswählen.")
            return
        try:
            self._controller.modul_hinzufuegen(self._auswahl_module[index])
        except ValueError as fehler:
            messagebox.showerror("Modul hinzufügen", str(fehler))
        self.aktualisieren()

    def _on_beenden(self, modul: Modul, art: str, note_text: str):
        try:
            # Komma oder Punkt erlauben, also 1,7 und 1.7
            note = float(note_text.strip().replace(",", "."))
        except ValueError:
            messagebox.showerror("Modul beenden",
                                 "Bitte eine Note eingeben, z. B. 1,7")
            return
        try:
            self._controller.modul_beenden(modul, art, note)
        except ValueError as fehler:
            messagebox.showerror("Modul beenden", str(fehler))
            return
        self.aktualisieren()

    def _on_semester_abschliessen(self):
        nummer = self._controller.kennzahlen()["aktuelles_semester"]
        if not messagebox.askyesno("Semester abschließen",
                                   f"Semester {nummer} wirklich abschließen?"):
            return
        try:
            self._controller.semester_abschliessen()
        except ValueError as fehler:
            messagebox.showerror("Semester abschließen", str(fehler))
        self.aktualisieren()

    def _on_save(self):
        try:
            self._controller.speichern()
        except OSError as fehler:
            messagebox.showerror("Speichern", f"Speichern fehlgeschlagen:\n{fehler}")
            return
        self.aktualisieren()

    def _on_schliessen(self):
        if self._controller.geaendert:
            antwort = messagebox.askyesnocancel(
                "Beenden", "Es gibt ungespeicherte Änderungen. Jetzt speichern?")
            if antwort is None:
                return
            if antwort:
                self._on_save()
        self.destroy()
