# laptop_controller.py — pip install pyautogui selenium keyboard pillow pytesseract
import pyautogui
import time
import keyboard
import subprocess
import os
from PIL import Image
import pytesseract  # Free OCR — reads what's on screen

pyautogui.FAILSAFE = True  # Move mouse to corner to stop
pyautogui.PAUSE = 0.5

# Configure Tesseract Path if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def open_app(app_name):
    if os.name == 'nt':  # Windows
        subprocess.Popen(['start', app_name], shell=True)
    else:  # Mac/Linux
        subprocess.Popen(['open', '-a', app_name])
    time.sleep(2)

def click_at(x, y, double=False):
    pyautogui.moveTo(x, y, duration=0.5)
    if double:
        pyautogui.doubleClick()
    else:
        pyautogui.click()

def type_text(text, interval=0.05):
    pyautogui.typewrite(text, interval=interval)

def find_and_click(image_path, confidence=0.8):
    # Find a button/element on screen by image — FREE
    try:
        location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        if location:
            pyautogui.click(location)
            return True
    except Exception as e:
        print(f"locateCenterOnScreen error: {e}")
    return False

def read_screen_text(region=None):
    # Free OCR — reads any text on screen
    try:
        screenshot = pyautogui.screenshot(region=region)
        return pytesseract.image_to_string(screenshot)
    except Exception as e:
        return f"OCR Error: {e}"

def open_browser_url(url):
    import webbrowser
    webbrowser.open(url)
    time.sleep(3)

# Example: Auto-post to Claude.ai and get script
def generate_content_with_claude(prompt):
    open_browser_url('https://claude.ai')
    time.sleep(4)
    # Find the text input and type
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(1)
    type_text(prompt)
    pyautogui.press('enter')
    time.sleep(15)  # Wait for response
    # Select all text and copy
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey('ctrl', 'c')
    import pyperclip
    return pyperclip.paste()

# Selenium for browser automation — FREE
def selenium_browser_task(url, actions):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=opts)  # Free ChromeDriver
    driver.get(url)
    time.sleep(3)
    for action in actions:
        if action['type'] == 'click':
            driver.find_element(By.CSS_SELECTOR, action['selector']).click()
        elif action['type'] == 'type':
            el = driver.find_element(By.CSS_SELECTOR, action['selector'])
            el.clear()
            el.send_keys(action['text'])
        time.sleep(1)
    return driver

# Example: auto-open Groww and navigate to a stock
def open_groww_stock(stock_name):
    import webbrowser
    url = f"https://groww.in/stocks/{stock_name.lower()}"
    webbrowser.open(url)  # Opens in default browser, logs in automatically
    print(f"Opening {stock_name} in Groww...")

if __name__ == "__main__":
    print("Laptop controller library loaded. Run in orchestrator or import functions to use.")