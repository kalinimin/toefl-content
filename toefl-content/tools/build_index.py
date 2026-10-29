#!/usr/bin/env python3
"""Собирает index.json из всех заданий со status = approved и проверяет их.

Запуск из корня репозитория:  python tools/build_index.py
Ошибки выводятся списком; при ошибках index.json не перезаписывается.
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTIONS = {
    "reading": {"complete_the_words", "daily_life", "academic_passage"},
    "listening": {"choose_response", "conversation", "announcement", "academic_talk"},
    "writing": {"build_sentence", "write_email", "academic_discussion"},
    "speaking": {"listen_repeat", "interview"},
}
CEFR = {"A2", "B1", "B2", "C1"}


def check_task(path: pathlib.Path, t: dict) -> list[str]:
    errs = []
    section = path.parent.name
    for field in ("id", "type", "section", "cefr", "version", "content"):
        if field not in t:
            errs.append(f"нет поля {field}")
    if errs:
        return errs
    if t["id"] != path.stem:
        errs.append(f"id ({t['id']}) не совпадает с именем файла")
    if t["section"] != section:
        errs.append(f"section = {t['section']}, а файл лежит в папке {section}")
    if t["type"] not in SECTIONS.get(section, set()):
        errs.append(f"type {t['type']} не относится к секции {section}")
    if t["cefr"] not in CEFR:
        errs.append(f"cefr = {t['cefr']}")
    if not isinstance(t["version"], int) or t["version"] < 1:
        errs.append("version должен быть целым числом от 1")

    c = t["content"]
    if t["type"] == "build_sentence":
        chunks, ans = c.get("chunks", []), c.get("answer", [])
        if len(chunks) != len(ans) + 1:
            errs.append(f"фрагментов {len(chunks)}, в ответе {len(ans)}: должен быть ровно один лишний")
        if sorted(set(ans)) != sorted(ans) or any(i < 0 or i >= len(chunks) for i in ans):
            errs.append("answer: индексы повторяются или выходят за пределы chunks")
    if t["type"] == "complete_the_words":
        words = c.get("paragraph", "").split()
        if not 60 <= len(words) <= 110:
            errs.append(f"абзац {len(words)} слов, нужно около 70–100")
    if t["type"] == "listen_repeat":
        n = len(c.get("sentences", []))
        if n != 7:
            errs.append(f"фраз {n}, на экзамене 7")
    if t["type"] == "interview":
        n = len(c.get("questions", []))
        if n != 4:
            errs.append(f"вопросов {n}, на экзамене 4")
    for q in c.get("questions", []):
        if "options" in q and not 0 <= q.get("answer", -1) < len(q["options"]):
            errs.append(f"вопрос {q.get('id')}: answer вне вариантов")
    return errs


def main() -> int:
    entries, problems, preview = [], [], []
    for section in SECTIONS:
        for path in sorted((ROOT / section).glob("*.json")):
            try:
                t = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                problems.append(f"{path.relative_to(ROOT)}: неверный JSON ({e})")
                continue
            if t.get("status", "approved") != "approved":
                continue
            errs = check_task(path, t)
            if errs:
                problems += [f"{path.relative_to(ROOT)}: {e}" for e in errs]
                continue
            entries.append({
                "id": t["id"],
                "path": path.relative_to(ROOT).as_posix(),
                "version": t["version"],
                "cefr": t["cefr"],
            })
            if t["type"] == "build_sentence":
                c = t["content"]
                body = " ".join(c["chunks"][i] for i in c["answer"])
                extra = [ch for i, ch in enumerate(c["chunks"]) if i not in c["answer"]]
                preview.append(f"  {t['id']}: {c['prefix']} {body} {c['suffix']}  (лишнее: {extra[0]})")

    if problems:
        print("Ошибки, index.json не обновлён:")
        print("\n".join(f"  - {p}" for p in problems))
        return 1

    index = {"updated": datetime.date.today().isoformat(), "tasks": entries}
    (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"index.json: {len(entries)} заданий")
    if preview:
        print("Проверьте собранные предложения Build a Sentence:")
        print("\n".join(preview))
    return 0


if __name__ == "__main__":
    sys.exit(main())
