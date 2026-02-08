import os
import requests
import datetime
# 🛠️ 옛날 방식(import google.generativeai)을 지우고 이 방식으로 바꿔야 합니다!
from google import genai

# 금고(Secrets)에서 비밀번호 가져오기
NAVER_CLIENT_ID = os.environ['NAVER_CLIENT_ID']
NAVER_CLIENT_SECRET = os.environ['NAVER_CLIENT_SECRET']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')

# 2. [수정 포인트] genai.configure 대신 바로 Client를 생성합니다.
client = genai.Client(api_key=GEMINI_API_KEY)

# --- [1. 국내 뉴스 (네이버)] ---
def get_naver_news(query):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    res = requests.get(url, headers=headers)
    return res.json().get('items', [])

# --- [2. 해외 뉴스 (NewsAPI)] --- 🛠️ 새로 추가된 함수
def get_overseas_news(query):
    # 어제 날짜 구하기
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'from': yesterday,
        'language': 'en',      # 영어 뉴스만
        'sortBy': 'relevancy', # 관련성 높은 순
        'pageSize': 5,         # 5개만
        'apiKey': NEWSAPI_KEY
    }
    res = requests.get(url, params=params)
    articles = res.json().get('articles', [])
    return [f"[해외] {a['title']}\n링크: {a['url']}" for a in articles]

def main():
    print("🌍 국내 및 해외 뉴스를 동시에 수집 중...")
    
    # 관심 키워드 설정
    ko_keywords = ["국내 경제", "2차전지", "AI", "빅테크","주식"]
    en_keywords = ["Global Economy", "AI Technology", "EV Battery", "Stock"]
    
    total_context = ""

    # 국내 뉴스 수집
    for kw in ko_keywords:
        items = get_naver_news(kw)
        for i in items[:3]:
            title = i['title'].replace('<b>','').replace('</b>','')
            total_context += f"국내뉴스: {title}\n링크: {i['link']}\n\n"

    # 해외 뉴스 수집
    for kw in en_keywords:
        items = get_overseas_news(kw)
        total_context += "\n".join(items) + "\n\n"

    if not total_context:
        print("수집된 뉴스가 없습니다.")
        return

    # --- [4. Gemini 요약 명령서 (링크 유지 요청)] ---
    prompt = f"""
    아래 뉴스 리스트는 어제 발생한 국내외 경제, AI, 2차전지 뉴스입니다.
    
    [지시 사항]
    1. 국내/해외를 구분해서 가장 중요한 소식 위주로 카테고리화 해
       #영문 뉴스는 반드시 한국어로 번역해서 요약해.
    2. 카테고리 별 핵심적인 뉴스 2~3개를 선정해줘.
       #무조건 2개 이상
    3. 핵심 내용을 2줄 이내로 요약해줘.
    4. 중요도가 높은 뉴스는 맨 앞에 배치하고, 각 요약 끝에 간단한 인사이트 및 투자포인트를 포함해줘
    5. 각 요약된 뉴스 바로 아래에 제공된 해당 뉴스의 원본 링크를 반드시 포함해줘.
    6. 가독성 좋게 기호와 아이콘을 넣어 글을 구성해.

    
    뉴스 리스트:
    {total_news_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        summary_text = response.text
        
        # --- [5. 텔레그램 전송] ---
        send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # 링크 클릭이 잘 되도록 설정
        payload = {
            "chat_id": CHAT_ID,
            "text": f"📅 링크가 포함된 어제자 뉴스 브리핑\n\n{summary_text}",
            "disable_web_page_preview": False  # 링크 미리보기를 보여줄지 선택 (True면 안보임)
        }
        requests.post(send_url, json=payload)
        print("✨ 링크 포함 전송 완료! 텔레그램을 확인해보세요.")
        
    except Exception as e:
        print(f"❗ 오류 발생: {e}")

if __name__ == "__main__":
    main()
