import os
import schedule
import time
import random
from atproto import Client
from atproto_client.models.app.bsky.feed.search_posts import Params as SearchParams
import anthropic
from dotenv import load_dotenv

load_dotenv()

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

POST_PROMPT = """
You are writing posts for a parody account of an archetypal 
"Resistance Liberal" on Bluesky. The humor comes from the character 
being completely sincere — they are NOT self-aware that they are cringe.

The character:
- Is deeply nostalgic for Obama, Biden, Hilary, Kamala and "when adults were in charge"
- Idolizes celebrities, resistance republicans like Liz Cheney and Adam Kinzinger, and late night hosts as political heroes
- Says things like "I miss when we had a president who could form 
  a sentence", "I cried watching the inauguration", "Hillary would 
  have prevented this"
- Conflates basic decency with radical progressivism
- Is vaguely condescending toward "the left" for being too demanding
- Name-drops MSNBC, The Atlantic, Pod Save America unironically
- Occasionally mentions mundane hobbies or daily life in between 
  political takes — things like wine, his dog Cooper, a TV show, 
  a book he's reading, a walk he took, or something he cooked. 
  These should feel incidental, not a recurring theme. Never mention 
  Wordle or Cooper more than once every several posts.
- Uses phrases like "This is not normal", "Stay mad", "We go high"
- Never references posting a photo or image since she cannot attach them

Write a single Bluesky post (max 290 characters) in this character's 
voice. It should be funny because it's painfully authentic, not because 
it's winking at the audience. No hashtags. Just the post text, nothing else.
"""

REPLY_PROMPT = """
You are writing a reply for a parody account of an archetypal 
"Resistance Liberal" on Bluesky. The humor comes from the character 
being completely sincere — they are NOT self-aware that they are cringe.

The character replying:
- Is deeply nostalgic for Obama, Biden, Hilary, Kamala, and "when adults were in charge"
- Finds a way to relate almost any political topic back to missing Obama
  or hating Trump
- Praises the original poster effusively if they seem vaguely liberal
- Gently scolds if they seem "too far left" or "not helpful"
- Uses phrases like "THIS", "Say it louder", "Thank you for saying this",
  "We go high", "This is not normal"
- Is vaguely condescending toward third party voters or progressives
- Never references posting a photo or image since she cannot attach them

Someone posted this on Bluesky:
"{post_text}"

Write a single reply (max 280 characters) in this character's voice.
It should feel authentic and slightly unhinged in a very suburban-liberal way.
No hashtags. Just the reply text, nothing else. Don't be nasty and follow the rules.
"""

SEARCH_TERMS = [
    "US politics",
    "Congress",
    "White House",
    "Senate",
    "Supreme Court",
    "election",
    "president",
    "Democrat",
    "Republican",
    "Trump",
    "Biden",
    "Obama"
]

replied_to = set()
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_post():
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": POST_PROMPT}]
    )
    return message.content[0].text.strip()


def generate_reply(post_text):
    prompt = REPLY_PROMPT.format(post_text=post_text)
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def get_popular_posts(bsky_client, search_term, limit=10):
    try:
        results = bsky_client.app.bsky.feed.search_posts(
            SearchParams(q=search_term, limit=limit, sort="top")
        )
        return results.posts if results and results.posts else []
    except Exception as e:
        print(f"  Search error for '{search_term}': {e}")
        return []


def find_post_to_reply_to(bsky_client):
    term = random.choice(SEARCH_TERMS)
    print(f"  Searching for posts about: '{term}'")
    posts = get_popular_posts(bsky_client, term)

    candidates = [
        p for p in posts
        if p.uri not in replied_to
        and p.record.text
        and len(p.record.text) > 30
        and p.author.handle != BLUESKY_HANDLE
    ]

    if not candidates:
        print("  No suitable posts found.")
        return None

    candidates.sort(
        key=lambda p: (p.like_count or 0) + (p.repost_count or 0),
        reverse=True
    )

    return random.choice(candidates[:3])

def post_original(bsky_client):
    print("📝 Generating original post...")
    try:
        text = generate_post()
        bsky_client.send_post(text=text)
        print(f"✅ Posted: {text}\n")
    except Exception as e:
        print(f"❌ Failed to post: {e}\n")


def post_reply(bsky_client):
    print("🔍 Looking for a post to reply to...")
    try:
        target = find_post_to_reply_to(bsky_client)
        if not target:
            return

        original_text = target.record.text
        author = target.author.handle
        print(f"  Found post by @{author}: \"{original_text[:80]}...\"")

        reply_text = generate_reply(original_text)

        reply_ref = {
            "root": {"uri": target.uri, "cid": target.cid},
            "parent": {"uri": target.uri, "cid": target.cid}
        }

        bsky_client.send_post(text=reply_text, reply_to=reply_ref)
        replied_to.add(target.uri)

        print(f"✅ Replied to @{author}: {reply_text}\n")

    except Exception as e:
        print(f"❌ Failed to reply: {e}\n")


def run_original_post():
    bsky_client = Client()
    bsky_client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    post_original(bsky_client)


def run_reply():
    bsky_client = Client()
    bsky_client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    post_reply(bsky_client)


schedule.every(1).hours.do(run_original_post)
schedule.every(30).minutes.do(run_reply)

print("🌊 Resistance bot starting...\n")
run_original_post()
run_reply()

print("🕐 Scheduled: original post every hour, reply every 30 mins.")
print("Press Ctrl+C to stop.\n")

while True:
    schedule.run_pending()
    time.sleep(30)