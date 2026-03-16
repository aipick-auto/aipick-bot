import os, json, datetime, googleapiclient.discovery, gspread
from oauth2client.service_account import ServiceAccountCredentials

def run():
    # 1. 보안 비밀번호(Secrets) 로드
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")

    if not YOUTUBE_API_KEY or not json_creds:
        print("에러: API Key 또는 JSON 설정이 누락되었습니다.")
        return

    # 2. 구글 시트 연결 (서비스 계정 인증)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("AIPICK_Database").worksheet("Content")
    except Exception as e:
        print(f"구글 시트 연결 중 에러 발생: {e}")
        return

    # 3. 유튜브 데이터 수집 (API 키 인증 - static_discovery=False 추가)
    try:
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", 
            developerKey=YOUTUBE_API_KEY,
            static_discovery=False  # ← 이 부분이 인증 에러를 막는 핵심입니다
        )
        
        search_res = youtube.search().list(
            q="AI shorts #AIanimation #KlingAI", 
            part="snippet", maxResults=20, type="video", videoDuration="short", order="viewCount"
        ).execute()

        rows = []
        for item in search_res.get('items', []):
            v_id = item['id']['videoId']
            v_title = item['snippet']['title']
            ch_title = item['snippet']['channelTitle']
            
            stats_res = youtube.videos().list(part="statistics", id=v_id).execute()
            stats = stats_res['items'][0]['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            score = round((likes/views*1000) + (views*0.0001), 2) if views > 0 else 0
            
            rows.append([v_id, ch_title, "숏폼", v_title, 
                         f"https://www.youtube.com/shorts/{v_id}", views, likes, score, str(datetime.date.today())])

        # 4. 시트 업데이트
        header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "ai_score", "created_at"]
        sheet.clear()
        sheet.update('A1', [header] + rows)
        print(f"성공: {len(rows)}개의 데이터를 업데이트했습니다!")

    except Exception as e:
        print(f"유튜브 데이터 수집 중 에러 발생: {e}")

if __name__ == "__main__":
    run()
