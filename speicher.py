"""Persistenz: Speichern und Laden des Studiengangs.

Die abstrakte Klasse Datenspeicher legt nur fest, WAS ein Speicher können
muss. Wie gespeichert wird, entscheidet die Unterklasse. Im Prototyp gibt es
nur den TextDateiSpeicher, später könnte z. B. ein JSON- oder
Datenbank-Speicher dazukommen, ohne dass sich der Rest des Programms ändert.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from model import Modul, ModulStatus, Studiengang

TRENNZEICHEN = ";"


class Datenspeicher(ABC):
    """Schnittstelle für alle Speicherarten."""

    @abstractmethod
    def speichern(self, sg: Studiengang):
        ...

    @abstractmethod
    def laden(self) -> Studiengang:
        ...


class TextDateiSpeicher(Datenspeicher):
    """Speichert den Studiengang zeilenweise in einer .txt Datei.

    Aufbau der Datei (Felder durch Semikolon getrennt):

        STUDIENGANG;name;gesamt_ects;regelstudienzeit;ziel_note
        SEMESTER;nummer;abgeschlossen (ja/nein)
        MODUL;semester;name;ects;status;pruefungsart;note;datum

    Zeilen mit # am Anfang und leere Zeilen werden beim Laden übersprungen.
    So kann man die Datei auch von Hand ändern.
    """

    def __init__(self, pfad: str | Path):
        self._pfad = Path(pfad)

    @property
    def pfad(self) -> Path:
        return self._pfad

    def speichern(self, sg: Studiengang):
        zeilen = [
            "# Studien-Dashboard - Datendatei",
            "# Format: siehe speicher.py (TextDateiSpeicher)",
            self._zeile("STUDIENGANG", sg.name, sg.gesamt_ects,
                        sg.regelstudienzeit, sg.ziel_note),
        ]
        for semester in sg.semester:
            zeilen.append(self._zeile("SEMESTER", semester.nummer,
                                      "ja" if semester.abgeschlossen else "nein"))
        for semester in sg.semester:
            for modul in semester.module:
                leistung = modul.pruefungsleistung
                zeilen.append(self._zeile(
                    "MODUL", semester.nummer, modul.name, modul.ects,
                    modul.status.name,
                    leistung.art if leistung else "",
                    leistung.note if leistung else "",
                    leistung.datum.isoformat() if leistung else "",
                ))
        self._pfad.parent.mkdir(parents=True, exist_ok=True)
        self._pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def laden(self) -> Studiengang:
        if not self._pfad.exists():
            raise FileNotFoundError(f"Datendatei {self._pfad} nicht gefunden")

        sg = None
        with self._pfad.open(encoding="utf-8") as datei:
            for nr, zeile in enumerate(datei, start=1):
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#"):
                    continue
                felder = zeile.split(TRENNZEICHEN)
                try:
                    if felder[0] == "STUDIENGANG":
                        sg = Studiengang(felder[1], int(felder[2]),
                                         int(felder[3]), float(felder[4]))
                    elif sg is None:
                        raise ValueError("STUDIENGANG muss die erste Zeile sein")
                    elif felder[0] == "SEMESTER":
                        if felder[2].lower() == "ja":
                            sg.get_semester(int(felder[1])).abschliessen()
                    elif felder[0] == "MODUL":
                        modul = self._modul_aus_feldern(felder)
                        sg.get_semester(int(felder[1])).modul_hinzufuegen(modul)
                    else:
                        raise ValueError(f"unbekannter Zeilentyp {felder[0]}")
                except (IndexError, ValueError, KeyError) as fehler:
                    raise ValueError(
                        f"Fehler in {self._pfad.name}, Zeile {nr}: {fehler}"
                    ) from fehler

        if sg is None:
            raise ValueError(f"{self._pfad.name} enthält keinen Studiengang")
        return sg

    @staticmethod
    def _modul_aus_feldern(felder: list[str]) -> Modul:
        _, _, name, ects, status = felder[:5]
        modul = Modul(name, int(ects))
        # Status über den Namen der Enum wiederherstellen
        status = ModulStatus[status]
        # Die Methoden des Moduls nutzen, statt den Status direkt zu setzen.
        # So gelten beim Laden dieselben Regeln wie in der Oberfläche.
        if status != ModulStatus.OFFEN:
            modul.starten()
        if status == ModulStatus.ABGESCHLOSSEN:
            art, note, datum = felder[5:8]
            modul.abschliessen(art, float(note.replace(",", ".")),
                               date.fromisoformat(datum))
        return modul

    @staticmethod
    def _zeile(*werte) -> str:
        for wert in werte:
            if TRENNZEICHEN in str(wert):
                raise ValueError(f"'{TRENNZEICHEN}' ist in '{wert}' nicht erlaubt")
        return TRENNZEICHEN.join(str(w) for w in werte)
