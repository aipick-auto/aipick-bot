import os
import json
import datetime
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    print("===== 작업 시작 =====")
    
    # 1. 환경변수 읽기
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")
    
    # 2. 구글 시트 연결
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 시트 열기
        doc = client.open("AIPICK_Database")
        # ★중요: 시트 하단 탭 이름이 반드시 'Content'여야 합니다.
        sheet = doc.worksheet("Content")
        print("1. 구글 시트 연결 성공")
    except Exception as e:
        print(f"X 구글 시트 연결 실패: {e}")
        return

    # 3. 유튜브 데이터 수집 (가장 확실한 'requests' 방식)
    all_rows = []
    # 검색어는 가장 대중적인 'shorts'로 설정
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q=shorts&type=video&videoDuration=short&order=viewCount&key={api_key}"
    
    try:
        print("2. 유튜브 검색 시작...")
        response = requests.get(search_url).json()
        items = response.get('items', [])
        print(f"   - 검색 결과: {len(items)}개 발견")

        if items:
            video_ids = [item['id']['videoId'] for item in items]
            ids_str = ",".join(video_ids)
            
            # 상세 정보(조회수) 가져오기
            stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={ids_str}&key={api_key}"
            stats_res = requests.get(stats_url).json()
            
            for video in stats_res.get('items', []):
                v_id = video['id']
                v_title = video['snippet']['title']
                ch_title = video['snippet']['channelTitle']
                stats = video['statistics']
                
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                # 점수 계산
                score = round((likes/views*1000) + (views*0.00001), 2) if views > 0 else 0
                
                all_rows.append([
                    v_id, ch_title, "인기쇼츠", v_title, 
                    f"https://www.youtube.com/shorts/{v_id}", 
                    views, likes, score, str(datetime.date.today())
                ])
    except Exception as e:
        print(f"X 유튜브 수집 실패: {e}")
        return

    # 4. 시트에 데이터 쓰기
    try:
        if all_rows:
            # 점수 높은 순 정렬
            all_rows.sort(key=lambda x: x[7], reverse=True)
            
            header = ["ID", "크리에이터", "분류", "제목", "링크", "조회수", "좋아요", "점수", "날짜"]
            
            # 시트 비우기
            sheet.clear()
            # 데이터 넣기 (리스트의 리스트 형태로 업데이트)
            data_to_update = [header] + all_rows
            sheet.update('A1', data_to_update)
            print(f"3. 성공: {len(all_rows)}개의 데이터를 시트에 기록했습니다!")
        else:
            print("X 수집된 데이터가 없습니다.")
    except Exception as e:
        print(f"X 시트 기록 실패: {e}")

if __name__ == "__main__":
    run()
