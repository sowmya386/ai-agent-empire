# youtube_agent.py — pip install google-api-python-client gtts moviepy pytrends
import os
import sys
from gtts import gTTS
from moviepy.editor import AudioFileClip, ColorClip, TextClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pytrends.request import TrendReq

# Step 1: Find trending topic
def get_trending_topic():
    try:
        pt = TrendReq(hl='en-IN', tz=330)
        pt.build_payload(['AI tools', 'make money online'], geo='IN')
        data = pt.related_queries()
        topics = data['AI tools']['top']
        return topics.iloc[0]['query'] if not topics.empty else 'AI tools 2026'
    except Exception as e:
        print(f"Error checking trends: {e}. Falling back to default topic.")
        return 'AI tools 2026'

# Step 2: Generate script (paste into Claude.ai free or use Ollama locally)
SCRIPT_PROMPT = """Write a 5-minute YouTube script about: {topic}
Include: hook (30s), 3 main points, call to action. 
Make it engaging, add timestamps."""

# Step 3: Text to speech — FREE with gTTS
def make_audio(text, filename='audio.mp3'):
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filename)
    return filename

# Step 4: Assemble video with MoviePy — FREE
def make_video(audio_file, title, output='video.mp4'):
    audio = AudioFileClip(audio_file)
    bg = ColorClip(size=(1920, 1080), color=[15, 15, 30], duration=audio.duration)
    
    # Standard text clips can sometimes fail on systems without ImageMagick.
    # We will write a fallback or print instructions.
    try:
        txt = TextClip(title, fontsize=60, color='white', font='Arial-Bold')
        txt = txt.set_pos('center').set_duration(audio.duration)
        video = CompositeVideoClip([bg, txt]).set_audio(audio)
    except Exception as e:
        print(f"TextClip failed (usually needs ImageMagick): {e}")
        print("Falling back to plain color clip with audio.")
        video = bg.set_audio(audio)
        
    video.write_videofile(output, fps=24, codec='libx264')
    return output

# Step 5: Upload to YouTube — FREE API
def upload_to_youtube(video_file, title, description):
    yt_api_key = os.environ.get('YT_API_KEY')
    if not yt_api_key:
        print("YT_API_KEY environment variable not set. Cannot upload.")
        return
    # Set up OAuth2 / Developer Key API access
    youtube = build('youtube', 'v3', developerKey=yt_api_key)
    request = youtube.videos().insert(
        part='snippet,status',
        body={'snippet':{'title':title,'description':description,
               'tags':['AI','money','automation'],'categoryId':'28'},
              'status':{'privacyStatus':'public'}},
        media_body=MediaFileUpload(video_file))
    response = request.execute()
    print(f"Uploaded: youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    print("Starting YouTube pipeline...")
    topic = get_trending_topic()
    print(f"Trending Topic: {topic}")
    audio = make_audio(f"Today we talk about {topic}. This is a zero cost agent demonstration.")
    video = make_video(audio, topic)
    upload_to_youtube(video, topic, f"Learn about {topic}")
    print("YouTube pipeline complete.")