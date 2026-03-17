
import os
import json
import datetime
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    print("===== 진짜 시트 찾아가기 시스템 가동 =====")
    
    # 1. 환경변수 확인
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")
    
    # 2. 구글 시트 연결 (ID로 직통 연결)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # ★주인님이 주신 바로 그 시트 ID입니다!
        SHEET_ID = "1wA8CMPzVmkG9f9Aew9ZwON6VFfCM8TZBmpQ6JXpY8fs"
        doc = client.open_by_key(SHEET_ID)
        sheet = doc.get_worksheet(0) # 첫 번째 탭 선택
        print(f"1. 연결 성공: {doc.title} ({sheet.title} 탭)")
    except Exception as e:
        print(f"X 시트 연결 실패 (공유 설정을 확인하세요): {e}")
        return

    # 3. 유튜브 데이터 수집 (100개 목표)
    all_rows = []
    next_page_token = ""
    print("2. 유튜브 데이터 100개 수집 시작...")

    for i in range(2): # 50개씩 2번 = 100개
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'maxResults': 50,
            'q': 'AI shorts',
            'type': 'video',
            'videoDuration': 'short',
            'order': 'viewCount',
            'key': api_key,
            'pageToken': next_page_token
        }
        
        response = requests.get(search_url, params=params).json()
        items = response.get('items', [])
        
        if not items: break

        video_ids = [item['id']['videoId'] for item in items]
        ids_str = ",".join(video_ids)
        
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
            # 점수 계산 (반응률 기반)
            score = round((likes/views*1000) + (views*0.00001), 2) if views > 0 else 0
            
            all_rows.append([v_id, ch_title, "AI인기쇼츠", v_title, f"https://www.youtube.com/shorts/{v_id}", views, likes, score, str(datetime.date.today())])
            
        next_page_token = response.get('nextPageToken')
        if not next_page_token: break
        print(f"   - {len(all_rows)}개 수집 중...")

    # 4. 시트에 데이터 쓰기
    try:
        if all_rows:
            all_rows.sort(key=lambda x: x[7], reverse=True)
            header = ["ID", "크리에이터", "분류", "제목", "링크", "조회수", "좋아요", "점수", "날짜"]
            sheet.clear()
            sheet.update([header] + all_rows, 'A1')
            print(f"3. 완료: 총 {len(all_rows)}개의 데이터를 진짜 시트에 적었습니다!")
        else:
            print("X 유튜브에서 가져온 데이터가 없습니다.")
    except Exception as e:
        print(f"X 시트 기록 실패: {e}")

if __name__ == "__main__":
    run()
