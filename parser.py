from bs4 import BeautifulSoup
import requests
import unicodedata
import dateparser


def parse_newest_pages(stop_titles=None):
    if stop_titles is None:
        stop_titles = set()
    parsed_docs = []
    i = 1
    while True:
        print(f'page {i}\n')
        url = f'https://smart-lab.ru/news/list/page{i}/'
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        all_news = soup.find_all("div", {'class': 'inside'})
        if not all_news:
            break

        for news_entry in all_news:
            article_url = 'https://smart-lab.ru' + news_entry.find('a')['href']
            response = requests.get(article_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            title = unicodedata.normalize("NFKC", soup.find("h1").find("span").get_text(strip=True))
            if title in stop_titles:
                return parsed_docs

            content_div = soup.find("div", {'class': 'topic'}).find("div", {'class': 'content'})
            content = unicodedata.normalize("NFKC", content_div.get_text(strip=True))

            date = dateparser.parse(soup.find("li", {'class': 'date'}).get_text(strip=True))
            
            parsed_docs.append({"title": title, "content": content, "date": date})
        i += 1
    return parsed_docs  