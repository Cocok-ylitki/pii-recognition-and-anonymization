"""Формирует синтетическую и ручную части теста из независимой разметки."""

import json
import random
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
MARKED = re.compile(r"\[([A-Z]+)\|([^]]+)\]")

TEMPLATES = {
    "INN": (
        "В карточке поставщика указан ИНН {}.", "Проверили ИНН: {}.",
        "Для договора оставили реквизит налогоплательщика {}.", "ИНН {} нужно внести в акт.",
        "В заявке фигурирует ИНН № {}.", "ИНН в выгрузке — {}.",
        "Сотрудник сверил значение «{}» в поле ИНН.", "В графе «ИНН» напечатано {}.",
    ),
    "PASSPORT": (
        "Предъявлен паспорт {}.", "Скопируйте в анкету поля паспорта: {}.",
        "Сведения о паспорте — {}.", "Проверьте реквизит {} в поле паспорта.",
        "При выдаче сверили паспорт № {}.", "Он указал в заявлении паспорт {}.",
        "В поле «Паспорт» напечатано {}.", "Паспортные данные «{}» уже внесены.",
    ),
    "CARD": (
        "Для возврата выбрана карта {}.", "Укажите номер карты: {}.",
        "Поле оплаты содержало {}.", "Указан номер банковской карты {}.",
        "Получатель ввёл «{}» в поле карты.", "В чеке напечатана карта {}.",
        "Данные карты — {}.", "Перевод оформлен на карту № {}.",
    ),
    "SNILS": (
        "Внесён СНИЛС {}.", "СНИЛС: {}.", "В анкете указан страховой номер {}.",
        "СНИЛС № {} сверили с выпиской.", "Выгрузка содержит СНИЛС «{}».",
        "В карточке сотрудника СНИЛС — {}.", "В поле «СНИЛС» записано {}.",
        "СНИЛС сотрудника {} прикреплён к заявке.",
    ),
    "URL": (
        "Страница опубликована по адресу {}.", "Источник ({}).",
        "Форма обратной связи доступна по ссылке «{}».", "В инструкции указали {}.",
        "В поле сайта введено {};", "Веб-страница — {}.",
        "Ссылка из письма: {}.", "Материал доступен на {}!",
    ),
    "PHONE": (
        "Телефон: {}.", "Контактный телефон {} доступен в рабочие часы.",
        "Звоните по номеру {}.", "Мы получили телефон {} из анкеты.",
        "В поле «Телефон» оставили {}.", "Телефон отдела — {}.",
        "Для звонка используйте {}.", "Номер телефона «{}» внесли в заявку.",
    ),
    "MARRIAGE": (
        "В приложении свидетельство о браке {}.", "В графе «Свидетельство о браке» указано {}.",
        "В ЗАГС передали документ {}.", "Для подтверждения брака представлен документ {}.",
        "Свидетельство о заключении брака: {}.", "В записи о браке указан реквизит {}.",
        "ЗАГС выдал свидетельство {}.", "Номер свидетельства о браке — {}.",
    ),
    "CADASTRAL": (
        "В выписке указан кадастровый номер {}.", "Участок {} внесли в реестр.",
        "Кадастровый номер объекта: {}.", "Оценка участка с номером {} завершена.",
        "Реквизит по кадастру — {}.", "Проверьте кадастровую запись «{}».",
        "На схеме выделен участок {}.", "В карточке указан номер по кадастру {}.",
    ),
}

HAND = (
    "Я, [NAME|Анна] [SURNAME|Ветрова], направила заявление.",
    "Ответ отправили [NAME|Алексею] [SURNAME|Грачёву] на следующий день.",
    "В приёмную пришли [NAME|Лидия] [SURNAME|Крылова] и [NAME|Тимур] [SURNAME|Аскаров].",
    "Карточку заполнила [NAME|Анна-Мария] [SURNAME|Витт].",
    "Договор отдали [NAME|Льву] [SURNAME|Тихому].",
    "В архив пришло письмо на имя [NAME|Эммы] [SURNAME|Король].",
    "Вера в успех помогла команде закончить работу.",
    "Маргарита на витрине — название пиццы.",
    "Сокол сел на ограду; счёт матча 3:02.",
    "Входящий номер пакета 45 08 761200 относится к архивной накладной.",
    "В каталоге упомянули компанию Mail.Ru Group.",
    "Кадровик сверил паспорт [PASSPORT|4517000894] и СНИЛС [SNILS|112-233-445 95].",
    "Паспорт [PASSPORT|45 17 № 000894] предъявила [NAME|Анна] [SURNAME|Ветрова].",
    "ИНН [INN|502712857787]; телефон [PHONE|+7 (812) 000-00-01].",
    "Карта [CARD|4111 1111 1111 1111]; ИНН [INN|7707083893].",
    "На сайте [URL|https://portal.example/client/4111111111111111] есть инструкция.",
    "Проверьте свидетельство о браке [MARRIAGE|IV-МР № 001894] и кадастровый номер [CADASTRAL|50:09:0070611:917].",
    "На бланке заполнены поля: [MARRIAGE|III-МК № 091777], экземпляр 2.",
    "Проверьте паспорт [PASSPORT|45 17\n000894] и подпись.",
    "Сведения актуальны на 09.10.2026, интервал 16:30–17:45.",
    "Материалы доступны ([URL|https://docs.example/page_(test)]).",
    "Тел. [PHONE|(495) 000-32-19]. Сверьте также СНИЛС [SNILS|11223344595].",
    "Телефон [PHONE|4950003219], резервный [PHONE|+7-812-000-00-01].",
    "Для оплаты укажите карту [CARD|3782 822463 10005].",
    "По кадастровому номеру [CADASTRAL|77:01:123:456] нашли участок.",
    "В выписке в строке «Объект» значится [CADASTRAL|77:01:123:457].",
    "Пожалуйста, напишите [NAME|Саше] [SURNAME|Ким].",
    "Подпись: [SURNAME|Алимова] [NAME|Гульнара].",
    "Протокол [URL|ftp://archive.example:2121/inbox] сохранили.",
    "Позвоните [NAME|Ивану] [SURNAME|Зорину] по телефону [PHONE|8 916 000 12 70].",
    "СНИЛС [SNILS|112–233–445 95] проверила [NAME|Майя] [SURNAME|Егорова].",
    "Найдена карта 4111 1111 1111 1112 с ошибкой в последней цифре.",
)


