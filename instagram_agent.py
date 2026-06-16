# instagram_agent.py — pip install requests Pillow schedule
import requests
import os
import schedule
import time
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

IG_TOKEN = os.environ.get('IG_ACCESS_TOKEN')  # Free from Meta for Developers
IG_USER_ID = os.environ.get('IG_USER_ID')

CAPTIONS = [
    "5 AI tools that save 10 hours a week 🤖\n\n1. Claude AI\n2. Notion AI\n3. Otter.ai\n4. Gamma.app\n5. Perplexity\n\nSave this post! ♻️\n\n#AItools #productivity #automation #makemoneyonline",
    "How I made ₹50,000 this month using FREE AI tools 💰\n\nNo investment. Just:\n✅ Claude AI for content\n✅ Python for automation\n✅ Canva free for design\n\nFollow for daily tips 👉\n\n#sidehustle #AIincome #freedomlife",
]

def create_post_image(text, filename='post.jpg'):
    # Create image with Pillow — completely free
    img = Image.new('RGB', (1080, 1080), color=(15, 15, 35))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 50)
        small = ImageFont.truetype('arial.ttf', 36)
    except:
        font = ImageFont.load_default()
        small = font
    draw.text((80, 80), "⚡ AI EMPIRE", fill=(124, 111, 247), font=font)
    draw.text((80, 200), text[:200], fill=(255, 255, 255), font=small)
    img.save(filename, quality=95)
    print(f"Generated image: {filename}")
    return filename

def upload_to_instagram(image_path, caption):
    if not IG_TOKEN or not IG_USER_ID:
        print("Meta credentials (IG_ACCESS_TOKEN / IG_USER_ID) not set. Skipping upload.")
        return
    # Step 1: Upload image to get container ID
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    # Note: image must be a public URL — host on GitHub Pages free
    params = {'image_url': 'YOUR_GITHUB_PAGES_IMAGE_URL',
              'caption': caption,
              'access_token': IG_TOKEN}
    r = requests.post(url, params=params).json()
    container_id = r.get('id')
    if not container_id:
        print(f"Failed to create media container: {r}")
        return
    # Step 2: Publish
    publish_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    requests.post(publish_url, params={'creation_id': container_id, 'access_token': IG_TOKEN})
    print(f"Posted at {datetime.now().strftime('%H:%M')}")

def auto_post():
    import random
    caption = random.choice(CAPTIONS)
    img = create_post_image(caption)
    upload_to_instagram(img, caption)

if __name__ == "__main__":
    print("Running Instagram agent auto-post task...")
    auto_post()