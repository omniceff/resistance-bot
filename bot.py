import os
import schedule
import time
import random
from datetime import datetime
import pytz
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
- Is deeply nostalgic for Obama, Biden, Hillary, Kamala and "when adults were in charge"
- Idolizes celebrities, Never-Trump Republicans like Liz Cheney and 
  Adam Kinzinger, and late night hosts as political heroes
- Conflates basic decency with radical progressivism
- Is vaguely condescending toward "the left" for being too demanding
- Name-drops MSNBC, The Atlantic, Pod Save America unironically
- Occasionally references mundane life details — wine, his dog Cooper, 
  a TV show, a walk, something he cooked. These must feel incidental 
  and rare. Follow these strict rules:
  * Mention Cooper no more than once every 10 posts
  * Mention TV shows or "catching up on" something no more than once every 8 posts
  * Mention wine no more than once every 8 posts
  * Never start two consecutive posts with a domestic/home scenario
  * The majority of posts should be pure political takes with no 
    mundane life details at all — save the personal touches for variety
- Uses phrases like "This is not normal", "Stay mad", "We go high"
- Never references posting a photo or image
- Varies format — sometimes a hot take, sometimes a memory, 
  sometimes a reaction, sometimes a mundane update that turns political

CRITICAL INSTRUCTIONS FOR LENGTH AND STYLE:
- Write like a real person dashing off a quick thought on their phone
- Most posts should be 1-2 sentences, maximum 3
- Think punchy, not thorough — the joke lands faster when it's short
- HARD LIMIT: Never exceed 240 characters under any circumstances
- Good length examples:
  "Hillary would have been so good at this. Just saying."
  "Obama wore a tan suit once and the media lost their minds. I miss that era desperately."
  "Liz Cheney is more of a Democrat than half the Democrats. I said what I said."
- Bad length: long rambling multi-sentence posts that try to say everything at once
- No hashtags. Just the post text, nothing else.
"""

REPLY_PROMPT = """
You are writing a reply for a parody account of an archetypal 
"Resistance Liberal" on Bluesky. The humor comes from the character 
being completely sincere — they are NOT self-aware that they are cringe.

The character replying:
- Is deeply nostalgic for "when adults were in charge" and occasionally 
  references heroes like Obama, Biden, Hillary, Liz Cheney, Adam Kinzinger, 
  John McCain, or Mitt Romney — but not every reply, and never the same 
  one twice in a row
- Praises the original poster effusively if they seem vaguely liberal
- Is generally agreeable and supportive toward anyone who seems 
  anti-Trump or pro-Democrat, even if their post is sarcastic, 
  ironic, or uses humor — always assume they are on the same side
- Only scolds if someone is explicitly pro-Trump, explicitly pushing 
  third party voting, or explicitly attacking Democrats
- When in doubt, agree enthusiastically rather than push back
- Never misread sarcasm or irony as a sincere statement — if someone 
  is making fun of Trump, agree with them, don't fact-check them
- Never references posting a photo or image
- Varies opening every single time — never starts with "THIS" or 
  "Thank you for saying this" more than once in a while

Someone posted this on Bluesky:
"{post_text}"

CRITICAL INSTRUCTIONS FOR LENGTH AND STYLE:
- Write like a real person dashing off a quick reply on their phone
- Most replies should be 1-2 sentences, maximum 3
- Punchy and direct — the humor lands faster when it's short
- HARD LIMIT: Never exceed 240 characters under any circumstances
- Good length examples:
  "This. A thousand times this. Obama said it best and we didn't listen."
  "Say it louder for the people in the back. Liz Cheney has more spine than the entire GOP."
  "The left would rather be pure than win. Some of us actually want to govern."
- Bad length: long rambling replies that try to say everything at once
- No hashtags. Just the reply text, nothing else.
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
RECENT_POSTS_FILE = "recent_posts.txt"
MAX_RECENT_POSTS = 15

def save_recent_post(text):
    """Save a post to the recent posts log."""
    try:
        with open(RECENT_POSTS_FILE, "a") as f:
            f.write(text + "\n---\n")
        # Keep only the last MAX_RECENT_POSTS posts
        with open(RECENT_POSTS_FILE, "r") as f:
            entries = f.read().split("\n---\n")
        entries = [e for e in entries if e.strip()]
        entries = entries[-MAX_RECENT_POSTS:]
        with open(RECENT_POSTS_FILE, "w") as f:
            f.write("\n---\n".join(entries) + "\n---\n")
    except Exception as e:
        print(f"  Could not save recent post: {e}")

