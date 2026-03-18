from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

SUGGERITI_URL = "https://www.instagram.com/explore/people/"
COOKIES_JSON = os.getenv("INSTAGRAM_COOKIES")  # Cookie di sessione in formato JSON
MAX_FOLLOW = 70  # Numero massimo di account da seguire per sessione


def carica_cookies(context):
    """Carica i cookie di sessione Instagram nel browser."""
    if not COOKIES_JSON:
        print("Errore: INSTAGRAM_COOKIES non trovato nei secrets.")
        return False
    try:
        cookies = json.loads(COOKIES_JSON)
        context.add_cookies(cookies)
        print(f"Cookie caricati con successo ({len(cookies)} cookie).")
        return True
    except Exception as e:
        print(f"Errore nel caricamento dei cookie: {e}")
        return False


def chiudi_popup(page):
    """Chiude eventuali popup o dialoghi aperti su Instagram."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        for testo in ["Non ora", "Not Now", "Chiudi", "Close", "Cancel"]:
            btn = page.locator(f"button:has-text('{testo}')").first
            if btn.is_visible():
                btn.click(timeout=3000)
                time.sleep(0.5)
                break
    except Exception:
        pass


def trova_bottoni_segui(page):
    """
    DEBUG: stampa testo e background-color dei primi bottoni trovati.
    Per ora NON clicca nulla, solo logga i dati che ci servono.
    """
    bottoni_da_cliccare = []

    all_buttons = page.locator("button")
    count = all_buttons.count()
    print(f"Bottoni totali trovati: {count}")

    for i in range(count):
        btn = all_buttons.nth(i)
        try:
            if not btn.is_visible():
                continue

            bg = btn.evaluate(
                "el => window.getComputedStyle(el).getPropertyValue('background-color')"
            )
            txt = (btn.inner_text() or "").strip()

            # per debug: primi 15 bottoni
            if i < 15:
                print(f"Bottone {i}: text='{txt}', background-color='{bg}'")

        except Exception as e:
            print(f"Errore leggendo colore bottone {i}: {e}")
            continue

    # per ora NON clicchiamo niente
    return []


def segui_account_suggeriti(page):
    """Naviga sulla pagina dei suggeriti e (più avanti) seguirà gli account."""
    print("Navigo sulla pagina degli account suggeriti...")
    page.goto(SUGGERITI_URL, timeout=60000)
    page.wait_for_timeout(5000)

    # Verifica che il login sia andato a buon fine
    if "accounts/login" in page.url:
        print("Errore: non loggato. I cookie potrebbero essere scaduti.")
        return

    print("Login confermato tramite cookie. Inizio follow (fase di debug)...")
    seguiti = 0
    tentativi_falliti = 0
    max_tentativi_falliti = 3  # pochi tentativi, ci basta vedere i log

    while seguiti < MAX_FOLLOW:
        try:
            chiudi_popup(page)

            bottoni = trova_bottoni_segui(page)

            # In debug, ci basta un giro di log e poi usciamo
            print("Fase debug completata, esco dal loop.")
            break

        except Exception as e:
            print(f"Errore nel loop principale: {e}")
            tentativi_falliti += 1
            time.sleep(2)
            if tentativi_falliti >= max_tentativi_falliti:
                break
            continue

    print(f"Operazione (debug) completata. Account seguiti oggi: {seguiti}")


def main():
    if not COOKIES_JSON:
        print("Errore: INSTAGRAM_COOKIES non trovato. Aggiungi il secret su GitHub.")
        return
    try:
        with sync_playwright() as p:
            # per debug puoi mettere headless=False e slow_mo=500
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            ok = carica_cookies(context)
            if not ok:
                browser.close()
                return
            page = context.new_page()
            segui_account_suggeriti(page)
            browser.close()
    except PWTimeoutError:
        print("Timeout durante la navigazione.")
    except Exception as e:
        print(f"Errore imprevisto: {e}")


if __name__ == "__main__":
    main()
