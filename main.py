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
    Trova i bottoni 'Segui' / 'Follow' in modo il più generico possibile.
    1) Prova a prendere direttamente i bottoni con testo Segui/Follow.
    2) Se non trova nulla, guarda card dei suggeriti e prende il bottone
       nella card che ha testo Segui/Follow.
    Restituisce una lista di locator dei bottoni da cliccare.
    """

    bottoni_da_cliccare = []

    # 1) Direct: ruolo + testo (più robusto ai piccoli cambi HTML)
    for label in ["Segui", "Follow"]:
        btns = page.get_by_role("button", name=label)
        if btns.count() > 0:
            bottoni_da_cliccare.extend(btns.all())

    if bottoni_da_cliccare:
        print(f"Trovati {len(bottoni_da_cliccare)} bottoni tramite get_by_role.")
        return bottoni_da_cliccare

    # 2) Per sicurezza: qualsiasi button che contiene il testo
    for label in ["Segui", "Follow"]:
        btns = page.locator(f"button:has-text('{label}')")
        if btns.count() > 0:
            bottoni_da_cliccare.extend(btns.all())

    if bottoni_da_cliccare:
        print(f"Trovati {len(bottoni_da_cliccare)} bottoni tramite :has-text.")
        return bottoni_da_cliccare

    # 3) Fallback: lavoro per card dei suggeriti
    cards = page.locator("article, div[role='presentation']").all()
    print(f"Card suggeriti trovate: {len(cards)}")

    for card in cards:
        # dentro ogni card, cerca button o div[role='button']
        buttons = card.locator("button, div[role='button']").all()
        for btn in buttons:
            try:
                txt = (btn.inner_text() or "").strip().lower()
            except Exception:
                txt = ""

            # clicca solo se il testo contiene segui/follow
            if "segui" in txt or "follow" in txt:
                bottoni_da_cliccare.append(btn)
                break  # passa alla prossima card

    print(f"Bottoni Segui/Follow trovati nelle card: {len(bottoni_da_cliccare)}")
    return bottoni_da_cliccare


def segui_account_suggeriti(page):
    """Naviga sulla pagina dei suggeriti e segue gli account."""
    print("Navigo sulla pagina degli account suggeriti...")
    page.goto(SUGGERITI_URL, timeout=60000)
    page.wait_for_timeout(5000)

    # Verifica che il login sia andato a buon fine
    if "accounts/login" in page.url:
        print("Errore: non loggato. I cookie potrebbero essere scaduti.")
        return

    print("Login confermato tramite cookie. Inizio follow...")
    seguiti = 0
    tentativi_falliti = 0
    max_tentativi_falliti = 10  # Dopo 10 errori consecutivi ricarica la pagina

    while seguiti < MAX_FOLLOW:
        try:
            chiudi_popup(page)

            # Trova bottoni in modo robusto
            bottoni = trova_bottoni_segui(page)

            if not bottoni:
                print("Nessun bottone Segui trovato. Ricarico la pagina...")
                page.goto(SUGGERITI_URL, timeout=60000)
                page.wait_for_timeout(4000)
                tentativi_falliti += 1
                if tentativi_falliti >= max_tentativi_falliti:
                    print("Troppi tentativi falliti. Uscita.")
                    break
                continue

            cliccato = False
            for bottone in bottoni:
                try:
                    chiudi_popup(page)
                    bottone.scroll_into_view_if_needed()
                    bottone.click(timeout=3000, force=True)
                    page.wait_for_timeout(1000)  # dai tempo al cambio stato

                    seguiti += 1
                    tentativi_falliti = 0
                    print(f"Seguito account {seguiti}/{MAX_FOLLOW}")
                    cliccato = True

                    time.sleep(2)

                    if seguiti % 5 == 0:
                        page.reload()
                        page.wait_for_timeout(4000)

                    break  # passa al prossimo ciclo while

                except Exception as e:
                    print(f"Errore click bottone: {e}")
                    chiudi_popup(page)
                    continue

            if not cliccato:
                tentativi_falliti += 1
                print(f"Nessun bottone cliccabile trovato (tentativo {tentativi_falliti})")
                page.keyboard.press("End")
                time.sleep(2)
                if tentativi_falliti >= max_tentativi_falliti:
                    page.goto(SUGGERITI_URL, timeout=60000)
                    page.wait_for_timeout(4000)
                    tentativi_falliti = 0

        except Exception as e:
            print(f"Errore nel loop principale: {e}")
            tentativi_falliti += 1
            time.sleep(2)
            continue

    print(f"Operazione completata. Account seguiti oggi: {seguiti}")


def main():
    if not COOKIES_JSON:
        print("Errore: INSTAGRAM_COOKIES non trovato. Aggiungi il secret su GitHub.")
        return
    try:
        with sync_playwright() as p:
            # per debug locale puoi mettere headless=False e slow_mo=500
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
