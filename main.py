import requests
import json
import feedparser
import os
import asyncio
from datetime import datetime

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = "8285832122:AAE0BdJxpF3kigE3Ljnj0DbWmDbVjFeQcKs"
CHAT_ID = "7745305298"

RSS_SOURCES = {
    'habr': 'https://habr.com/ru/rss/all/all/?fl=ru',
    'vc_ru': 'https://vc.ru/rss', 
}

RELEVANT_KEYWORDS = [
    'python', 'junior', 'джуниор', 'собеседование', 'карьера',
    'работа', 'IT', 'разработчик', 'программист', 'начинающий'
]

# ==================== ОБЩИЕ ФУНКЦИИ ====================

def get_vacancies():
    """Парсим вакансии с HH.ru"""
    try:
        url = "https://api.hh.ru/vacancies?text=python&experience=noExperience"
        data = requests.get(url, timeout=10)
        return data.json()
    except Exception as e:
        print(f"❌ Ошибка получения вакансий: {e}")
        return None

def filter_vacancies(data):
    """Фильтруем вакансии для джунов"""
    junior_vacancies = []
    if not data:
        return []
    
    for vacancy in data['items']:
        if (vacancy['id'] and vacancy['id'].strip() != "" and 
            any(keyword in vacancy['name'].lower() for keyword in ['data', 'bi', 'etl', 'analytics'])):
            junior_vacancies.append(vacancy)
    return junior_vacancies

def save_vacancies(junior_vacancies):
    """Сохраняем только новые вакансии"""
    new_vacancies = []
    try:
        with open('old_vacancies.json', 'r') as f:
            old_vacancies = json.load(f) 
    except FileNotFoundError:
        old_vacancies = []
    
    old_ids = {v['id'] for v in old_vacancies}
    for vacancy in junior_vacancies:
        if vacancy['id'] not in old_ids:
            new_vacancies.append(vacancy)
       
    with open('old_vacancies.json', 'w') as f:
        json.dump(junior_vacancies, f)
    return new_vacancies

def get_news():
    """Парсим новости"""
    all_new_articles = []
    
    try:
        with open('previous_news.json', 'r', encoding='utf-8') as f:
            previous_articles = json.load(f)
    except FileNotFoundError:
        previous_articles = []
    
    previous_titles = {a['title'] for a in previous_articles}
    current_articles = previous_articles.copy()
    
    for source_name, rss_url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(rss_url)
            raw_articles = []
            for entry in feed.entries[:10]:
                raw_articles.append({
                    'title': entry.title,
                    'url': entry.link,
                    'source': source_name
                })
            
            # Фильтруем по релевантности
            relevant_articles = []
            for article in raw_articles:
                title_lower = article['title'].lower()
                if any(keyword in title_lower for keyword in RELEVANT_KEYWORDS):
                    relevant_articles.append(article)
            
            # Дедубликация и проверка на новые
            seen_titles = set()
            for article in relevant_articles:
                short_title = article['title'][:40].lower()
                if short_title not in seen_titles:
                    seen_titles.add(short_title)
                    if article['title'] not in previous_titles:
                        current_articles.append(article)
                        all_new_articles.append(article)
                        previous_titles.add(article['title'])
                        
        except Exception as e:
            print(f"❌ Ошибка {source_name}: {e}")
    
    # Сохраняем
    if all_new_articles:
        with open('previous_news.json', 'w', encoding='utf-8') as f:
            json.dump(current_articles, f, ensure_ascii=False, indent=2)
    
    return all_new_articles

def format_digest(vacancies, news):
    """Форматируем дайджест"""
    message = "📊 ЕЖЕДНЕВНЫЙ ДАЙДЖЕСТ ДЛЯ ДЖУНОВ\n\n"
    
    if vacancies:
        message += f"🎯 Вакансии ({len(vacancies)}):\n"
        for v in vacancies[:5]:
            message += f"• {v['name']}\n"
        message += "\n"
    
    if news:
        message += f"📰 Новости ({len(news)}):\n"
        for n in news[:3]:
            message += f"• {n['title']}\n"
    
    message += "Удачи в поисках! 💪"
    return message

