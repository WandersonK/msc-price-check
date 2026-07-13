from playwright.sync_api import sync_playwright
import time
import json
import os
import requests

URL = "https://www.msccruzeiros.com.br/Search%20Result?departureDateFrom=29%2F10%2F2027&departureDateTo=29%2F10%2F2027&passengers=2%7C0%7C0%7C0&page=1&ships=DI&nights=13&embkPort=CVV&area=POS"
# SELECTOR = ".itinerary-card-price__price"
SELECTORS = [
    ".itinerary-card-price__price",  # seletor antigo
    ".prices__main-price span"       # novo seletor (primeiro span filho)
]
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

# def fetch_price():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page()
#         page.goto(URL)
#         page.wait_for_selector(SELECTOR, timeout=30000)
#         time.sleep(5)  # espera 5s adicionais
#         price = page.locator(SELECTOR).first.text_content().strip()
#         browser.close()
#         return price

def fetch_price():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        element = None
        for selector in SELECTORS:
            try:
                print(f"Tentando seletor: {selector}")
                page.wait_for_selector(selector, timeout=30000)
                # Espera extra pra garantir renderização
                time.sleep(5)
                element = page.query_selector(selector)
                if element:
                    break
            except Exception as e:
                print(f"Seletor {selector} não encontrado: {e}")

        if not element:
            raise Exception("Nenhum seletor válido encontrado para o preço.")

        price_text = element.inner_text().strip()
        browser.close()
        return price_text
    
    
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
    last = load_last()

    if not last or last["price"] != price:
        msg = f"💰 Preço alterado para {price}\n{URL}"
        send_telegram(msg)
        save_last(price)
        print("Novo preço detectado e salvo:", price)
    else:
        msg = f'Sem alteração. Preço atual: {price}'
        send_telegram(msg)
        print("Sem alteração. Preço atual:", price)

if __name__ == "__main__":
    main()
