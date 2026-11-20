"""Проверка контрольных разрядов и валидности структурированных ПДн."""


def luhn_ok(digits: str) -> bool:
    """Алгоритм Луна для номера банковской карты."""
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _inn_digit(digits, coefs):
    return sum(int(d) * c for d, c in zip(digits, coefs)) % 11 % 10


def inn_ok(s: str) -> bool:
    """ИНН: 10 цифр (юрлицо) с одним или 12 цифр (физлицо) с двумя контрольными разрядами."""
    if not s.isdigit():
        return False
    if len(s) == 10:
        return _inn_digit(s, (2, 4, 10, 3, 5, 9, 4, 6, 8)) == int(s[9])
    if len(s) == 12:
        c1 = _inn_digit(s, (7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        c2 = _inn_digit(s, (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        return c1 == int(s[10]) and c2 == int(s[11])
    return False


def snils_ok(s: str) -> bool:
    """СНИЛС: 9 цифр номера + 2 цифры контрольного числа."""
    if not s.isdigit() or len(s) != 11:
        return False
    num = s[:9]
    # Контрольное число не вычисляется для номеров <= 001-001-998
    if int(num) <= 1001998:
        return False
    total = sum(int(d) * w for d, w in zip(num, range(9, 0, -1)))
    if total < 100:
        check = total
    elif total in (100, 101):
        check = 0
    else:
        check = total % 101
        if check in (100, 101):
            check = 0
    return check == int(s[9:])


# Допустимые коды субъектов РФ в серии паспорта (первые 2 цифры серии — код ОКАТО региона)
_PASSPORT_REGIONS = {
    1, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 17, 18, 19, 20, 22, 24, 25, 26, 27, 28, 29, 30, 32, 33,
    34, 35, 36, 37, 38, 40, 41, 42, 44, 45, 46, 47, 49, 50, 52, 53, 54, 56, 57, 58, 60, 61, 63,
    64, 65, 66, 67, 68, 69, 70, 71, 73, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
    89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
}


def passport_ok(s: str) -> bool:
    """Паспорт РФ: серия (2 цифры региона + 2 цифры года выдачи) и 6 цифр номера.

    Контрольных разрядов нет, проверяем регион и правдоподобность года выдачи.
    """
    if not s.isdigit() or len(s) != 10:
        return False
    if int(s[:2]) not in _PASSPORT_REGIONS:
        return False
    year = int(s[2:4])
    if not (year <= 26 or year >= 97):  # паспорта РФ выдаются с 1997 года
        return False
    return s[4:] != "000000"


def phone_ok(digits: str) -> bool:
    """Российский номер: 11 цифр, 7/8 + код (9xx — мобильный, 3xx-8xx — городской)."""
    if not digits.isdigit() or len(digits) != 11 or digits[0] not in "78":
        return False
    return digits[1] in "3489"


