import os
import json
import datetime
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    print("===== 시스템 가동 =====")
    
    # 1. 환경변수 확인
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")
    
    # API 키가 제대로 로드되었는지 확인
    if not api_key:
        print("X 에러: YOUTUBE_API_KEY가 비어있습니다. GitHub Secrets 설정을 확인하세요.")
        return
    else:
        # 보안을 위해 앞글자만 출력해서 확인
        print(f"1. API 키 확인 완료 (앞글자: {api_key[:5]}...)")

    # 2. 구글 시트 연결
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        doc = client.open("AIPICK_Database")
        sheet = doc.get_worksheet(0) # 첫 번째 탭
        print(f"2. 시트 연결 성공 (탭 이름: {sheet.title})")
    except Exception as e:
        print(f"X 시트 연결 실패: {e}")
        return

    # 3. 유튜브 데이터 수집
    all_rows = []
    # 주소에 직접 API 키를 넣는 방식
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'maxResults': 50,
        'q': 'AI shorts',
        'type': 'video',
        'videoDuration': 'short',
        'order': 'viewCount',
        'key': api_key
    }
    
    try:
        print("3. 유튜브 데이터 요청 중...")
        response = requests.get(search_url, params=params).json()
        
        if "error" in response:
            print(f"X 유튜브 API 에러 발생: {response['error']['message']}")
            return

        items = response.get('items', [])
        print(f"   - 검색 결과: {len(items)}개 발견")

        if items:
            video_ids = [item['id']['videoId'] for item in items]
            ids_str = ",".join(video_ids)
            
            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                'part': 'statistics,snippet',
                'id': ids_str,
                'key': api_key
            }
            stats_res = requests.get(stats_url, params=stats_params).json()
            
            for video in stats_res.get('items', []):
                v_id = video['id']
                v_title = video['snippet']['title']
                ch_title = video['snippet']['channelTitle']
                stats = video['statistics']
                
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                score = round((likes/views*1000) + (views*0.00001), 2) if views > 0 else 0
                
                all_rows.append([
                    v_id, ch_title, "인기쇼츠", v_title, 
                    f"https://www.youtube.com/shorts/{v_id}", 
                    views, likes, score, str(datetime.date.today())
                ])
    except Exception as e:
        print(f"X 유튜브 데이터 수집 중 오류: {e}")
        return

    # 4. 시트에 쓰기
    try:
        if all_rows:
            all_rows.sort(key=lambda x: x[7], reverse=True)
            header = ["ID", "크리에이터", "분류", "제목", "링크", "조회수", "좋아요", "점수", "날짜"]
            sheet.clear()
            sheet.update([header] + all_rows, 'A1')
            print(f"4. 완료: {len(all_rows)}개의 데이터를 시트에 적었습니다!")
        else:
            print("X 수집된 데이터가 0개입니다.")
    except Exception as e:
        print(f"X 시트 기록 중 오류: {e}")

if __name__ == "__main__":
    run()