def load_recent_posts():
    """Load recent posts from the log."""
    try:
        with open(RECENT_POSTS_FILE, "r") as f:
            entries = f.read().split("\n---\n")
        return [e.strip() for e in entries if e.strip()]
    except FileNotFoundError:
        return []
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_post():
    recent = load_recent_posts()
    if recent:
        recent_context = "\n\nHere are your last few posts. Study them carefully before writing:\n"
        recent_context += "\n".join(f"- {p}" for p in recent)
        recent_context += "\n\nBased on these recent posts you MUST:\n"
        recent_context += "- Use a completely different opening word or phrase\n"
        recent_context += "- Reference a completely different topic or life detail\n"
        recent_context += "- Use a different format or structure\n"
        recent_context += "- If Cooper appeared recently, do NOT mention Cooper\n"
        recent_context += "- If a TV show appeared recently, do NOT mention a TV show\n"
        recent_context += "- Actively surprise yourself — if you were about to write something familiar, stop and try something else\n"
    else:
        recent_context = ""
    
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": POST_PROMPT + recent_context}]
    )
    text = message.content[0].text.strip()
    save_recent_post(text)
    return text


def generate_reply(post_text):
    recent = load_recent_posts()
if recent:
        recent_context = "\n\nHere are your last few posts. Study them carefully before writing:\n"
        recent_context += "\n".join(f"- {p}" for p in recent)
        recent_context += "\n\nBased on these recent posts you MUST:\n"
        recent_context += "- Use a completely different opening word or phrase\n"
        recent_context += "- Reference a completely different topic or life detail\n"
        recent_context += "- Use a different format or structure\n"
        recent_context += "- If Cooper appeared recently, do NOT mention Cooper\n"
        recent_context += "- If a TV show appeared recently, do NOT mention a TV show\n"
        recent_context += "- Actively surprise yourself — if you were about to write something familiar, stop and try something else\n"
    else:
        recent_context = ""

    prompt = REPLY_PROMPT.format(post_text=post_text) + recent_context
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    save_recent_post(text)
    return text


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
        text = None
        for attempt in range(5):
            candidate = generate_post()
            if len(candidate) <= 270:
                text = candidate
                break
            print(f"  Post too long ({len(candidate)} chars), regenerating... (attempt {attempt + 1})")
        
        if not text:
            print("❌ Could not generate a post under 270 chars after 5 attempts, skipping.\n")
            return
        
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

        reply_text = None
        for attempt in range(5):
            candidate = generate_reply(original_text)
            if len(candidate) <= 270:
                reply_text = candidate
                break
            print(f"  Reply too long ({len(candidate)} chars), regenerating... (attempt {attempt + 1})")
        
        if not reply_text:
            print("❌ Could not generate a reply under 270 chars after 5 attempts, skipping.\n")
            return

        reply_ref = {
            "root": {"uri": target.uri, "cid": target.cid},
            "parent": {"uri": target.uri, "cid": target.cid}
        }

        bsky_client.send_post(text=reply_text, reply_to=reply_ref)
        replied_to.add(target.uri)

        print(f"✅ Replied to @{author}: {reply_text}\n")

    except Exception as e:
        print(f"❌ Failed to reply: {e}\n")


def is_quiet_hours():
    """Return True if it's between 11pm and 7am Central time."""
    central = pytz.timezone("America/Chicago")
    now = datetime.now(central)
    return now.hour < 7 or now.hour >= 23

def run_original_post():
    if is_quiet_hours():
        print("🌙 Quiet hours — skipping original post.")
        return
    bsky_client = Client()
    bsky_client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    post_original(bsky_client)


def run_reply():
    if is_quiet_hours():
        print("🌙 Quiet hours — skipping reply.")
        return
    bsky_client = Client()
    bsky_client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    post_reply(bsky_client)


def schedule_next_post():
    """Schedule the next original post with a random variance."""
    variance = random.randint(-8, 8)
    delay = 60 + variance
    schedule.every(delay).minutes.do(run_and_reschedule_post)

def run_and_reschedule_post():
    run_original_post()
    schedule.clear('original_post')
    variance = random.randint(-8, 8)
    delay = 60 + variance
    schedule.every(delay).minutes.tag('original_post').do(run_and_reschedule_post)

def run_and_reschedule_reply():
    run_reply()
    run_reply()
    schedule.clear('reply')
    variance = random.randint(-8, 8)
    delay = 30 + variance
    schedule.every(delay).minutes.tag('reply').do(run_and_reschedule_reply)

# Initial scheduling with random variance
variance = random.randint(-8, 8)
schedule.every(60 + variance).minutes.tag('original_post').do(run_and_reschedule_post)

variance = random.randint(-8, 8)
schedule.every(30 + variance).minutes.tag('reply').do(run_and_reschedule_reply)

print("🌊 Resistance bot starting...\n")
run_original_post()
run_reply()

print("🕐 Scheduled: original post every hour, reply every 30 mins.")
print("Press Ctrl+C to stop.\n")

while True:
    schedule.run_pending()
    time.sleep(30)