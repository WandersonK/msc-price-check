import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright

URL = "https://www.msccruzeiros.com.br/Search%20Result?departureDateFrom=29%2F10%2F2027&departureDateTo=29%2F10%2F2027&passengers=2%7C0%7C0%7C0&page=1&ships=DI&nights=13&embkPort=CVV&area=POS"

SELECTORS = [
    ".itinerary-card-price__price",  # seletor antigo
    ".prices__main-price span",      # novo seletor (primeiro span filho)
]
STATE_FILE = "last_price.json"

# User-Agent realista para reduzir chance de bloqueio/página diferente no CI.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Quantas vezes tentar o scraping antes de desistir (evita alerta por falha pontual).
MAX_ATTEMPTS = 3


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram não configurado.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        print("Mensagem enviada:", message)
    except Exception as e:
        print("Erro ao enviar Telegram:", e)


def parse_price(price_text):
    """Converte 'R$ 5.313' ou 'R$ 5.313,50' em float. Retorna None se não der."""
    if not price_text:
        return None
    # Mantém apenas dígitos, ponto e vírgula.
    cleaned = re.sub(r"[^\d.,]", "", price_text)
    if not cleaned:
        return None
    # Formato brasileiro: '.' é separador de milhar, ',' é decimal.
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _read_price_from_page(page):
    """Tenta cada seletor e devolve o primeiro texto não-vazio encontrado."""
    for selector in SELECTORS:
        try:
            print(f"Tentando seletor: {selector}")
            page.wait_for_selector(selector, timeout=30000)
        except Exception as e:
            print(f"Seletor {selector} não encontrado: {e}")
            continue

        # Aguarda o texto ser renderizado (evita sleep fixo cego).
        for _ in range(10):
            element = page.query_selector(selector)
            if element:
                text = (element.inner_text() or "").strip()
                if text:
                    return text
            time.sleep(1)
    return None


def fetch_price():
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Tentativa {attempt}/{MAX_ATTEMPTS}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                try:
                    page.goto(URL, timeout=60000)
                    price_text = _read_price_from_page(page)
                finally:
                    browser.close()

            if price_text and parse_price(price_text) is not None:
                return price_text
            last_error = f"Preço não encontrado/ inválido: {price_text!r}"
            print(last_error)
        except Exception as e:
            last_error = str(e)
            print(f"Erro na tentativa {attempt}: {e}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(5)

    raise RuntimeError(f"Falha ao obter preço após {MAX_ATTEMPTS} tentativas: {last_error}")


def load_last():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print("Não foi possível ler o estado anterior:", e)
    return None


def save_last(price_text):
    payload = {
        "price": price_text,
        "value": parse_price(price_text),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def build_change_message(last, price_text):
    """Monta a mensagem de variação com direção e delta, quando possível."""
    new_value = parse_price(price_text)
    old_text = last.get("price") if last else None
    old_value = last.get("value") if last else None
    if old_value is None:
        old_value = parse_price(old_text)

    if old_value is not None and new_value is not None:
        delta = new_value - old_value
        if delta < 0:
            emoji, verbo = "📉", "baixou"
        elif delta > 0:
            emoji, verbo = "📈", "subiu"
        else:
            emoji, verbo = "🔄", "mudou"
        return (
            f"{emoji} Preço {verbo}: {old_text} → {price_text} "
            f"(Δ R$ {abs(delta):,.2f})\n{URL}"
        )
    return f"💰 Preço alterado para {price_text}\n{URL}"


def main():
    try:
        price = fetch_price()
    except Exception as e:
        send_telegram(f"⚠️ Monitor MSC falhou ao obter o preço.\n{e}\n{URL}")
        raise

    last = load_last()

    if not last:
        send_telegram(f"👀 Monitor iniciado. Preço atual: {price}\n{URL}")
        save_last(price)
        print("Primeiro preço registrado:", price)
    elif last.get("price") != price:
        send_telegram(build_change_message(last, price))
        save_last(price)
        print("Novo preço detectado e salvo:", price)
    else:
        # Sem mudança: só loga, não notifica (evita spam de hora em hora).
        print("Sem alteração. Preço atual:", price)


if __name__ == "__main__":
    main()
