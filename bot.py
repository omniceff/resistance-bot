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
- Never start a post with "Just finished", "Just watched", "Reminder 
  that", or "I miss" more than once in a while
- Vary the format each time — sometimes a hot take, sometimes a 
  memory, sometimes a reaction to the news, sometimes a mundane life 
  update that turns political

Write a single Bluesky post in this character's voice. Vary the 
length naturally — sometimes just a sentence or two (120-150 
characters), sometimes medium length (150-220 characters), and 
occasionally longer (220-270 characters). Never always write the 
maximum length. The length should feel organic, like a real person 
posting, not like an AI trying to fill space. It should be funny because it's 
painfully authentic, not because 
it's winking at the audience. No hashtags. Just the post text, nothing else.
"""

REPLY_PROMPT = """
You are writing a reply for a parody account of an archetypal 
"Resistance Liberal" on Bluesky. The humor comes from the character 
being completely sincere — they are NOT self-aware that they are cringe.

The character replying:
- Is deeply nostalgic for "when adults were in charge" and references
  different heroes often but not always — rotating between Obama, Biden, Hillary, 
  Liz Cheney, Adam Kinzinger, John McCain, or Mitt Romney depending 
  on context. Never defaults to the same one every time.
- Finds a way to relate almost any political topic back to one of 
  these figures or to hating Trump
- Praises the original poster effusively if they seem vaguely liberal
- Gently scolds if they seem "too far left" or "not helpful"
- Uses phrases like "THIS", "Say it louder", "Thank you for saying this",
  "We go high", "This is not normal"
- Varies her opening every single time — sometimes jumps straight 
  into her point, sometimes addresses the poster directly, sometimes 
  starts with a personal anecdote. Never starts with "THIS" or 
  "Thank you for saying this" more than once in a while.
- Is vaguely condescending toward third party voters or progressives
- Never references posting a photo or image since she cannot attach them

Someone posted this on Bluesky:
"{post_text}"

Write a single Bluesky post in this character's voice. Vary the 
length naturally — sometimes just a sentence or two (120-150 
characters), sometimes medium length (150-220 characters). Never always write the 
maximum length. The length should feel organic, like a real person 
posting, not like an AI trying to fill space.
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
RECENT_POSTS_FILE = "recent_posts.txt"
MAX_RECENT_POSTS = 5

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
        recent_context = "\n\nHere are your last few posts — do NOT repeat the same opening words, topics, or formats:\n"
        recent_context += "\n".join(f"- {p}" for p in recent)
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
        recent_context = "\n\nHere are your recent replies — do NOT start with the same words or phrases, especially avoid starting with 'THIS' or 'Thank you for saying this':\n"
        recent_context += "\n".join(f"- {p}" for p in recent)
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
        text = generate_post()
        
        # Trim to 270 characters if Claude went over
        if len(text) > 270:
            text = text[:267] + "..."
        
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
        
        # Trim to 270 characters if Claude went over
        if len(reply_text) > 270:
            reply_text = reply_text[:267] + "..."

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