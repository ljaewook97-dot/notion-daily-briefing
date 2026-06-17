import os, smtplib, google.generativeai as genai
from datetime import date
from notion_client import Client
from email.mime.text import MIMEText

# 설정
notion = Client(auth=os.environ["NOTION_TOKEN"])
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini = genai.GenerativeModel("gemini-1.5-flash")
DB_ID = os.environ["NOTION_DB_ID"]
today = date.today().isoformat()

# 노션에서 오늘 마감 일정 가져오기
response = notion.databases.query(
    database_id=DB_ID,
    filter={
        "and": [
            {"property": "마감일", "date": {"equals": today}},
            {"property": "완료", "checkbox": {"equals": False}}
        ]
    }
)

items = []
for page in response["results"]:
    title = page["properties"]["이름"]["title"]
    if title:
        name = title[0]["text"]["content"]
        구분 = page["properties"].get("구분", {}).get("select", {})
        구분명 = 구분.get("name", "") if 구분 else ""
        items.append(f"- {name} ({구분명})" if 구분명 else f"- {name}")

if not items:
    content = "오늘 마감인 할 일이 없어요! 😊 여유로운 하루 되세요~"
else:
    task_list = "\n".join(items)
    result = gemini.generate_content(
        f"오늘({today}) 노션 할 일 목록이야. 친근하게 간단히 정리해서 아침 브리핑처럼 알려줘:\n{task_list}"
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

print("브리핑 이메일 발송 완료!")
