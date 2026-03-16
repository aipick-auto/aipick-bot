import os
import json
import datetime
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

def run():
    print("--- 실시간 데이터 수집 시작 ---")
    
    # 1. 환경변수 확인
    api_key = os.environ.get("YOUTUBE_API_KEY")
    json_creds = os.environ.get("GOOGLE_SHEETS_JSON")
    
    if not api_key or not json_creds:
        print("에러: 비밀번호(Secrets) 설정이 누락되었습니다.")
        return

    # 2. 구글 시트 연결
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 시트 이름과 탭 이름 확인 필수!
        spreadsheet = client.open("AIPICK_Database")
        sheet = spreadsheet.worksheet("Content")
        print("구글 시트 연결 성공")
    except Exception as e:
        print(f"에러: 구글 시트 연결 실패 ({e})")
        return

    # 3. 유튜브 데이터 수집 (인기 쇼츠 100개 목표)
    all_rows = []
    next_page_token = ""
    search_query = "AI shorts #shorts" # 가장 결과가 많이 나오는 검색어

    print(f"유튜브 검색어: {search_query}")

    for i in range(2): # 50개씩 2번 = 최대 100개
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&q={search_query}&type=video&videoDuration=short&order=viewCount&key={api_key}&pageToken={next_page_token}"
        
        response = requests.get(url).json()
        items = response.get('items', [])
        
        print(f"{i+1}차 검색 결과: {len(items)}개 발견")
        
        if not items:
            break
            
        video_ids = [item['id']['videoId'] for item in items]
        ids_str = ",".join(video_ids)
        
        # 상세 통계(조회수, 좋아요) 수집
        stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={ids_str}&key={api_key}"
        stats_res = requests.get(stats_url).json()
        
        for video in stats_res.get('items', []):
            v_id = video['id']
            v_title = video['snippet']['title']
            ch_title = video['snippet']['channelTitle']
            stats = video['statistics']
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            
            # 랭킹 점수 계산 (조회수 + 반응률)
            engagement = (likes / views * 1000) if views > 0 else 0
            score = round(engagement + (views * 0.00001), 2)
            
            all_rows.append([
                v_id, ch_title, "AI쇼츠", v_title, 
                f"https://www.youtube.com/shorts/{v_id}", 
                views, likes, score, str(datetime.date.today())
            ])
            
        next_page_token = response.get('nextPageToken', "")
        if not next_page_token:
            break

    # 4. 데이터 정렬 및 시트 업데이트
    if all_rows:
        # 점수 순으로 내림차순 정렬
        all_rows.sort(key=lambda x: x[7], reverse=True)
        
        header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "rank_score", "created_at"]
        
        # 시트 비우고 새로 쓰기
        sheet.clear()
        sheet.update('A1', [header] + all_rows)
        print(f"업데이트 완료: 총 {len(all_rows)}개의 데이터를 기록했습니다.")
    else:
        print("검색 결과가 없어 업데이트를 중단합니다.")

if __name__ == "__main__":
    run()
