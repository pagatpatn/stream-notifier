import os, time, re, threading, ssl, requests, websocket
from googleapiclient.discovery import build

# --- CONFIG ---
YOUTUBE_API_KEY   = os.getenv("AIzaSyCxNZR0fOBWFJNYmGIy70FXk4Ne7W8H2x0")
YOUTUBE_CHANNEL_ID = os.getenv("UCyIbUTzFN8fNmxRo4aG2rCg")
FACEBOOK_PAGE_ID  = os.getenv("110575327401854")
FACEBOOK_TOKEN    = os.getenv("EAAkyd2KmkFkBPI3c3ztJ3ARJLPktXcTOFOkqofL1eAvZArLiF9XoTGFojvNFzWFjpcLAv92MmWzWa8hKaAM2J68JsOXLOlmaSKNMc8xdYdf4VMZAp9AJLdDEcIsRmboDVPPNzyTCHq5m1TPZAY24Clg3AmxEPF8AV6N2GwCNgZBhlOelIyZBgZAX9gqZA9VNSqg6Ba3VGcpMPDmPvMcZAcEUf2QvTO3OJTFGGnkv")
KICK_USERNAME     = os.getenv("LastMove")
KICK_CHANNEL      = os.getenv("https://kick.com/lastmove")
NTFY_TOPIC        = os.getenv("NTFY_TOPIC", "https://ntfy.sh/streamchats123")

# --- NTFY ---
def send_ntfy(platform, user, msg):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=f"[{platform}] {user}: {msg}".encode("utf-8"),
            headers={"Title": f"New {platform} Chat", "Priority": "default"}
        )
    except Exception as e:
        print(f"⚠️ ntfy error: {e}")

# --- Worker to prevent message spam ---
import queue
ntfy_queue = queue.Queue()

def ntfy_worker():
    while True:
        platform, user, msg = ntfy_queue.get()
        send_ntfy(platform, user, msg)
        time.sleep(5)  # 5s delay between notifications

def queue_ntfy(platform, user, msg):
    ntfy_queue.put((platform, user, msg))

# --- YouTube ---
def connect_youtube():
    print("🟢 Connecting to YouTube...")
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        search = youtube.search().list(
            part="snippet",
            channelId=YOUTUBE_CHANNEL_ID,
            eventType="live",
            type="video"
        ).execute()

        if not search["items"]:
            print("❌ No live stream found on YouTube.")
            return

        video_id = search["items"][0]["id"]["videoId"]
        live = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
        live_chat_id = live["items"][0]["liveStreamingDetails"]["activeLiveChatId"]
        print(f"✅ Connected to YouTube liveChatId: {live_chat_id}")

        while True:
            messages = youtube.liveChatMessages().list(
                liveChatId=live_chat_id, part="snippet,authorDetails"
            ).execute()

            for item in messages.get("items", []):
                user = item["authorDetails"]["displayName"]
                msg = item["snippet"]["displayMessage"]
                print(f"[YouTube] {user}: {msg}")
                queue_ntfy("YouTube", user, msg)

            time.sleep(5)
    except Exception as e:
        print(f"❌ YouTube error: {e}")

# --- Facebook ---
def connect_facebook():
    print("🟢 Connecting to Facebook...")
    url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/live_videos?access_token={FACEBOOK_TOKEN}"
    try:
        while True:
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                print(f"✅ Facebook response: {data}")
            else:
                print("❌ Facebook error", r.text)
            time.sleep(10)
    except Exception as e:
        print(f"❌ Facebook error: {e}")

# --- Kick ---
def connect_kick():
    print("🟢 Connecting to Kick...")

    def on_message(ws, message):
        for line in message.split("\r\n"):
            if "PRIVMSG" in line:
                match = re.match(r":(.*?)!.* PRIVMSG #.* :(.*)", line)
                if match:
                    user, msg = match.groups()
                    print(f"[Kick] {user}: {msg}")
                    queue_ntfy("Kick", user, msg)

    def on_open(ws):
        print("✅ Connected to Kick chat")
        ws.send(f"NICK {KICK_USERNAME}")
        ws.send(f"JOIN #{KICK_CHANNEL}")

    ws = websocket.WebSocketApp(
        "wss://irc-ws.chat.kick.com/",
        on_message=on_message,
        on_open=on_open,
    )
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=ntfy_worker, daemon=True).start()
    threading.Thread(target=connect_youtube, daemon=True).start()
    threading.Thread(target=connect_facebook, daemon=True).start()
    threading.Thread(target=connect_kick, daemon=True).start()

    while True:
        time.sleep(1)
