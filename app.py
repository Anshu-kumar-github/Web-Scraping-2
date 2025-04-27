import csv
import time
from datetime import datetime
from urllib.parse import urljoin

import openpyxl
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

BASE_URL = "https://www.hindustantimes.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
WAIT_TIME = 2  # seconds

def fetch_html(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching page: {e}")
        return None

def extract_article(url):
    html = fetch_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    title = soup.find('h1')
    author = soup.select_one('span[class*="author"], a[class*="author"]')
    date = soup.find('span', class_='dateTime')
    content_block = soup.find('div', class_='storyDetails')
    category_links = soup.select('ul.breadcrumb li a')

    article = {
        'Title': title.text.strip() if title else "N/A",
        'Author': author.text.strip() if author else "N/A",
        'Published Time': date.text.strip() if date else "N/A",
        'URL': url,
        'Categories': ', '.join(a.text.strip() for a in category_links[1:]) if category_links else "N/A",
        'Full Text': '\n\n'.join(p.text.strip() for p in content_block.find_all('p')) if content_block else "N/A"
    }
    return article

def save_to_csv(articles, filename):
    keys = ['Title', 'Author', 'Published Time', 'URL', 'Categories', 'Full Text']
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for article in articles:
            writer.writerow(article)
            writer.writerow({})

def save_to_txt(articles, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for idx, article in enumerate(articles, start=1):
            f.write(f"ARTICLE #{idx}\n")
            f.write("="*40 + "\n")
            for key, value in article.items():
                f.write(f"{key}:\n{value}\n\n")
            f.write("-"*80 + "\n\n")

def save_to_excel(articles, filename):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scraped Articles"

    headers = ['Title', 'Author', 'Published Time', 'URL', 'Categories', 'Full Text']
    ws.append(headers)

    for article in articles:
        row = [article.get(key, "") for key in headers]
        ws.append(row)
        ws.append(["-"*10 for _ in headers])

    wb.save(filename)

def scrape_articles(category, max_articles, file_type):
    articles = []
    page = 1

    while len(articles) < max_articles:
        if page == 1:
            url = f"{BASE_URL}/{category}/"
        else:
            url = f"{BASE_URL}/{category}/page-{page}"

        html = fetch_html(url)
        if not html:
            break

        soup = BeautifulSoup(html, 'lxml')
        links = soup.select('div[class*="cartHolder"] a')

        if not links:
            break

        for link in links:
            if len(articles) >= max_articles:
                break
            href = link.get('href')
            if not href or '/photos/' in href or '/videos/' in href:
                continue

            full_url = urljoin(BASE_URL, href)

            if any(a['URL'] == full_url for a in articles):
                continue

            article = extract_article(full_url)
            if article:
                articles.append(article)

            time.sleep(WAIT_TIME)

        page += 1
        time.sleep(WAIT_TIME)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"hindustan_times_{category}_{date_str}.{file_type}"

    if file_type == 'csv':
        save_to_csv(articles, filename)
    elif file_type == 'txt':
        save_to_txt(articles, filename)
    elif file_type == 'xlsx':
        save_to_excel(articles, filename)
    else:
        save_to_csv(articles, filename)

    return filename

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    category = request.form.get('category')
    max_articles = int(request.form.get('max_articles', 10))
    file_type = request.form.get('file_type', 'csv')

    output_file = scrape_articles(category, max_articles, file_type)

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
