import os
import json
import requests
from bs4 import BeautifulSoup
from shopee_afflib import ShopeeAffiliate

# --- Configurações (vêm dos Secrets do GitHub) ---
SHOPEE_APP_ID = os.environ.get("SHOPEE_APP_ID")
SHOPEE_SECRET = os.environ.get("SHOPEE_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def buscar_shopee():
    """Busca ofertas na API de afiliados da Shopee."""
    ofertas = []
    try:
        client = ShopeeAffiliate(app_id=SHOPEE_APP_ID, secret=SHOPEE_SECRET)
        # Exemplo: busca ofertas com desconto. Ajuste os parâmetros conforme a documentação.
        response = client.product_offer_v2(limit=20, sort_by="sales")
        for item in response.get("data", {}).get("item", []):
            info = item.get("item_basic", {})
            ofertas.append({
                "plataforma": "Shopee",
                "titulo": info.get("name", "Oferta Shopee"),
                "preco": info.get("price", 0) / 100000,  # A API retorna em centavos
                "link": info.get("offer_link", "#"),
                "imagem": f"https://cf.shopee.com.br/file/{info.get('image', '')}"
            })
    except Exception as e:
        print(f"Erro na Shopee: {e}")
    return ofertas

def buscar_mercadolivre():
    """Scraping simples para o Mercado Livre (pode falhar se o site mudar)."""
    ofertas = []
    try:
        url = "https://www.mercadolivre.com.br/ofertas"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".promotion-item")[:10]  # Seleciona os primeiros 10 cards
        for card in cards:
            titulo = card.select_one(".promotion-item__title")
            preco = card.select_one(".andes-money-amount__fraction")
            link = card.select_one("a")
            img = card.select_one("img")
            if titulo and preco and link:
                ofertas.append({
                    "plataforma": "Mercado Livre",
                    "titulo": titulo.get_text(strip=True),
                    "preco": float(preco.get_text(strip=True).replace(".", "").replace(",", ".")),
                    "link": link.get("href", "#"),
                    "imagem": img.get("src") if img else ""
                })
    except Exception as e:
        print(f"Erro no Mercado Livre: {e}")
    return ofertas

def enviar_telegram(ofertas):
    """Envia um resumo das ofertas para o Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram não configurado. Pulando envio.")
        return
    
    mensagem = "🛒 *Melhores Ofertas de Hoje*\n\n"
    for of in ofertas[:5]:  # Envia as 5 primeiras para não floodar
        mensagem += f"*{of['plataforma']}*: {of['titulo']}\n"
        mensagem += f"💰 R$ {of['preco']:.2f}\n"
        mensagem += f"[Ver oferta]({of['link']})\n\n"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

if __name__ == "__main__":
    print("Iniciando coleta...")
    todas = buscar_shopee() + buscar_mercadolivre()
    todas.sort(key=lambda x: x["preco"])  # Ordena do mais barato para o mais caro
    
    # Salva o JSON que o painel vai ler
    with open("ofertas.json", "w", encoding="utf-8") as f:
        json.dump(todas, f, ensure_ascii=False, indent=2)
    
    enviar_telegram(todas)
    print(f"Coleta finalizada. {len(todas)} ofertas salvas.")
