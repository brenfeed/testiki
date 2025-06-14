import fitz
import re
import json
from collections import OrderedDict


def extract_question_options(q_text):
    lines = q_text.split('\n')
    main_lines = []
    options = []

    for line in lines:
        if re.match(r'^\s*\d+[).]\s*\S+', line):
            option_text = re.sub(r'^\s*\d+[).]\s*', '', line).strip()
            options.append(option_text)
        elif not options:
            main_lines.append(line)

    main_text = '\n'.join(main_lines).strip()
    return main_text, options


def parse_answer_string(s):
    """Преобразует строку ответа в список индексов (0-based)"""
    s = s.strip()
    if not s:
        return []

    # Удаляем все нецифровые символы, кроме запятых
    cleaned = re.sub(r'[^\d,]', '', s)
    if not cleaned:
        return []

    # Разбиваем по запятым и конвертируем в числа
    try:
        # Преобразуем в 0-based индексы
        return [int(x) - 1 for x in cleaned.split(',') if x.isdigit()]
    except:
        return []


def parse_pdf_questions(pdf_path):
    questions = OrderedDict()
    doc = fitz.open(pdf_path)

    full_text = ""
    for page in doc:
        full_text += page.get_text("text", sort=True) + "\n"

    pattern = r'(?:Задание|Вопрос)[\s№:]*(\d+)[\s.:-]*([\s\S]*?)(?=(?:Задание|Вопрос)[\s№:]*\d+|\Z)'
    matches = re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL)

    for match in matches:
        try:
            q_num = int(match.group(1).strip())
            q_text = match.group(2).strip()

            q_text = re.sub(r'\n\s+', '\n', q_text)
            q_text = re.sub(r'\s{2,}', ' ', q_text)

            main_text, options = extract_question_options(q_text)

            # Сохраняем исходные номера вариантов
            questions[q_num] = {
                "question_text": main_text,
                "options": options
            }
        except Exception as e:
            print(f"Ошибка обработки вопроса: {e}")

    return questions


def parse_answers(txt_path):
    answers = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if re.match(r'^(N|№|\d+)[\s°]*\d+', line):
                try:
                    q_num = int(re.search(r'\d+', line).group())
                    ans = re.sub(r'^(N|№|\d+)[\s°]*\d+\s*', '', line).strip()
                    answers[q_num] = ans
                except Exception as e:
                    print(f"Ошибка обработки ответа: {line} - {e}")

    return answers


def main(pdf_path, txt_path, output_json):
    questions = parse_pdf_questions(pdf_path)
    answers = parse_answers(txt_path)

    print(f"Найдено вопросов в PDF: {len(questions)}")
    print(f"Найдено ответов в TXT: {len(answers)}")

    result = []
    for q_num, q_data in questions.items():
        if q_num in answers:
            answer_indices = parse_answer_string(answers[q_num])
            result.append({
                "id": q_num,
                "question": q_data["question_text"],
                "options": q_data["options"],
                "answer": answer_indices,
                "type": "multiple" if len(answer_indices) > 1 else "single"
            })
        else:
            print(f"Ответ для вопроса {q_num} не найден!")

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Успешно обработано {len(result)} вопросов")


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) != 4:
        print("Использование: python parser.py <input.pdf> <answers.txt> <output.json>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    txt_path = sys.argv[2]
    output_json = sys.argv[3]

    if not os.path.exists(pdf_path):
        print(f"PDF файл не найден: {pdf_path}")
        sys.exit(1)

    if not os.path.exists(txt_path):
        print(f"TXT файл не найден: {txt_path}")
        sys.exit(1)

    main(pdf_path, txt_path, output_json)