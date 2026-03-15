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
    search_res = youtube.search().list(
        q="#AIAnimation #KlingAI #LumaAI #SoraAI", 
        part="snippet", maxResults=20, type="video", videoDuration="short", order="viewCount"
    ).execute()

    rows = []
    for item in search_res['items']:
        v_id = item['id']['videoId']
        stats = youtube.videos().list(part="statistics", id=v_id).execute()['items'][0]['statistics']
        views, likes = int(stats.get('viewCount', 0)), int(stats.get('likeCount', 0))
        score = round((likes/views*1000) + (views*0.0001), 2) if views > 0 else 0
        rows.append([v_id, item['snippet']['channelTitle'], "숏폼", item['snippet']['title'], 
                     f"https://www.youtube.com/shorts/{v_id}", views, likes, score, str(datetime.date.today())])

    header = ["content_id", "creator_id", "category", "title", "source_url", "view_count", "like_count", "ai_score", "created_at"]
    sheet.update('A1', [header] + rows)
    print("Update Complete!")

if __name__ == "__main__":
    run()
