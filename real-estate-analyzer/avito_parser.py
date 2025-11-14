from bs4 import BeautifulSoup
import re
import pandas as pd

def extract_price(text):
    """Ищем число ЛЮБОГО формата перед ₽"""
    match = re.search(r'([\d\xa0\s]+)\s*₽', text)
    if match:
        # Убираем ВСЕ не-цифры
        digits = re.sub(r'[^\d]', '', match.group(1))
        return int(digits) if digits else None
    return None

def parse_avito_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
   
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        price_tags = soup.find_all('p', class_='stylesMarningNormal-module-paragraph-m-dense-mYuSK')
        
        for tag in price_tags:
            if '₽' in tag.text and 'м²' in tag.text:
                price = extract_price(tag.text)
                if price:
                    prices.append(price)
        
        print(f"Файл {file_path}: {len(prices)} цен")
        return prices
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# Обрабатываем ВСЕ файлы
all_prices = []
for i in range(1, 11):
    file_path = f"E:/pars_avito/saved_avito{i}.html"
    prices = parse_avito_file(file_path)
    all_prices.extend(prices)

# Статистика
if all_prices:
    prices_series = pd.Series(all_prices)
    print(f"\n📊 ВСЕГО: {len(all_prices)} цен")
    print(f"📈 МЕДИАНА: {prices_series.median():,.0f} ₽/м²")
    
    # Сохраняем
    pd.DataFrame({'price_per_m2': all_prices}).to_csv('avito_results.csv', index=False)
    print("💾 Данные сохранены в avito_results.csv")
else:
    print("❌ Данные не найдены")
