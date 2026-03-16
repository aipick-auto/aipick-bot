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
    
    # 2. 구글 시트 연결
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 파일 열기
        doc = client.open("AIPICK_Database")
        # ★핵심수정: 이름을 따지지 않고 '첫 번째 탭'을 무조건 선택합니다.
        sheet = doc.get_worksheet(0) 
        print(f"1. 시트 연결 성공 (탭 이름: {sheet.title})")
    except Exception as e:
        print(f"X 시트 연결 실패: {e}")
        return

    # 3. 유튜브 데이터 수집
    all_rows = []
    # 검색어를 더 단순하게 'AI'로 변경 (가장 많이 검색됨)
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q=AI+shorts&type=video&videoDuration=short&order=viewCount&key={api_key}"
    
    try:
        print("2. 유튜브 데이터 가져오는 중...")
        response = requests.get(search_url).json()
        
        # API 에러 확인용 로그
        if "error" in response:
            print(f"X 유튜브 API 에러: {response['error']['message']}")
            return

        items = response.get('items', [])
        print(f"   - 검색 결과: {len(items)}개 발견")

        if items:
            video_ids = [item['id']['videoId'] for item in items]
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
                # 점수 계산
                score = round((likes/views*1000) + (views*0.00001), 2) if views > 0 else 0
                
                all_rows.append([
                    v_id, ch_title, "인기쇼츠", v_title, 
                    f"https://www.youtube.com/shorts/{v_id}", 
                    views, likes, score, str(datetime.date.today())
                ])
    except Exception as e:
        print(f"X 유튜브 수집 중 오류: {e}")
        return

    # 4. 시트에 쓰기
    try:
        if all_rows:
            # 점수 높은 순 정렬
            all_rows.sort(key=lambda x: x[7], reverse=True)
            
            header = ["ID", "크리에이터", "분류", "제목", "링크", "조회수", "좋아요", "점수", "날짜"]
            
            # 시트 싹 비우기
            sheet.clear()
            
            # 데이터 넣기
            data_to_update = [header] + all_rows
            sheet.update(data_to_update, 'A1')
            print(f"3. 완료: {len(all_rows)}개의 데이터를 시트에 적었습니다!")
        else:
            print("X 수집된 데이터가 0개입니다.")
    except Exception as e:
        print(f"X 시트 기록 중 오류: {e}")

if __name__ == "__main__":
    run()
