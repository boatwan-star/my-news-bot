import os
import requests
import datetime
import google.generativeai as genai

# 금고(Secrets)에서 비밀번호 가져오기
NAVER_CLIENT_ID = os.environ['NAVER_CLIENT_ID']
NAVER_CLIENT_SECRET = os.environ['NAVER_CLIENT_SECRET']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

def get_naver_news(query):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=50&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    response = requests.get(url, headers=headers)
    return response.json().get('items', [])

def filter_yesterday_news(items):
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d %b %Y")
    filtered = []
    for item in items:
        if yesterday in item['pubDate']:
            clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            clean_desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            filtered.append(f"제목: {clean_title}\n요약: {clean_desc}\n링크: {item['link']}\n")
    return filtered

def main():
    keywords = ["국내외 경제", "AI 빅테크 신기술", "2차전지 산업"]
    total_news_text = ""
    for kw in keywords:
        raw_news = get_naver_news(kw)
        yesterday_news = filter_yesterday_news(raw_news)
        if yesterday_news:
            total_news_text += f"### {kw} ###\n" + "\n".join(yesterday_news[:10]) + "\n\n"

    if not total_news_text:
        return

    prompt = f"아래 뉴스를 카테고리별로 3줄 요약하고 바로 밑에 링크를 붙여줘:\n{total_news_text}"
    response = model.generate_content(prompt)
    
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(send_url, json={"chat_id": CHAT_ID, "text": f"📅 뉴스 브리핑\n\n{response.text}"})

if __name__ == "__main__":
    main()
