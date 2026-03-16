import os, json, datetime, googleapiclient.discovery, gspread
from oauth2client.service_account import ServiceAccountCredentials

def run():
    # 1. 환경변수 로드
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")

    if not YOUTUBE_API_KEY:
        print("에러: YOUTUBE_API_KEY가 설정되지 않았습니다.")
        return

    # 2. 구글 시트 연결 (기존과 동일)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("AIPICK_Database").worksheet("Content")
    except Exception as e:
        print(f"구글 시트 인증 에러: {e}")
        return

    # 3. 유튜브 데이터 수집 (★핵심 수정: credentials=None 추가)
    try:
        # 이 부분이 인증 에러를 방지하는 가장 확실한 방법입니다.
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", 
            developerKey=YOUTUBE_API_KEY,
            credentials=None  # 자격 증명 확인을 건너뛰고 API 키만 사용하도록 강제
        )
        
        search_res = youtube.search().list(
            q="AI shorts", 
            part="snippet", 
            maxResults=50, 
            type="video", 
            videoDuration="short", 
            order="viewCount"
        ).execute()

        rows = []
        for item in search_res.get('items', []):
            v_id = item['id']['videoId']
            v_title = item['snippet']['title']
            ch_title = item['snippet']['channelTitle']
            
            # 영상 상세 통계
            stats_res = youtube.videos().list(part="statistics", id=v_id).execute()
            if not stats_res['items']: continue
            
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
        print(f"성공: {len(rows)}개의 데이터를 시트에 저장했습니다.")

    except Exception as e:
        print(f"유튜브 API 실행 중 에러: {e}")

if __name__ == "__main__":
    run()
