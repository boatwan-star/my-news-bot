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

# 🛠️ [중요 수정] Gemini 로봇 설정 (404 오류 방지)
genai.configure(api_key=GEMINI_API_KEY)
# 'models/'를 붙여서 이름을 아주 정확하게 알려줍니다.
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- [1. 네이버 뉴스 수집 함수] ---
def get_naver_news(query):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=50&sort=date"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    response = requests.get(url, headers=headers)
    return response.json().get('items', [])

# --- [2. 어제 뉴스만 필터링 (링크 포함 버전)] ---
def filter_yesterday_news(items):
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d %b %Y")
    filtered = []
    for item in items:
        if yesterday in item['pubDate']:
            clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            clean_desc = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            # 🔗 여기에 '링크' 정보를 추가해서 저장합니다.
            filtered.append(f"제목: {clean_title}\n요약: {clean_desc}\n링크: {item['link']}\n")
    return filtered

# --- [3. 메인 로직] ---
def main():
    print("🤖 뉴스와 링크를 수집하여 요약 중입니다...")
    keywords = ["국내 경제","세계 경제", "빅테크 신기술", "2차전지", "AI"]
    total_news_text = ""

    for kw in keywords:
        raw_news = get_naver_news(kw)
        yesterday_news = filter_yesterday_news(raw_news)
        
        if yesterday_news:
            total_news_text += f"### {kw} 카테고리 ###\n" + "\n".join(yesterday_news[:10]) + "\n\n"

    if not total_news_text:
        print("❌ 어제 발행된 뉴스가 없습니다.")
        return

    # --- [4. Gemini 요약 명령서 (링크 유지 요청)] ---
    prompt = f"""
    아래 뉴스 리스트는 어제 발생한 국내외 경제, AI, 2차전지 뉴스입니다.
    
    [지시 사항]
    1. 각 카테고리별로 핵심 뉴스 2~3개를 선정해줘.
    2. 핵심 내용을 2줄 이내로 요약해줘.
    3. 중요도가 높은 뉴스는 맨 앞에 배치하고, 각 요약 끝에 간단한 인사이트 및 투자포인트를 포함해줘
    4. 각 요약된 뉴스 바로 아래에 제공된 해당 뉴스의 원본 링크를 반드시 포함해줘.
    5. 가독성 좋게 기호와 아이콘을 넣어 글을 구성해.
    
    뉴스 리스트:
    {total_news_text}
    """
    
    try:
        response = model.generate_content(prompt)
        summary = response.text

        # --- [5. 텔레그램 전송] ---
        send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # 링크 클릭이 잘 되도록 설정
        payload = {
            "chat_id": CHAT_ID,
            "text": f"📅 링크가 포함된 어제자 뉴스 브리핑\n\n{summary}",
            "disable_web_page_preview": False  # 링크 미리보기를 보여줄지 선택 (True면 안보임)
        }
        requests.post(send_url, json=payload)
        print("✨ 링크 포함 전송 완료! 텔레그램을 확인해보세요.")
        
    except Exception as e:
        print(f"❗ 오류 발생: {e}")

if __name__ == "__main__":
    main()
