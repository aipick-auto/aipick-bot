import os, json, datetime, googleapiclient.discovery, gspread
from oauth2client.service_account import ServiceAccountCredentials

def run():
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")

    # 1. 구글 시트 연결
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(json_creds)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("AIPICK_Database").worksheet("Content")

    # 2. 유튜브 데이터 수집 (검색어 대폭 확장)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY, static_discovery=False)
    
    # 검색어(q)를 더 포괄적으로 변경: "AI shorts" (가장 데이터가 많은 단어)
    search_res = youtube.search().list(
        q="AI shorts", 
        part="snippet", 
        maxResults=50, # 최대 50개까지 수집
        type="video", 
        videoDuration="short", 
        order="viewCount"
    ).execute()

    items = search_res.get('items', [])
    print(f"검색된 비디오 개수: {len(items)}") # 로그에서 확인용

    rows = []
    for item in items:
        v_id = item['id']['videoId']
        v_title = item['snippet']['title']
        ch_title = item['snippet']['channelTitle']
        
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

    # 3. 데이터 쓰기
    header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "ai_score", "created_at"]
    sheet.clear()
    sheet.update('A1', [header] + rows)
    print(f"최종 업데이트 완료: {len(rows)}개의 데이터가 입력되었습니다.")

if __name__ == "__main__":
    run()