# ==================== РЕЖИМ 1: СЕРВЕРНАЯ ВЕРСИЯ ====================

async def send_telegram_message(text):
    """Отправка сообщения в Telegram"""
    from telegram import Bot
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)

def vacancies_etl():
    """ETL для вакансий"""
    print("🔄 Вакансии: начинаем ETL...")
    raw_data = get_vacancies()
    if not raw_data:
        print("❌ Не удалось получить данные вакансий")
        return []
    
    clean_data = filter_vacancies(raw_data)
    new_vacancies = save_vacancies(clean_data)
    print(f"✅ Вакансии: {len(new_vacancies)} новых")
    return new_vacancies

def news_etl():
    """ETL для новостей"""
    print("📰 Новости: начинаем ETL...")
    new_news = get_news()
    print(f"✅ Новости: {len(new_news)} новых")
    return new_news

async def main():
    """Основная функция для серверного запуска"""
    print("🚀 ЗАПУСК НА СЕРВЕРЕ (без Airflow)")
    
    # Запускаем ETL процессы
    vacancies = vacancies_etl()
    news = news_etl()
    
    # Отправляем дайджест
    if vacancies or news:
        message = format_digest(vacancies, news)
        await send_telegram_message(message)
        print("✅ Дайджест отправлен в Telegram")
    else:
        await send_telegram_message("📭 Сегодня нет новых вакансий и новостей")
        print("📭 Ничего нового")

# ==================== РЕЖИМ 2: AIRFLOW DAG ====================
"""
# РАЗКОММЕНТИРОВАТЬ ДЛЯ AIRFLOW:

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# Конфиги через Airflow Variables (рекомендуется для продакшена)
# TELEGRAM_TOKEN = Variable.get("telegram_token")
# CHAT_ID = Variable.get("chat_id")

def airflow_vacancies_etl():
    # Обертка для Airflow
    return vacancies_etl()

def airflow_news_etl():
    return news_etl()

def airflow_send_digest(**context):
    # Логика с XCom для Airflow
    ti = context['ti']
    vacancies = ti.xcom_pull(task_ids='vacancies_etl') or []
    news = ti.xcom_pull(task_ids='news_etl') or []
    
    # Формируем и отправляем сообщение
    if vacancies or news:
        message = format_digest(vacancies, news)
        # В реальном Airflow используйте Telegram Hook или отдельный оператор
        print(f"📤 Отправка в Telegram: {len(vacancies)} вакансий, {len(news)} новостей")
        # Реальная отправка: await send_telegram_message(message)
    else:
        print("📭 Ничего нового для отправки")

# Определение DAG
with DAG(
    'daily_jobs_pipeline',
    description='Production ETL pipeline for junior jobs monitoring',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['jobs', 'monitoring', 'etl']
) as dag:
    
    vacancies_task = PythonOperator(
        task_id='vacancies_etl',
        python_callable=airflow_vacancies_etl
    )
    
    news_task = PythonOperator(
        task_id='news_etl',
        python_callable=airflow_news_etl
    )
    
    telegram_task = PythonOperator(
        task_id='send_telegram_digest',
        python_callable=airflow_send_digest,
        provide_context=True
    )
    
    # Определяем порядок выполнения
    vacancies_task >> news_task >> telegram_task

"""

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    # Автоматическое определение режима
    try:
        # Пробуем импортировать Airflow
        from airflow import DAG
        print("✅ Режим: Airflow DAG (раскомментируйте блок выше)")
        # DAG будет загружен при импорте, если раскомментирован
    except ImportError:
        print("✅ Режим: Серверный запуск")
        # Запускаем серверную версию
        asyncio.run(main())
