"""
French Public Holidays Calculator and Date Attributes Generator.
Modernizes jGenerateCalendar and replaces manual joursFeries.xlsx dependency.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple


def calculate_easter_sunday(year: int) -> date:
    """
    Computes Easter Sunday using the Anonymous Gregorian algorithm (Meeus/Jones/Butcher).
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


class FrenchHolidaysCalculator:
    """
    Computes all standard French legal public holidays (Jours fériés légaux en France).
    """

    @staticmethod
    def get_holidays_for_year(year: int) -> Dict[date, str]:
        easter = calculate_easter_sunday(year)
        easter_monday = easter + timedelta(days=1)
        ascension = easter + timedelta(days=39)
        pentecost_monday = easter + timedelta(days=50)

        holidays = {
            date(year, 1, 1): "Jour de l'An",
            easter_monday: "Lundi de Pâques",
            date(year, 5, 1): "Fête du Travail",
            date(year, 5, 8): "Victoire 1945",
            ascension: "Ascension",
            pentecost_monday: "Lundi de Pentecôte",
            date(year, 7, 14): "Fête Nationale",
            date(year, 8, 15): "Assomption",
            date(year, 11, 1): "Toussaint",
            date(year, 11, 11): "Armistice 1918",
            date(year, 12, 25): "Noël",
        }
        return holidays

    @classmethod
    def get_holidays_range(cls, start_year: int, end_year: int) -> Dict[date, str]:
        all_holidays = {}
        for y in range(start_year, end_year + 1):
            all_holidays.update(cls.get_holidays_for_year(y))
        return all_holidays
