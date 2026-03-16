import os, json, datetime, gspread, requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    # 1. 환경변수 로드
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")

    # 2. 구글 시트 연결 (이 부분은 기존 방식대로 유지)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(json_creds)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("AIPICK_Database").worksheet("Content")

    # 3. 유튜브 데이터 수집 (requests 라이브러리 사용하여 인증 에러 방지)
    all_rows = []
    next_page_token = ""
    
    print("인기 쇼츠 100개 수집 시작...")

    for _ in range(2): # 50개씩 2번 = 100개
        # 검색 API 호출
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q=%23shorts&type=video&videoDuration=short&order=viewCount&key={api_key}&pageToken={next_page_token}"
        search_res = requests.get(search_url).json()
        
        items = search_res.get('items', [])
        if not items: break
        
        video_ids = [item['id']['videoId'] for item in items]
        
        # 상세 통계 API 호출
        ids_str = ",".join(video_ids)
        stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={ids_str}&key={api_key}"
        stats_res = requests.get(stats_url).json()
        
        for video in stats_res.get('items', []):
            v_id = video['id']
            v_title = video['snippet']['title']
            ch_title = video['snippet']['channelTitle']
            stats = video['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            
            # 랭킹 점수 계산
            engagement = (likes / views * 1000) if views > 0 else 0
            score = round(engagement + (views * 0.00001), 2)
            
            all_rows.append([
                v_id, ch_title, "인기쇼츠", v_title, 
                f"https://www.youtube.com/shorts/{v_id}", views, likes, score, str(datetime.date.today())
            ])
            
        next_page_token = search_res.get('nextPageToken', "")
        if not next_page_token: break

    # 4. 상위 100개 정렬 및 저장
    all_rows.sort(key=lambda x: x[7], reverse=True)
    final_rows = all_rows[:100]

    # 5. 구글 시트 업데이트
    header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "rank_score", "created_at"]
    sheet.clear()
    sheet.update(values=[header] + final_rows, range_name='A1')
    
    print(f"성공: 총 {len(final_rows)}개의 인기 쇼츠 데이터를 업데이트했습니다!")

if __name__ == "__main__":
    run()