def _check(digits, weights):
    return str(sum(int(digit) * weight for digit, weight in zip(digits, weights)) % 11 % 10)


def _values(rng):
    def number(count):
        return "".join(str(rng.randrange(10)) for _ in range(count))

    inn = []
    for i in range(8):
        base = rng.choice(("5027", "7707", "6601", "5402"))
        if i % 2:
            base += number(6)
            base += _check(base, (7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
            inn.append(base + _check(base, (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)))
        else:
            base += number(5)
            inn.append(base + _check(base, (2, 4, 10, 3, 5, 9, 4, 6, 8)))

    passports, cards, snils, phones, marriages, cadastral = [], [], [], [], [], []
    for i in range(8):
        region = rng.choice(("45", "40", "50", "52", "66", "46"))
        year = f"{rng.randrange(3, 26):02}"
        serial = f"{rng.randrange(1, 999999):06}"
        passports.append((
            f"{region} {year} № {serial}", f"{region}{year} {serial}",
            f"{region}{year}{serial}", f"{region}\u00a0{year}\u00a0{serial}",
        )[i % 4])

        length = 16 if i < 6 else 19
        body = str(4 + i % 2) + number(length - 2)
        total = sum((int(d) * w // 10 + int(d) * w % 10)
                    for d, w in zip(reversed(body), (2, 1) * length))
        card = body + str(-total % 10)
        cards.append(("", " ", "-", "\u202f")[i % 4].join(
            card[j:j + 4] for j in range(0, length, 4)
        ))

        body = str(rng.randrange(1, 10)) + number(8)
        remainder = sum(int(d) * w for d, w in zip(body, range(9, 0, -1))) % 101
        check = f"{0 if remainder == 100 else remainder:02}"
        snils.append((
            f"{body[:3]}-{body[3:6]}-{body[6:]} {check}", body + check,
            f"{body[:3]} {body[3:6]} {body[6:]} {check}",
            f"{body[:3]}–{body[3:6]}–{body[6:]}-{check}",
        )[i % 4])

        code = ("916", "812", "495", "846", "383", "423", "999", "800")[i]
        tail = f"{i:02}" + number(2)
        phones.append((
            f"+7 ({code}) 000-{tail[:2]}-{tail[2:]}",
            f"8 {code} 000 {tail[:2]} {tail[2:]}",
            f"({code}) 000-{tail[:2]}-{tail[2:]}",
            f"+7-{code}-000-{tail[:2]}-{tail[2:]}",
        )[i % 4])

        series = ("IV-МР", "II-АБ", "X-ЮК", "VI–УС")[i % 4]
        marker = (" № ", " ", " N ", "\u00a0№")[i % 4]
        marriages.append(series + marker + f"{rng.randrange(1, 999999):06}")
        cadastral.append(f"{rng.randrange(1, 90):02}:{rng.randrange(1, 20):02}:"
                          f"{number(5 + i % 3)}:{rng.randrange(1, 9999)}")

    urls = (
        "https://portal.example/feedback?q=1", "http://help.example:8080/start",
        "ftp://files.example/upload", "www.support.example/contacts",
        "https://личный.рф/анкета", "kb.example/guide#step",
        "https://info.example/id/4111111111111111", "https://docs.example/item_(2026)",
    )
    return dict(zip(TEMPLATES, (inn, passports, cards, snils, urls, phones, marriages, cadastral)))


def marked_row(marked, source, index):
    text = ""
    spans = []
    cursor = 0
    for match in MARKED.finditer(marked):
        label, value = match.groups()
        text += marked[cursor:match.start()]
        spans.append([label, len(text), len(text) + len(value)])
        text += value
        cursor = match.end()
    return dict(id=f"{source}-{index:03}", source=source, text=text + marked[cursor:], spans=spans)


def synthetic():
    values = _values(random.Random(13))
    for label, templates in TEMPLATES.items():
        for template in templates:
            for value in values[label]:
                yield template.format(f"[{label}|{value}]")
    for label, quota in (("CARD", 6), ("INN", 5), ("SNILS", 5)):
        for i in range(quota):
            value = re.sub(r"[^0-9]", "", values[label][i])
            wrong = value[:-1] + str((int(value[-1]) + 1) % 10)
            yield TEMPLATES[label][i].format(wrong)


def main():
    for source, examples in (("synthetic", synthetic()), ("hand", HAND)):
        path = DATA / f"{source}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as output:
            for i, text in enumerate(examples, 1):
                output.write(json.dumps(marked_row(text, source, i), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
