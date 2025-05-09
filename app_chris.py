import os
import sys
import chainlit as cl
import shutil
import base64
from pathlib import Path
from dotenv import load_dotenv
from time import sleep
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI

# Ajuste o caminho do browser_use conforme sua máquina
sys.path.append("/Users/christian/Documents/GitHub/browser-use")

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig

# Carrega variáveis de ambiente
load_dotenv()

# Caminho de destino para os downloads
DOWNLOAD_PATH = Path("/Users/christian/Documents/Documents/UFG/Oficina Conectada/Chainlit")

# Inicializa LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    temperature=0.0
)

# Inicializa navegador com pasta de download definida
browser = Browser(
    config=BrowserConfig(
        new_context_config=BrowserContextConfig(
            save_downloads_path=str(DOWNLOAD_PATH),
            #accept_downloads=True  # garante que o navegador aceite baixar arquivos
        )
    )
)

# Dados fixos para compor instrução
models = ['ecosport', 'courier', 'edge', 'fiesta-rocam', 'focus', 'fusion', 'fusion-hibrido', 'ka', 'new-fiesta', 'new-fiesta-sedan', 'ranger']
years = ['2009', '2010', '2011', '2012', '2013', '2014', '2015']
systems = ['carroceria', 'motor', 'semi-arvores', 'sistema-de-combustivel', 'sistema-de-direcao', 'sistema-de-escapamento', 'sistema-de-freio', 'sistema-de-transmissao', 'sistema-eletrico', 'suspensao', 'informacoes-gerais']

def wait_for_download_completion(download_path, timeout=30):
    """Aguarda até que um novo PDF apareça na pasta de download."""
    for _ in range(timeout):
        files = list(download_path.glob("*.pdf"))
        if files:
            return max(files, key=lambda f: f.stat().st_mtime)
        sleep(1)
    return None

@cl.step(type="tool")
async def ford_agent(user_request: str):
    task = f"""
    Você é um agente destinado a ajudar pessoas com problemas em carros da marca Ford. Seu objetivo é entender o que o usuário está precisando e retornar o material técnico mais adequado, 
    realizando uma busca no site do Reparador Ford. Existem duas maneiras possíveis para essa busca:

    # Maneira 1 - Busca por URL estruturada:
    Você pode utilizar a seguinte URL base: https://www.reparadorford.com.br/motorcraft/informacoes-tecnicas/model/year/system
    As palavras `model`, `year` e `system` são variáveis que devem ser substituídas por termos correspondentes às listas {models}, {years} e {systems}, respectivamente. Analise o pedido do usuário e escolha os termos mais apropriados para cada variável. 
    Caso mais de um termo se aplique bem ao contexto, você pode usar múltiplos valores separados por dois-pontos, como neste exemplo: `modelo1:modelo2:modelo3`
    Após definir a URL, acesse o site e clique em leia mais no arquivo que mais se relaciona com o problema do usuário. Você pode rolar a página, clicar em "carregar mais arquivos" e navegar livremente para encontrar o melhor resultado.
    Aguarde o carregamento da página e clique em baixar para baixar o arquivo, se necessário faça login com as credenciais fornecidas nas observações. 
    Após o download ser concluído, tire um print dessa tela.

    # Maneira 2 - Busca por expressão:
    Utilize a seguinte URL base: https://www.reparadorford.com.br/motorcraft/informacoes-tecnicas?busca=expressao
    Substitua a palavra `expressao` por uma frase ou palavra-chave que resuma da melhor forma o pedido do usuário. 
    Após definir a URL, realize a busca, clique em 'leia mais' no arquivo mais relevante, considerando sempre o modelo, ano e problema descrito pelo usuário. Você também pode rolar a página e carregar mais arquivos, se necessário.
    Aguarde o carregamento da página e clique em 'baixar' para baixar o arquivo e espere o download ser concluído, se necessário faça login com as credenciais fornecidas nas observações.
    Após o download ser concluído, tire um print dessa tela.

    ## Observações importantes:
    - Sempre analise o pedido do usuário com atenção para evitar alucinações;
    - Escolha livremente entre a Maneira 1 ou a Maneira 2, conforme o caso;
    - Usar somente as Urls fornecidas, podendo ser alteradas de acordo com o pedido do usuário;
    - Se o site solicitar login, use as seguintes credenciais:
      CPF: 406.967.091-20
      Senha: Diag2025!

    A seguir está o pedido do usuário:
    {user_request}
    """

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
        max_actions_per_step=8,
    )

    await agent.run(max_steps=25)

    # Aguarda o término do download
    latest_file = wait_for_download_completion(DOWNLOAD_PATH)

    # ✅ Tira print da aba atual
    page = await browser.get_current_page()
    screenshot_b64 = await page.screenshot(full_page=True)

    image_data = base64.b64decode(screenshot_b64)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/Users/christian/Documents/Documents/UFG/Oficina Conectada/Chainlit/screenshot_{timestamp}.png"

    with open(output_path, "wb") as f:
        f.write(image_data)

    print(f"📸 Screenshot salvo em: {output_path}")

    if latest_file is None:
        return "❌ O download do arquivo falhou ou demorou demais."

    file_name = latest_file.name

    # Construir link direto se for aplicável
    pdf_link = f"https://www.reparadorford.com.br/pdf/view/{file_name}"

    await cl.Message(
        content=f"📄 Arquivo técnico encontrado! [Clique aqui para visualizar o PDF]({pdf_link})"
    ).send()

    return "✅ Execução finalizada com sucesso!"

@cl.on_message
async def main(message: cl.Message):
    await cl.Message(content="🔍 Executando agente de busca...").send()

    response = await ford_agent(message.content)

    await cl.Message(content=response).send()