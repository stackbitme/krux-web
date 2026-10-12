# Simulador Krux no navegador

A Krux de verdade rodando dentro do navegador, para estudar e apresentar. O código
da Krux não é alterado: é o mesmo `src/` da versão oficial, executado num Python
que roda no navegador (Pyodide). Só a camada que finge ser o hardware (tela, toque,
botões, câmera, cartão SD) foi refeita para o navegador.

Versão incluída: **Krux v26.09.0**, dispositivo **Maix Amigo**.

## Como abrir

Precisa do Python 3 instalado (só ele, sem pacotes extras). Funciona sem internet.

| Sistema | Como abrir |
| --- | --- |
| macOS | Duplo clique em `Iniciar simulador (Mac).command`. Na primeira vez o macOS pode bloquear: clique com o botão direito, **Abrir**. |
| Windows | Duplo clique em `Iniciar simulador (Windows).bat`. Se não tiver Python, instale em python.org. |
| Linux | `./iniciar-simulador.sh` |
| Qualquer um | No terminal, dentro desta pasta: `python3 serve.py` |

O navegador abre em `http://localhost:8000`. Para encerrar, feche a janela do
terminal (ou Ctrl+C).

Abrir o `index.html` direto (duplo clique no arquivo) **não funciona**: o navegador
só libera a memória compartilhada que o simulador usa quando a página vem de um
servidor.

## Usando

- **Tela:** clique ou toque na tela do aparelho.
- **Botões:** Enter, seta para baixo (próximo) e seta para cima (anterior), ou os
  botões no painel. Como no aparelho, o primeiro aperto de botão só ativa o modo
  de botões.
- **Câmera:** quando a Krux abre a câmera, escolha a fonte no painel:
  - **Webcam**;
  - **Tela ou janela**: o navegador pergunta o que compartilhar (tela inteira,
    uma janela ou uma aba, por exemplo a do Ian Coleman). Na primeira vez no Mac,
    libere "Gravação de Tela" para o navegador em Ajustes do Sistema;
  - **Imagem**: no campo logo abaixo, arraste uma imagem de QR (de uma pasta ou
    de outra aba do navegador), cole com Ctrl+V / Cmd+V ou use "Colar imagem" e
    "Escolher arquivo".

  Para a Krux ler só uma parte da imagem (útil quando há mais de um QR na tela),
  use "Selecionar área": abre a imagem grande para você desenhar um retângulo em
  volta do QR. Ao compartilhar a tela, esse seletor abre sozinho. QR animados
  (PSBT, UR, BBQr) funcionam.
- **Cartão SD:** adicione arquivos (botão ou arrastando para a página), baixe,
  apague, exporte tudo em `.zip` ou importe um `.zip`. Funciona com a Krux ligada.
  No Chrome e no Edge dá para usar **uma pasta do computador** como cartão: o que
  a Krux gravar aparece na pasta.
- **Memória interna:** configurações, PIN e o aceite do aviso inicial ficam
  guardados por dispositivo. "Apagar memória interna" volta ao estado de fábrica.
- **Apresentar:** esconde os painéis e aumenta o aparelho (Esc para sair).
- **Capturar tela:** baixa um PNG da tela da Krux em 2x, bom para slides.
- **Link direto:** `?v=v26.09.0&device=amigo&lang=pt-BR` abre sem passar pelo
  menu inicial. O botão "Copiar link desta configuração" gera esse link.

Tudo fica salvo só neste navegador (IndexedDB). Limpar os dados do site apaga o
cartão e a memória interna.

## Publicar no site

Suba a pasta `web/` inteira para qualquer hospedagem de arquivos estáticos
(subdomínio, GitHub Pages, Netlify, Cloudflare Pages, um servidor seu).

- O simulador precisa estar "isolado" (cabeçalhos `Cross-Origin-Opener-Policy:
  same-origin` e `Cross-Origin-Embedder-Policy: require-corp`). Se a hospedagem
  permite configurar cabeçalhos, configure. Se não permite (GitHub Pages), o
  arquivo `coi-serviceworker.js` já incluído resolve sozinho.
