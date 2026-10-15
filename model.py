"""Fachklassen (Entity-Klassen) des Studien-Dashboards.

Die Klassen entsprechen dem Klassendiagramm aus Phase 1 bzw. dem Teil
"Fachklassen" der Gesamtarchitektur aus Phase 2. Sie wissen nichts von der
Oberfläche oder der Textdatei und lassen sich deshalb auch ohne GUI testen.
"""

from __future__ import annotations

from datetime import date
from enum import Enum


class ModulStatus(Enum):
    """Status eines Moduls. Daraus ergeben sich die drei Segmente der Piechart."""

    OFFEN = "offen"
    IN_BEARBEITUNG = "in Bearbeitung"
    ABGESCHLOSSEN = "abgeschlossen"


class Pruefungsleistung:
    """Ergebnis der Prüfung zu einem Modul (Klausur, Portfolio, ...).

    Wird nur vom Modul selbst in Modul.abschliessen() erzeugt (Komposition).
    """

    # Notenbereich an deutschen Hochschulen, bis einschließlich 4,0 bestanden
    BESTEHENSGRENZE = 4.0

    def __init__(self, art: str, note: float, datum: date):
        self._art = art
        self.note = note  # läuft schon über den Setter und wird geprüft
        self._datum = datum

    @property
    def art(self) -> str:
        return self._art

    @property
    def note(self) -> float:
        return self._note

    @note.setter
    def note(self, wert: float):
        if not 1.0 <= wert <= 5.0:
            raise ValueError("Note muss zwischen 1,0 und 5,0 liegen")
        self._note = float(wert)

    @property
    def datum(self) -> date:
        return self._datum

    def ist_bestanden(self) -> bool:
        return self._note <= self.BESTEHENSGRENZE


class Modul:
    """Ein Modul des Studiengangs, z. B. "Objektorientierte Programmierung mit Python"."""

    def __init__(self, name: str, ects: int,
                 status: ModulStatus = ModulStatus.OFFEN):
        if not name.strip():
            raise ValueError("Modulname darf nicht leer sein")
        if ects <= 0:
            raise ValueError("ECTS müssen größer als 0 sein")
        self._name = name.strip()
        self._ects = ects
        self._status = status
        # 0..1 im Klassendiagramm: solange das Modul nicht fertig ist, gibt es
        # noch keine Prüfungsleistung
        self._pruefungsleistung: Pruefungsleistung | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def ects(self) -> int:
        return self._ects

    @property
    def status(self) -> ModulStatus:
        return self._status

    @property
    def pruefungsleistung(self) -> Pruefungsleistung | None:
        return self._pruefungsleistung

    def starten(self):
        """Setzt ein offenes Modul auf 'in Bearbeitung'."""
        if self._status != ModulStatus.OFFEN:
            raise ValueError(f"Modul '{self._name}' wurde schon begonnen")
        self._status = ModulStatus.IN_BEARBEITUNG

    def abschliessen(self, art: str, note: float, datum: date | None = None):
        """Beendet das Modul und legt dabei die Prüfungsleistung an.

        Es wird nur das Endergebnis gespeichert. Ist die Note schlechter als
        4,0, wird das Modul nicht abgeschlossen, da es dann ja noch nicht
        bestanden ist.
        """
        if self._status == ModulStatus.ABGESCHLOSSEN:
            raise ValueError(f"Modul '{self._name}' ist bereits abgeschlossen")
        leistung = Pruefungsleistung(art, note, datum or date.today())
        if not leistung.ist_bestanden():
            raise ValueError("Mit einer Note über 4,0 ist das Modul nicht "
                             "bestanden und kann noch nicht beendet werden")
        self._pruefungsleistung = leistung
        self._status = ModulStatus.ABGESCHLOSSEN

    def get_note(self) -> float | None:
        if self._pruefungsleistung is None:
            return None
        return self._pruefungsleistung.note

    def __repr__(self) -> str:
        return f"Modul({self._name!r}, {self._ects} ECTS, {self._status.name})"


class Semester:
    """Ein Semester mit den Modulen, die ihm zugeordnet sind.

    Die Module werden nur referenziert (Aggregation). Ein Modul kann also aus
    einem Semester entfernt und einem anderen zugeordnet werden, ohne dass
    es dabei verloren geht.
    """

    def __init__(self, nummer: int, abgeschlossen: bool = False):
        self._nummer = nummer
        self._abgeschlossen = abgeschlossen
        self._module: list[Modul] = []

    @property
    def nummer(self) -> int:
        return self._nummer

    @property
    def abgeschlossen(self) -> bool:
        return self._abgeschlossen

    @property
    def module(self) -> list[Modul]:
        # Kopie zurückgeben, damit die Liste nicht von außen verändert wird
        return list(self._module)

    def modul_hinzufuegen(self, modul: Modul):
        if modul not in self._module:
            self._module.append(modul)

    def modul_entfernen(self, modul: Modul):
        self._module.remove(modul)

    def abschliessen(self):
        self._abgeschlossen = True


class Studiengang:
    """Der Studiengang mit den Zielwerten, die das Dashboard überwacht."""

    def __init__(self, name: str, gesamt_ects: int = 180,
                 regelstudienzeit: int = 6, ziel_note: float = 2.0):
        self._name = name
        self._gesamt_ects = gesamt_ects
        self._regelstudienzeit = regelstudienzeit
        self._ziel_note = ziel_note
        # Komposition: der Studiengang legt seine Semester selbst an
        self._semester = [Semester(i) for i in range(1, regelstudienzeit + 1)]

    @property
    def name(self) -> str:
        return self._name

    @property
    def gesamt_ects(self) -> int:
        return self._gesamt_ects

    @property
    def regelstudienzeit(self) -> int:
        return self._regelstudienzeit

    @property
    def ziel_note(self) -> float:
        return self._ziel_note

    @property
    def semester(self) -> list[Semester]:
        return list(self._semester)

    def get_semester(self, nummer: int) -> Semester:
        for semester in self._semester:
            if semester.nummer == nummer:
                return semester
        raise ValueError(f"Semester {nummer} gibt es nicht")

    def aktuelles_semester(self) -> Semester:
        """Erstes Semester, das noch nicht abgeschlossen ist."""
        for semester in self._semester:
            if not semester.abgeschlossen:
                return semester
        # alle abgeschlossen -> das letzte bleibt das aktuelle
        return self._semester[-1]

    def alle_module(self) -> list[Modul]:
        return [m for s in self._semester for m in s.module]

    def berechne_notendurchschnitt(self) -> float | None:
        """Nach ECTS gewichteter Durchschnitt aller abgeschlossenen Module.

        Gibt None zurück, solange noch kein Modul eine Note hat.
        """
        benotet = [m for m in self.alle_module() if m.get_note() is not None]
        summe_ects = sum(m.ects for m in benotet)
        if summe_ects == 0:
            return None
        return sum(m.get_note() * m.ects for m in benotet) / summe_ects

    def berechne_erreichte_ects(self) -> int:
        return sum(m.ects for m in self.alle_module()
                   if m.status == ModulStatus.ABGESCHLOSSEN)

    def berechne_soll_ects(self) -> int:
        """ECTS, die nach den abgeschlossenen Semestern erreicht sein sollten."""
        pro_semester = self._gesamt_ects / self._regelstudienzeit
        fertig = sum(1 for s in self._semester if s.abgeschlossen)
        return round(fertig * pro_semester)
