"""Tests für die Fachklassen. Aufruf: python -m unittest"""

import unittest
from datetime import date

from model import Modul, ModulStatus, Pruefungsleistung, Semester, Studiengang


class TestPruefungsleistung(unittest.TestCase):

    def test_ungueltige_note_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            Pruefungsleistung("Klausur", 0.7, date.today())
        with self.assertRaises(ValueError):
            Pruefungsleistung("Klausur", 5.3, date.today())

    def test_setter_prueft_auch_spaeter(self):
        leistung = Pruefungsleistung("Klausur", 2.0, date.today())
        with self.assertRaises(ValueError):
            leistung.note = 6.0
        self.assertEqual(leistung.note, 2.0)

    def test_bestanden(self):
        self.assertTrue(Pruefungsleistung("Klausur", 4.0, date.today()).ist_bestanden())
        self.assertFalse(Pruefungsleistung("Klausur", 5.0, date.today()).ist_bestanden())


class TestModul(unittest.TestCase):

    def test_ablauf_offen_bis_abgeschlossen(self):
        modul = Modul("OOP mit Python", 5)
        self.assertEqual(modul.status, ModulStatus.OFFEN)
        self.assertIsNone(modul.pruefungsleistung)
        modul.starten()
        self.assertEqual(modul.status, ModulStatus.IN_BEARBEITUNG)
        modul.abschliessen("Portfolio", 1.7)
        self.assertEqual(modul.status, ModulStatus.ABGESCHLOSSEN)
        self.assertEqual(modul.get_note(), 1.7)

    def test_nicht_bestanden_bleibt_offen(self):
        modul = Modul("Mathe", 5)
        modul.starten()
        with self.assertRaises(ValueError):
            modul.abschliessen("Klausur", 5.0)
        self.assertEqual(modul.status, ModulStatus.IN_BEARBEITUNG)
        self.assertIsNone(modul.pruefungsleistung)

    def test_zweimal_starten_geht_nicht(self):
        modul = Modul("Mathe", 5)
        modul.starten()
        with self.assertRaises(ValueError):
            modul.starten()


class TestSemesterUndStudiengang(unittest.TestCase):

    def setUp(self):
        self.sg = Studiengang("Test", gesamt_ects=180, regelstudienzeit=6, ziel_note=2.0)

    def test_semester_werden_angelegt(self):
        self.assertEqual([s.nummer for s in self.sg.semester], [1, 2, 3, 4, 5, 6])

    def test_modul_verschieben_aggregation(self):
        modul = Modul("Statistik", 5)
        s2, s3 = self.sg.get_semester(2), self.sg.get_semester(3)
        s2.modul_hinzufuegen(modul)
        s2.modul_entfernen(modul)
        s3.modul_hinzufuegen(modul)
        self.assertNotIn(modul, s2.module)
        self.assertIn(modul, s3.module)

    def test_module_liste_nicht_von_aussen_aenderbar(self):
        semester = self.sg.get_semester(1)
        semester.module.append(Modul("Fremd", 5))
        self.assertEqual(semester.module, [])

    def test_notendurchschnitt_nach_ects_gewichtet(self):
        a, b = Modul("A", 5), Modul("B", 10)
        for modul, note in ((a, 1.0), (b, 2.5)):
            modul.starten()
            modul.abschliessen("Klausur", note)
            self.sg.get_semester(1).modul_hinzufuegen(modul)
        # (1,0 * 5 + 2,5 * 10) / 15 = 2,0
        self.assertAlmostEqual(self.sg.berechne_notendurchschnitt(), 2.0)

    def test_notendurchschnitt_ohne_noten(self):
        self.sg.get_semester(1).modul_hinzufuegen(Modul("A", 5))
        self.assertIsNone(self.sg.berechne_notendurchschnitt())

    def test_ects_ist_und_soll(self):
        modul = Modul("A", 5)
        modul.starten()
        modul.abschliessen("Klausur", 2.0)
        self.sg.get_semester(1).modul_hinzufuegen(modul)
        self.sg.get_semester(1).modul_hinzufuegen(Modul("B", 5))
        self.assertEqual(self.sg.berechne_erreichte_ects(), 5)
        self.assertEqual(self.sg.berechne_soll_ects(), 0)
        self.sg.get_semester(1).abschliessen()
        self.assertEqual(self.sg.berechne_soll_ects(), 30)
        self.assertEqual(self.sg.aktuelles_semester().nummer, 2)


if __name__ == "__main__":
    unittest.main()
