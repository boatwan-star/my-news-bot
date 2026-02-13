import os
import requests
import datetime
from google import genai

# 금고(Secrets)에서 비밀번호 가져오기 (없으면 None 반환하여 에러 방지)
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')

# 클라이언트 생성
client = genai.Client(api_key=GEMINI_API_KEY)

# --- [1. 국내 뉴스 (네이버)] ---
def get_naver_news(query):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("⚠️ 네이버 API 키가 없습니다.")
        return []
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    try:
        res = requests.get(url, headers=headers)
        return res.json().get('items', [])
    except Exception as e:
        print(f"네이버 뉴스 수집 중 에러: {e}")
        return []

# --- [2. 해외 뉴스 (NewsAPI)] ---
def get_overseas_news(query):
    if not NEWSAPI_KEY:
        print("⚠️ NewsAPI 키가 설정되지 않았습니다.")
        return []
        
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'from': yesterday,
        'language': 'en',
        'sortBy': 'relevancy',
        'pageSize': 3,  # 개수를 줄여서 오류 가능성을 낮춤
        'apiKey': NEWSAPI_KEY
    }
    try:
        res = requests.get(url, params=params)
        articles = res.json().get('articles', [])
        return [f"[해외] {a['title']}\n링크: {a['url']}" for a in articles]
    except Exception as e:
        print(f"해외 뉴스 수집 중 에러: {e}")
        return []

# 🛠️ 메시지가 길면 나눠서 보내는 함수
def send_long_telegram_message(text):
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # 텔레그램 제한인 4000자보다 넉넉하게 3500자씩 끊어서 전송
    max_length = 3000
    
    for i in range(0, len(text), max_length):
        part = text[i:i+max_length]
        payload = {
            "chat_id": CHAT_ID,
            "text": part,
            "disable_web_page_preview": False
        }
        res = requests.post(base_url, json=payload)
        if res.status_code != 200:
            print(f"❌ 전송 실패: {res.text}")
        else:
            print(f"✅ 메시지 파트 전송 성공!")


def main():
    print("🌍 뉴스 수집 및 요약 시작...")
    
    ko_keywords = ["경제", "2차전지", "AI", "빅테크"]
    en_keywords = ["Global Economy", "AI Technology", "EV Battery"]
    
    total_context = ""

    # 국내 뉴스 수집
    for kw in ko_keywords:
        items = get_naver_news(kw)
        for i in items[:3]:
            title = i['title'].replace('<b>','').replace('</b>','').replace('&quot;', '"')
            total_context += f"국내뉴스: {title}\n링크: {i['link']}\n\n"

    # 해외 뉴스 수집
    for kw in en_keywords:
        items = get_overseas_news(kw)
        if items:
            total_context += "\n".join(items) + "\n\n"

    if not total_context:
        print("❌ 수집된 뉴스가 없습니다. (API 키나 검색어를 확인하세요)")
        return

    # Gemini 요약 명령
    prompt = f"""
    아래 뉴스 리스트는 어제 발생한 국내외 경제, AI, 2차전지 뉴스입니다.
    
       [지시 사항]
    1. 국내/해외 뉴스 중 가장 중요한 소식 위주로 경제, AI, 2차전지에 대한 카테고리
       #영문 뉴스는 반드시 한국어로 번역해서 요약해.
    2. 카테고리 별 핵심적인 뉴스 2~3개를 선정해줘.
    3. 핵심 내용을 1~2줄 이내로 요약해줘.
    4. 중요도가 높은 뉴스는 맨 앞에 배치하고, 각 요약 끝에 간단한 인사이트 및 투자 포인트를 포함해줘
    5. 각 요약된 뉴스 바로 아래에 제공된 해당 뉴스의 원본 링크를 반드시 포함해줘.
    6. 가독성 좋게 기호와 아이콘을 넣어 글을 구성해.
    
    뉴스 리스트:
    {total_context}
    """
    
    try:
        # 🛠️ 안전한 2.0 모델 사용 (2.5가 안 될 경우를 대비)
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        summary_text = response.text
        
        # --- [5. 텔레그램 전송 (디버깅 강화)] ---
        send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": f"📅 뉴스 브리핑\n\n{summary_text}",
            "disable_web_page_preview": False
        }
        
        # 📨 실제 전송 결과 확인
        res = requests.post(send_url, json=payload)
        
        if res.status_code == 200:
            print("✨ [성공] 텔레그램 메시지가 정상적으로 전송되었습니다!")
        else:
            print(f"❌ [실패] 텔레그램 전송 실패!")
            print(f"에러 코드: {res.status_code}")
            print(f"에러 메시지: {res.text}") # 텔레그램이 보낸 거절 사유 출력
            
    except Exception as e:
        print(f"❗ 프로그램 실행 중 치명적인 오류 발생: {e}")

if __name__ == "__main__":
    main()
