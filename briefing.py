import os, smtplib, requests
from datetime import date
from google import genai
from email.mime.text import MIMEText

# 설정
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = os.environ["NOTION_DB_ID"]
today = date.today().isoformat()

# 노션 API 직접 호출 (필터 없이 전체 가져오기)
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

items = []
has_more = True
start_cursor = None

while has_more:
    payload = {"page_size": 100}
    if start_cursor:
        payload["start_cursor"] = start_cursor

    res = requests.post(
        f"https://api.notion.com/v1/databases/{DB_ID}/query",
        headers=headers,
        json=payload
    )
    data = res.json()

    for page in data.get("results", []):
        props = page["properties"]

        # 마감일 확인
        date_prop = props.get("마감일", {}).get("date")
        if not date_prop:
            continue
        deadline = date_prop.get("start", "")
        if not deadline.startswith(today):
            continue

        # 완료 여부 확인
        done = props.get("완료", {}).get("checkbox", False)
        if done:
            continue

        # 이름 추출
        title = props.get("이름", {}).get("title", [])
        if not title:
            continue
        name = title[0]["text"]["content"]

        # 구분 추출
        구분_data = props.get("구분", {}).get("select")
        구분명 = 구분_data.get("name", "") if 구분_data else ""
        items.append(f"- {name} ({구분명})" if 구분명 else f"- {name}")

    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

# Gemini로 브리핑 생성
if not items:
    content = "오늘 마감인 할 일이 없어요! 😊 여유로운 하루 되세요~"
else:
    task_list = "\n".join(items)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    result = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"오늘({today}) 노션 할 일 목록이야. 친근하게 간단히 정리해서 아침 브리핑처럼 알려줘:\n{task_list}"
    )
    content = result.text

# 이메일 발송
email_body = f"📅 오늘의 노션 일정 브리핑\n\n{content}"
mime = MIMEText(email_body, "plain", "utf-8")
mime["Subject"] = f"[노션 브리핑] {today}"
mime["From"] = os.environ["EMAIL_FROM"]
mime["To"] = os.environ["EMAIL_TO"]

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASSWORD"])
    server.send_message(mime)

print(f"브리핑 완료! 오늘 할 일 {len(items)}개")
