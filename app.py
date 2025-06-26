import gradio as gr
import cohere
from newspaper import Article
from dotenv import load_dotenv
import os


load_dotenv()


cohereKey = os.getenv("Cohere_key")
co = cohere.Client(cohereKey)

# --- Bullet extractor using Cohere Chat ---
def cohere_bullet_extractor(text):
    prompt = f"""
Extract 3 to 6 *brief and distinct bullet points* summarizing the following article. 
Each bullet point should be a short, standalone fact or update — no fluff or storytelling.

Return each point on a new line, starting with a dash ("- ").

Article:
{text}
"""

    try:
        response = co.chat(
            model="command-r",
            message=prompt,
            temperature=0.4
        )
        result = response.text
        bullets = [line.strip() for line in result.split("\n") if line.strip().startswith("-")]
        return bullets
    except Exception as e:
        return [f"[Error: {e}]"]



def generate_tweet_thread(title, url, bullet_points):
    tweets = []

    # ✅ Safe title
    title = title.strip() if title and title.strip() else "[Unknown Title]"
    tweets.append(f"🧵 Summary of: {title}\n\nHere are the key takeaways:")

    # ✅ Clean bullets
    clean_bullets = [bp.strip() for bp in bullet_points if bp.strip()]
    if not clean_bullets:
        return ["🧵 No valid bullet points extracted."]

    # ✅ Truncate and add each bullet
    for bullet in clean_bullets:
        tweet = bullet.strip()
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        tweets.append(tweet)

    # ✅ Final link
    final_link = f"📖 Read full article here:\n{url.strip()}"
    if len(final_link) > 280:
        final_link = final_link[:277] + "..."
    tweets.append(final_link)

    return tweets  # ✅ return list (NOT joined string)


def run_agent(url):
    try:
        article = Article(url)
        article.download()
        article.parse()

        bullets = cohere_bullet_extractor(article.text)
        
        thread = generate_tweet_thread(article.title, url, bullets)

        tweet_url = post_tweet_thread_v2(thread)


        return f"{thread}\n\n✅ Tweet thread posted: {tweet_url}"
    except Exception as e:
        return f"❌ Error: {e}"

import tweepy

# Paste your Bearer Token (found in Twitter Dev portal)
#BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAJ%2Fw2gEAAAAAwhu8I5KqydKAsBOJ9obakBNKtx0%3DkTSWUyRtrygTziA6T7KdcJGCvvKHMgEmQpRvW1yY2kfgfJI02E"

#client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Twitter app credentials
API_KEY = os.getenv("API_K")
API_SECRET = os.getenv("API_SEC")
ACCESS_TOKEN = os.getenv("ACCESS_TKN")
ACCESS_SECRET = os.getenv("ACCESS_SEC")
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

import time  
def post_tweet_thread_v2(tweets):
    try:
        tweet_chain = []
        clean_tweets = [t.strip() for t in tweets if t.strip()]

        # Post first tweet
        response = client.create_tweet(text=clean_tweets[0])
        tweet_id = response.data["id"]
        tweet_chain.append(tweet_id)

        # Post rest as replies with delay
        for tweet in clean_tweets[1:]:
            time.sleep(2)  # ⏱️ Wait 2 seconds before each post
            response = client.create_tweet(
                text=tweet,
                in_reply_to_tweet_id=tweet_chain[-1]
            )
            tweet_chain.append(response.data["id"])

        return f"https://twitter.com/user/status/{tweet_chain[0]}"
    except Exception as e:
        return f"[Tweeting failed ❌: {e}]"





app = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(label="Paste article URL here"),
    outputs=gr.Textbox(label="Tweet Thread Preview", lines=20),
    title="🧠 AI Article-to-Tweet Thread Agent",
    description="Paste a news/blog article link. I'll generate a summary thread ready for Twitter."
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port)
