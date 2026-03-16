import os, json, datetime, googleapiclient.discovery, gspread
from oauth2client.service_account import ServiceAccountCredentials

def run():
    YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
    creds_dict = json.loads(os.environ["GOOGLE_SHEETS_JSON"])
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("AIPICK_Database").worksheet("Content")

    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    # 검색어를 더 넓게 변경: "AI shorts" 또는 "AI 숏폼" 관련 영상 20개 찾기
    search_res = youtube.search().list(
        q="AI shorts #AIanimation #KlingAI", 
        part="snippet", maxResults=20, type="video", videoDuration="short", order="viewCount"
    ).execute()

    rows = []
    for item in search_res['items']:
        v_id = item['id']['videoId']
        v_title = item['snippet']['title']
        ch_title = item['snippet']['channelTitle']
        
        # 상세 통계 가져오기
        try:
            stats_res = youtube.videos().list(part="statistics", id=v_id).execute()
            stats = stats_res['items'][0]['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            
            # 랭킹 점수 계산
            score = round((likes/views*1000) + (views*0.0001), 2) if views > 0 else 0
            
            rows.append([v_id, ch_title, "숏폼", v_title, 
                         f"https://www.youtube.com/shorts/{v_id}", views, likes, score, str(datetime.date.today())])
        except:
            continue

    header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "ai_score", "created_at"]
    
    # 시트 초기화 후 데이터 넣기
    sheet.clear()
    sheet.update('A1', [header] + rows)
    print(f"{len(rows)}개의 데이터를 업데이트했습니다!")

if __name__ == "__main__":
    run()
