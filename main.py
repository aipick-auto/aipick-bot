import os, json, datetime, googleapiclient.discovery, gspread
from oauth2client.service_account import ServiceAccountCredentials

def run():
    # 1. 인증 정보 로드
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")

    # 2. 구글 시트 연결
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(json_creds)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("AIPICK_Database").worksheet("Content")

    # 3. 유튜브 데이터 수집 (100개 수집 로직)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY, credentials=None)
    
    all_rows = []
    next_page_token = None
    
    print("전체 인기 쇼츠 100개 수집 시작...")

    # 50개씩 2번 요청하여 총 100개를 가져옵니다.
    for i in range(2):
        search_res = youtube.search().list(
            q="#shorts",  # 전 세계 쇼츠 공통 태그
            part="snippet", 
            maxResults=50, 
            type="video", 
            videoDuration="short", 
            order="viewCount", # 조회수 높은 순
            pageToken=next_page_token
        ).execute()

        items = search_res.get('items', [])
        video_ids = [item['id']['videoId'] for item in items]

        # 영상들의 상세 통계(조회수, 좋아요) 한꺼번에 가져오기
        stats_res = youtube.videos().list(
            part="statistics,snippet", 
            id=",".join(video_ids)
        ).execute()

        for video in stats_res.get('items', []):
            v_id = video['id']
            v_title = video['snippet']['title']
            ch_title = video['snippet']['channelTitle']
            stats = video['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            
            # 랭킹 점수 계산 (조회수 + 참여도 가중치)
            # 조회수만 높으면 스팸일 수 있어 좋아요 비율을 섞습니다.
            engagement = (likes / views * 1000) if views > 0 else 0
            score = round(engagement + (views * 0.00001), 2)
            
            all_rows.append([
                v_id, 
                ch_title, 
                "인기쇼츠", 
                v_title, 
                f"https://www.youtube.com/shorts/{v_id}", 
                views, 
                likes, 
                score, 
                str(datetime.date.today())
            ])

        next_page_token = search_res.get('nextPageToken')
        if not next_page_token: break

    # 4. 점수 높은 순으로 정렬 (상위 100개)
    all_rows.sort(key=lambda x: x[7], reverse=True)
    final_rows = all_rows[:100]

    # 5. 시트 업데이트
    header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "rank_score", "created_at"]
    sheet.clear()
    sheet.update(values=[header] + final_rows, range_name='A1')
    
    print(f"성공: 총 {len(final_rows)}개의 인기 쇼츠 데이터를 업데이트했습니다!")

if __name__ == "__main__":
    run()
