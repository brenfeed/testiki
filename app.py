from flask import Flask, render_template, request, session, redirect, url_for, g
import json
import random
from datetime import timedelta
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=40)

# Загрузка всех вопросов при запуске приложения
with open('output.json', 'r', encoding='utf-8') as f:
    ALL_QUESTIONS = json.load(f)
    # В app.py после загрузки вопросов
    print("Sample question:", ALL_QUESTIONS[0])


def get_question_by_id(q_id):
    """Получить вопрос по ID"""
    return next((q for q in ALL_QUESTIONS if q['id'] == q_id), None)


@app.route('/')
def index():
    session.clear()
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_test():
    # Выбираем 50 случайных ID вопросов
    all_ids = [q['id'] for q in ALL_QUESTIONS]
    selected_ids = random.sample(all_ids, min(50, len(all_ids)))

    session['question_ids'] = selected_ids
    session['answers'] = {}
    return redirect(url_for('test_page'))


@app.route('/test')
def test_page():
    if 'question_ids' not in session:
        return redirect(url_for('index'))

    # Получаем полные вопросы по сохраненным ID
    questions = [get_question_by_id(q_id) for q_id in session['question_ids']]
    return render_template('test.html', questions=questions)


@app.route('/submit', methods=['POST'])
def submit():
    user_answers = {}

    # Получаем все параметры формы
    form_data = request.form

    # Обрабатываем каждый вопрос из сессии
    for q_id in session['question_ids']:
        key = f'q{q_id}'

        # Для множественного выбора (чекибоксы)
        if key in request.form.to_dict(flat=False):
            values = request.form.getlist(key)
            if values:
                try:
                    user_answers[q_id] = [int(v) for v in values]
                except ValueError:
                    print(f"Error converting values for question {q_id}: {values}")

        # Для одиночного выбора (радио-кнопки)
        elif key in form_data:
            value = form_data.get(key)
            if value:
                try:
                    user_answers[q_id] = [int(value)]
                except ValueError:
                    print(f"Error converting value for question {q_id}: {value}")

    session['answers'] = user_answers
    print("Saved answers:", user_answers)
    return redirect(url_for('results'))


@app.route('/results')
def results():
    print("Session data:", session)
    print("Answers in session:", session.get('answers'))
    if 'question_ids' not in session or 'answers' not in session:
        return redirect(url_for('index'))

    questions = [get_question_by_id(q_id) for q_id in session['question_ids']]
    user_answers = session['answers']
    score = 0
    all_questions_data = []

    for q in questions:
        q_id = q['id']
        correct = sorted(q['answer'])

        # Получаем ответ пользователя, преобразуя отсутствующий ответ в пустой список
        user = sorted(user_answers.get(str(q_id), []))

        print(f"Question {q_id}: Correct={correct}, User={user}")
        # Определяем статус ответа
        status = 'unanswered'
        if str(q_id) in user_answers:
            status = 'correct' if correct == user else 'incorrect'

        if status == 'correct':
            score += 1

        # Формируем данные для отображения
        q_data = {
            'id': q_id,
            'question': q['question'],
            'options': q['options'],
            'status': status,
            'user_answers': [q['options'][i] for i in user] if user else ["Нет ответа"],
            'correct_answers': [q['options'][i] for i in correct]
        }
        all_questions_data.append(q_data)
    print(score)
    print(all_questions_data)
    return render_template(
        'results.html',
        score=score,
        total=len(questions),
        all_questions=all_questions_data
    )

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()