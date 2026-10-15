"""Tests für TextDateiSpeicher und DashboardController. Aufruf: python -m unittest"""

import tempfile
import unittest
from pathlib import Path

from controller import DashboardController
from model import ModulStatus, Studiengang
from speicher import Datenspeicher, TextDateiSpeicher

BEISPIEL = Path(__file__).resolve().parent.parent / "daten" / "beispiel_studium.txt"


class TestTextDateiSpeicher(unittest.TestCase):

    def test_abstrakte_klasse_nicht_instanziierbar(self):
        with self.assertRaises(TypeError):
            Datenspeicher()

    def test_beispieldaten_laden(self):
        sg = TextDateiSpeicher(BEISPIEL).laden()
        self.assertEqual(sg.gesamt_ects, 180)
        self.assertEqual(sum(m.ects for m in sg.alle_module()), 180)
        self.assertEqual(sg.berechne_erreichte_ects(), 55)
        self.assertEqual(sg.berechne_soll_ects(), 60)

    def test_speichern_und_wieder_laden(self):
        sg = TextDateiSpeicher(BEISPIEL).laden()
        with tempfile.TemporaryDirectory() as ordner:
            speicher = TextDateiSpeicher(Path(ordner) / "test.txt")
            speicher.speichern(sg)
            neu = speicher.laden()
        self.assertEqual(neu.berechne_notendurchschnitt(), sg.berechne_notendurchschnitt())
        self.assertEqual([repr(m) for m in neu.alle_module()],
                         [repr(m) for m in sg.alle_module()])

    def test_kaputte_zeile_gibt_zeilennummer_an(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "kaputt.txt"
            pfad.write_text("STUDIENGANG;Test;180;6;2.0\nMODUL;1;A;fuenf;OFFEN;;;\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Zeile 2"):
                TextDateiSpeicher(pfad).laden()


class SpeicherImArbeitsspeicher(Datenspeicher):
    """Testdouble: zeigt nebenbei, dass der Controller jeden Datenspeicher nimmt."""

    def __init__(self, sg: Studiengang):
        self.sg = sg
        self.gespeichert = 0

    def speichern(self, sg):
        self.gespeichert += 1

    def laden(self):
        return self.sg


class TestDashboardController(unittest.TestCase):

    def setUp(self):
        self.speicher = SpeicherImArbeitsspeicher(TextDateiSpeicher(BEISPIEL).laden())
        self.controller = DashboardController(self.speicher)

    def test_kennzahlen(self):
        werte = self.controller.kennzahlen()
        self.assertEqual(werte["erreichte_ects"], 55)
        self.assertEqual(werte["aktuelles_semester"], 3)
        self.assertEqual(werte["anzahl_status"][ModulStatus.ABGESCHLOSSEN], 11)
        self.assertEqual(werte["anzahl_status"][ModulStatus.IN_BEARBEITUNG], 2)
        self.assertAlmostEqual(werte["notendurchschnitt"], 1.76, places=2)

    def test_hoechstens_drei_module(self):
        offene = self.controller.offene_module()
        self.controller.modul_hinzufuegen(offene[0])
        with self.assertRaises(ValueError):
            self.controller.modul_hinzufuegen(offene[1])
        self.assertEqual(len(self.controller.module_in_bearbeitung()), 3)

    def test_modul_wird_ins_aktuelle_semester_verschoben(self):
        modul = next(m for m in self.controller.offene_module()
                     if m.name == "Cloud Computing")  # laut Plan Semester 4
        self.controller.modul_hinzufuegen(modul)
        sg = self.speicher.sg
        self.assertIn(modul, sg.get_semester(3).module)
        self.assertNotIn(modul, sg.get_semester(4).module)

    def test_modul_beenden_aktualisiert_kennzahlen(self):
        modul = self.controller.module_in_bearbeitung()[0]
        self.controller.modul_beenden(modul, "Klausur", 1.0)
        werte = self.controller.kennzahlen()
        self.assertEqual(werte["erreichte_ects"], 60)
        self.assertEqual(werte["anzahl_status"][ModulStatus.ABGESCHLOSSEN], 12)
        self.assertTrue(self.controller.geaendert)

    def test_speichern_setzt_geaendert_zurueck(self):
        self.controller.semester_abschliessen()
        self.assertTrue(self.controller.geaendert)
        self.controller.speichern()
        self.assertFalse(self.controller.geaendert)
        self.assertEqual(self.speicher.gespeichert, 1)
        self.assertEqual(self.controller.kennzahlen()["soll_ects"], 90)


if __name__ == "__main__":
    unittest.main()
