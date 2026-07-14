import os
import datetime
import requests
import feedparser
import hashlib
import secrets
import base64
import random

# 1. 認証情報と設定
LIVEDOOR_ID = os.environ.get("LIVEDOOR_ID")
API_KEY = os.environ.get("LIVEDOOR_KEY")
BLOG_ID = os.environ.get("BLOG_ID")

# RSSフィードの候補リスト
RSS_SOURCES = [
    {"genre": "Yahoo!主要ニュース", "url": "https://news.yahoo.co.jp/rss/topics/top-picks.xml"},
    {"genre": "Yahoo!IT・科学ニュース", "url": "https://news.yahoo.co.jp/rss/topics/it.xml"},
    {"genre": "はてなブックマーク（テクノロジー人気）", "url": "https://b.hatena.ne.jp/hotentry/it.rss"},
    {"genre": "Qiita（新着トレンド風）", "url": "https://qiita.com/popular-items.feed"},
    {"genre": "GIGAZINE（IT・ガジェット）", "url": "https://gigazine.net/news/rss_2.0/"}
]

selected_source = random.choice(RSS_SOURCES)
genre_name = selected_source["genre"]
RSS_URL = selected_source["url"]

print(f"今回の取得ジャンル: {genre_name}")
print(f"RSSフィードを取得中: {RSS_URL}")

# 2. RSSから最新5件を取得してHTMLを組み立てる
feed = feedparser.parse(RSS_URL)
content_html = f"<p>本日の「{genre_name}」から最新のトピックをお届けします。</p><ul style='line-height: 1.8;'>"
entries = feed.entries[:5] if feed.entries else []

if not entries:
    content_html += "<li>ニュースの取得に失敗したか、記事がありませんでした。</li>"
else:
    for entry in entries:
        title = entry.title
        link = entry.link
        content_html += f"<li><a href='{link}' target='_blank' rel='noopener'>{title}</a></li>"

content_html += f"</ul><p>※この記事は「{genre_name}」のRSSを元に自動生成されています。</p>"

# 3. タイトル
today_str = datetime.datetime.now().strftime("%Y年%m月%d日")
article_title = f"{today_str}の最新ニュース【{genre_name}】"

# 4. livedoorの仕様に合わせたXMLデータの組み立て
url = f"https://livedoor.blogcms.jp/atompub/{BLOG_ID}/article"

xml_data = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{article_title}</title>
  <content type="text/html"><![CDATA[{content_html}]]></content>
  <app:control>
    <app:draft>no</app:draft>
  </app:control>
</entry>
"""

# 5. WSSE認証ヘッダーの作成
def make_wsse_header(username, api_key):
    nonce = secrets.token_bytes(16)
    created = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    sha = hashlib.sha1()
    sha.update(nonce + created.encode('utf-8') + api_key.encode('utf-8'))
    digest = sha.digest()

    b64_nonce = base64.b64encode(nonce).decode('utf-8')
    b64_digest = base64.b64encode(digest).decode('utf-8')

    return f'UsernameToken Username="{username}", PasswordDigest="{b64_digest}", Nonce="{b64_nonce}", Created="{created}"'

wsse_header = make_wsse_header(LIVEDOOR_ID, API_KEY)

# 6. 投稿送信
try:
    response = requests.post(
        url,
        headers={
            "Authorization": 'WSSE profile="UsernameToken"', # 【ここを追加！】livedoorに必須の認証ヘッダー
            "X-WSSE": wsse_header,
            "Content-Type": "application/atom+xml; type=entry"
        },
        data=xml_data.encode("utf-8")
    )

    if response.status_code in [201, 200]:
        print(f"記事「{article_title}」の投稿に成功しました！")
    else:
        print(f"投稿失敗: ステータスコード {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"エラーが発生しました: {e}")
