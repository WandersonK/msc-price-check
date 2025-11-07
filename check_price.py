from playwright.sync_api import sync_playwright
import time
import json
import os
import requests

URL = "https://www.msccruzeiros.com.br/Search%20Result?embkPort=SSZ&departureDateFrom=22%2F03%2F2026&departureDateTo=29%2F03%2F2026&passengers=2%7C0%7C0%7C0&page=1&ships=PR&nights=6%2C7#/"
SELECTOR = ".itinerary-card-price__price"
STATE_FILE = "last_price.json"

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram não configurado.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
        print("Mensagem enviada:", message)
    except Exception as e:
        print("Erro ao enviar:", e)

def fetch_price():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_selector(SELECTOR, timeout=30000)
        time.sleep(5)  # espera 5s adicionais
        price = page.locator(SELECTOR).first.text_content().strip()
        browser.close()
        return price

def load_last():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_last(price):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"price": price}, f, ensure_ascii=False)

def main():
    price = fetch_price()
    print(price)
    # last = load_last()

    # if not last or last["price"] != price:
    #     msg = f"💰 Preço alterado para {price}\n{URL}"
    #     send_telegram(msg)
    #     save_last(price)
    #     print("Novo preço detectado e salvo:", price)
    # else:
    #     print("Sem alteração. Preço atual:", price)

if __name__ == "__main__":
    main()
