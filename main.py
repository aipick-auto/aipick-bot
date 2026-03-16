import os
import json
import datetime
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    print("===== 100개 수집 시스템 가동 =====")
    
    # 1. 환경변수 확인
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")
    
    # 2. 구글 시트 연결
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        doc = client.open("AIPICK_Database")
        sheet = doc.get_worksheet(0) # 첫 번째 탭
        print(f"1. 시트 연결 성공: {sheet.title}")
    except Exception as e:
        print(f"X 시트 연결 실패: {e}")
        return

    # 3. 유튜브 데이터 수집 (2페이지, 총 100개)
    all_rows = []
    next_page_token = ""
    print("2. 유튜브 데이터 100개 수집 시작...")

    for i in range(2): # 50개씩 2번 수행
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'maxResults': 50,
            'q': 'AI shorts',
            'type': 'video',
            'videoDuration': 'short',
            'order': 'viewCount',
            'key': api_key,
            'pageToken': next_page_token # 다음 페이지를 가져오는 열쇠
        }
        
        response = requests.get(search_url, params=params).json()
        items = response.get('items', [])
        
        if not items:
            break

        video_ids = [item['id']['videoId'] for item in items]
        ids_str = ",".join(video_ids)
        
        # 상세 통계 가져오기
        stats_url = "https://www.googleapis.com/youtube/v3/videos"
        stats_params = {'part': 'statistics,snippet', 'id': ids_str, 'key': api_key}
        stats_res = requests.get(stats_url, params=stats_params).json()
        
        for video in stats_res.get('items', []):
            v_id = video['id']
            v_title = video['snippet']['title']
            ch_title = video['snippet']['channelTitle']
            stats = video['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            # 점수 계산 (반응률 + 조회수 가중치)
            score = round((likes/views*1000) + (views*0.00001), 2) if views > 0 else 0
            
            all_rows.append([
                v_id, ch_title, "AI인기쇼츠", v_title, 
                f"https://www.youtube.com/shorts/{v_id}", 
                views, likes, score, str(datetime.date.today())
            ])
            
        # 다음 페이지 토큰 저장
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
        print(f"   - {len(all_rows)}개 수집 중...")

    # 4. 시트에 데이터 쓰기
    try:
        if all_rows:
            # 점수 높은 순 정렬
            all_rows.sort(key=lambda x: x[7], reverse=True)
            header = ["ID", "크리에이터", "분류", "제목", "링크", "조회수", "좋아요", "점수", "날짜"]
            sheet.clear()
            sheet.update([header] + all_rows, 'A1')
            print(f"3. 완료: 총 {len(all_rows)}개의 데이터를 시트에 적었습니다!")
        else:
            print("X 수집된 데이터가 없습니다.")
    except Exception as e:
        print(f"X 시트 기록 실패: {e}")

if __name__ == "__main__":
    run()
