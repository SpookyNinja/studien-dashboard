"""Steuerung: verbindet die Oberfläche mit den Fachklassen.

Die Oberfläche ruft nur Methoden des DashboardControllers auf und greift
nicht selbst auf Studiengang, Semester oder Module zu. Regeln, die das
ganze Dashboard betreffen (z. B. höchstens drei Module gleichzeitig in
Bearbeitung), werden hier geprüft.
"""

from __future__ import annotations

from model import Modul, ModulStatus, Studiengang
from speicher import Datenspeicher


class DashboardController:

    MAX_IN_BEARBEITUNG = 3

    def __init__(self, speicher: Datenspeicher):
        self._speicher = speicher
        self._studiengang: Studiengang = speicher.laden()
        self._geaendert = False

    @property
    def geaendert(self) -> bool:
        """True, wenn es Änderungen gibt, die noch nicht gespeichert wurden."""
        return self._geaendert

    def offene_module(self) -> list[Modul]:
        return [m for m in self._studiengang.alle_module()
                if m.status == ModulStatus.OFFEN]

    def module_in_bearbeitung(self) -> list[Modul]:
        return [m for m in self._studiengang.alle_module()
                if m.status == ModulStatus.IN_BEARBEITUNG]

    def modul_hinzufuegen(self, modul: Modul):
        """Startet ein offenes Modul im aktuellen Semester."""
        if len(self.module_in_bearbeitung()) >= self.MAX_IN_BEARBEITUNG:
            raise ValueError(f"Es können höchstens {self.MAX_IN_BEARBEITUNG} "
                             "Module gleichzeitig bearbeitet werden")
        modul.starten()
        # Das Modul wird in das aktuelle Semester verschoben. Durch die
        # Aggregation bleibt es dabei mit allen Daten erhalten.
        aktuell = self._studiengang.aktuelles_semester()
        for semester in self._studiengang.semester:
            if modul in semester.module and semester is not aktuell:
                semester.modul_entfernen(modul)
        aktuell.modul_hinzufuegen(modul)
        self._geaendert = True

    def modul_beenden(self, modul: Modul, art: str, note: float):
        modul.abschliessen(art, note)
        self._geaendert = True

    def semester_abschliessen(self):
        """Schließt das aktuelle Semester ab, dadurch steigt der Soll-Wert."""
        aktuell = self._studiengang.aktuelles_semester()
        if aktuell.abgeschlossen:
            raise ValueError("Alle Semester sind bereits abgeschlossen")
        aktuell.abschliessen()
        self._geaendert = True

    def kennzahlen(self) -> dict:
        """Sammelt alle Werte, die das Dashboard anzeigt."""
        sg = self._studiengang
        module = sg.alle_module()
        anzahl = {status: sum(1 for m in module if m.status == status)
                  for status in ModulStatus}
        return {
            "studiengang": sg.name,
            "notendurchschnitt": sg.berechne_notendurchschnitt(),
            "ziel_note": sg.ziel_note,
            "erreichte_ects": sg.berechne_erreichte_ects(),
            "soll_ects": sg.berechne_soll_ects(),
            "gesamt_ects": sg.gesamt_ects,
            "aktuelles_semester": sg.aktuelles_semester().nummer,
            "regelstudienzeit": sg.regelstudienzeit,
            "anzahl_status": anzahl,
        }

    def speichern(self):
        self._speicher.speichern(self._studiengang)
        self._geaendert = False