- Use HTTPS, senão o navegador bloqueia a câmera.
- **Não funciona dentro de um iframe** num site comum (WordPress e afins): o
  navegador só isola a página se a página de fora também for isolada. Use um link
  ou um subdomínio próprio, por exemplo `krux.stackbit.me`.
- O primeiro carregamento baixa uns 15 MB (o Python). Depois fica em cache.

## Atualizar para uma versão nova da Krux

O que muda por versão fica em `web/versions/<versão>/`. Para gerar uma nova:

1. Baixe a versão nova da Krux com os submódulos:
   ```
   git clone --branch v26.10.0 --recurse-submodules https://github.com/selfcustody/krux.git
   ```
2. Tenha `clang` e `wasm-ld` (para compilar a biblioteca bc-ur da Krux em
   WebAssembly): no macOS `brew install llvm lld`; no Debian/Ubuntu
   `apt install clang lld`; no Windows, o instalador do LLVM.
3. Rode:
   ```
   python3 tools/build.py --krux ../krux --tag v26.10.0
   ```
   Isso gera `web/versions/v26.10.0/` e atualiza a lista de versões do menu.
4. Teste (veja abaixo). Se algo da camada de simulação mudou na Krux, os testes
   mostram onde.

Para liberar outros dispositivos, adicione-os em `ENABLED_DEVICES` no
`tools/build.py` e gere de novo. A camada de simulação já trata todos os modelos
que o simulador oficial trata, mas só o Amigo foi testado.

## Como funciona

```
navegador (página)                         Web Worker
──────────────────                         ──────────────────────────────────
tela (canvas)  ◄── memória compartilhada ── Pyodide (Python 3.12)
toque, botões  ──►         (SharedArrayBuffer) ├─ Krux src/ (sem alterações)
câmera + zbar  ──► quadros e QR lidos          ├─ kruxsim (mocks do simulador oficial)
cartão SD      ◄─► arquivos                     ├─ runtime/kruxweb (tela, toque,
IndexedDB                                      │   câmera, SD para o navegador)
                                               └─ ur.wasm (bc-ur da Krux em C)
```

- A Krux roda como no aparelho: num laço que nunca devolve o controle. Por isso
  ela fica num Web Worker e conversa com a página por memória compartilhada; as
  esperas usam `Atomics.wait` e acordam na hora quando você toca ou aperta algo.
- A tela é desenhada em Python, reproduzindo pixel a pixel o que o pygame faz no
  simulador oficial (fontes BDF da Krux, retângulos, círculos, linhas).
- O módulo `uUR` (QR animados) é a biblioteca C da própria Krux compilada para
  WebAssembly, com a mesma interface do módulo nativo.
- AES (`ucryptolib`) é uma implementação em Python compatível com o pycryptodome;
  PBKDF2 usa `@noble/hashes`.
- QR codes são lidos com o zbar (o mesmo do simulador oficial, via pyzbar).

## Testes

`tests/run_all.sh` (com `KRUX_DIR` apontando para a Krux da mesma versão, com o
ambiente do simulador oficial instalado, e `npm install` dentro de `tests/`) verifica:

1. texto de todas as traduções e as formas desenhadas idênticos ao pygame;
2. AES idêntico ao pycryptodome (ECB, CBC, CTR, GCM);
3. KEF, PBKDF2 e seed BIP39 idênticos ao Python nativo;
4. `uUR` em wasm idêntico ao módulo nativo da Krux nos casos de teste do bc-ur;
5. assinatura de uma PSBT de ponta a ponta, lendo o QR assinado da tela e
   comparando com o embit nativo.

`tests/browser/` tem testes no Chromium (Playwright): boot, leitura de QR por
imagem, carteira, cartão SD, teclado, apresentação, celular, desligar e religar,
webcam, captura de tela e seleção de região.

## Limitações conhecidas

- Testado no Chromium. Firefox e Safari devem funcionar, mas não foram testados.
- "Usar uma pasta do computador" só existe no Chrome e no Edge.
- Ler uma TinySeed fotografada pela câmera não funciona (também não funciona no
  simulador oficial).
- Impressora não é simulada.

## Licenças

Este projeto: MIT. Componentes de terceiros e suas licenças estão em
`THIRD_PARTY.md`. Krux é © Krux contributors, licença MIT. Este simulador não é
um projeto oficial da Krux.
