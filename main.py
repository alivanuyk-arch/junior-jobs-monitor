import asyncio
import requests
import json
import feedparser
import re
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# ==================== ВАКАНСИИ ====================
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

# ==================== НОВОСТИ ====================
RSS_SOURCES = {
    'habr': 'https://habr.com/ru/rss/all/all/?fl=ru',
    'vc_ru': 'https://vc.ru/rss', 
}

RELEVANT_KEYWORDS = [
    'python', 'junior', 'джуниор', 'собеседование', 'карьера',
    'работа', 'IT', 'разработчик', 'программист', 'начинающий'
]

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

# ==================== TELEGRAM ====================
async def send_telegram_message(text):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)

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

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
async def main():
    """Запускаем весь пайплайн"""
    print("🚀 Запуск парсера...")
    
    # 1. Вакансии
    vacancies_data = get_vacancies()
    if vacancies_data:
        filtered_vacancies = filter_vacancies(vacancies_data)
        new_vacancies = save_vacancies(filtered_vacancies)
        print(f"✅ Вакансии: {len(new_vacancies)} новых")
    else:
        new_vacancies = []
    
    # 2. Новости
    new_news = get_news()
    print(f"✅ Новости: {len(new_news)} новых")
    
    # 3. Отправляем в Telegram
    if new_vacancies or new_news:
        message = format_digest(new_vacancies, new_news)
        await send_telegram_message(message)
        print("✅ Дайджест отправлен в Telegram!")
    else:
        await send_telegram_message("📭 Сегодня нет новых вакансий и новостей")
        print("📭 Ничего нового")

if __name__ == "__main__":
    asyncio.run(main())