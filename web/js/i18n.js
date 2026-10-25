// Page language (the simulator's own interface; Krux has its own language
// setting). English is the default; the choice is remembered per browser and
// can be forced with ?ui=pt or ?ui=en.

export const UI_LANGS = { en: "English", pt: "Português" };
export const DEFAULT_UI = "en";

const STRINGS = {
  en: {
    "title": "Krux Simulator",
    "meta.description": "Krux running in the browser, for study and presentations.",
    "ui.lang": "Page language",
    "bar.session": "Session",
    "bar.shot": "Screenshot",
    "bar.shot.title": "Download the current screen as a PNG",
    "bar.present": "Present",
    "bar.present.title": "Hides the panels and enlarges the device (Esc to exit)",
    "bar.change": "Change version",
    "mat.label": "Device",

    "launcher.lead": "The real Krux, running in your browser, for study and presentations.",
    "launcher.version": "Version",
    "launcher.device": "Device",
    "launcher.lang": "Krux language",
    "launcher.start": "Power on",
    "launcher.fine": "The SD card and settings are saved in this browser. Nothing leaves your computer.",
    "launcher.notice": "For educational purposes only. Read the notice",
    "launcher.latest": "{v} (latest)",
    "launcher.keepLang": "Keep what is saved",

    "lcd.label": "Krux screen",
    "keys.hint": "Click the screen to tap. Keyboard: Enter, ↓ and ↑ act as the buttons.",
    "present.exit": "Exit presentation",

    "cam.title": "Camera",
    "cam.source": "Camera source",
    "cam.webcam": "Webcam",
    "cam.screen": "Screen or window",
    "cam.image": "QR image",
    "cam.drop": "Drag a QR image here or paste with {key}",
    "cam.paste": "Paste image",
    "cam.choose": "Choose file",
    "cam.empty": "A preview of what Krux will see appears here.",
    "cam.hint": "Mark the QR so Krux reads only that part: drag over the preview or use \"Select area\".",
    "cam.pick": "Select area",
    "cam.full": "Use the whole image",
    "cam.stop": "Stop",
    "cam.status.reading": "reading",
    "cam.status.waiting": "Krux is waiting",
    "cam.status.off": "off in Krux",
    "cam.lastQR": "Last QR read: {n} bytes, at {time}",
    "cam.denied": "Permission denied. Allow access in the browser and try again.",
    "cam.notFound": "No camera found.",
    "cam.cantOpen": "Could not open this source: {err}",
    "cam.notImage": "This file is not an image the browser can open.",
    "cam.imageLoaded": "Image loaded as the camera source.",
    "cam.imagePasted": "Image pasted as the camera source.",
    "cam.dragFail": "Could not get this image from the other site. Copy the image (right click, Copy image) and paste it here.",
    "cam.clipNoImage": "The clipboard has no image. Copy the QR image (not its link) and paste again.",
    "cam.clipNoImageBtn": "The clipboard has no image. Copy the QR image and try again.",
    "cam.clipUnsupported": "This browser does not let the button read the clipboard. Use {key}.",
    "cam.clipDenied": "The browser did not allow access to the clipboard. Use {key}.",

    "picker.title": "Mark the QR code",
    "picker.text": "Drag a rectangle around the QR. Krux will read only that part. You can redo it as many times as you like. You can also drop or paste another image here.",
    "picker.all": "Use the whole image",
    "picker.done": "Done",

    "sd.title": "SD card",
    "sd.drop": "Drop files here to write them to the card",
    "sd.add": "Add files",
    "sd.zip": "Download .zip",
    "sd.import": "Import .zip",
    "sd.folder": "Use a folder on this computer",
    "sd.folderStop": "Stop using the folder",
    "sd.folderNote": "The card now mirrors the folder \"{name}\": whatever Krux writes shows up there. Files added to the folder from outside come in when Krux restarts.",
    "sd.folderLoaded": "Folder \"{name}\" loaded. Restarting Krux with it.",
    "sd.folderWriteFail": "Could not write to the folder: {err}",
    "sd.clear": "Empty card",
    "sd.clearConfirm": "Confirm: empty",
    "sd.cleared": "Card emptied.",
    "sd.empty": "Empty card. Add a PSBT, a backup or any file for Krux to read.",
    "sd.download": "Download",
    "sd.delete": "Delete",
    "sd.status.one": "1 file, {size}",
    "sd.status.many": "{n} files, {size}",
    "sd.tooBig": "File too large to send while Krux is on. It goes into the card on the next boot.",
    "sd.written.one": "File written to the card.",
    "sd.written.many": "{n} files written to the card.",
    "sd.zipEmpty": "The card is empty.",
    "sd.zipName": "krux-sd-card.zip",
    "sd.zipBad": "Could not open this .zip.",
    "sd.imported.one": "1 file imported to the card.",
    "sd.imported.many": "{n} files imported to the card.",

    "buttons.title": "Buttons",
    "buttons.enter": "Enter",
    "buttons.next": "Next",
    "buttons.prev": "Previous",

    "session.title": "Session",
    "session.restart": "Restart Krux",
    "session.link": "Copy link to this setup",
    "session.flash": "Erase internal memory",
    "session.flashConfirm": "Confirm: erase",
    "session.flashErased": "Internal memory erased.",
    "session.hint": "Internal memory holds this device's settings, PIN and the acceptance of Krux's initial notice.",
    "session.log": "Krux log",
    "session.linkCopied": "Link copied. It opens straight into this version, device and language.",
    "session.label": "Krux {v} on {device}",
    "session.docTitle": "Krux {v}, {device}",

    "boot.python": "Loading Python…",
    "boot.krux": "Loading Krux…",
    "boot.boot": "Starting…",
    "boot.crash": "Krux stopped with an error.",
    "boot.restart": "Restart",
    "boot.off": "Krux was powered off.",
    "boot.on": "Power on",
    "boot.indexFail": "Could not load the list of versions: {err}",
    "boot.fetchFail": "{status} while fetching {url}",

    "blocked.title": "Open it through the local server",
    "blocked.p1": "The simulator needs a browser feature (shared memory) that does not work when the file is opened directly.",
    "blocked.p2": "In the project folder, run <code>python3 serve.py</code> and open <a href=\"http://localhost:8000\">http://localhost:8000</a>.",

    "notice.kicker": "Before you start",
    "notice.title": "For educational purposes only",
    "notice.intro": "This is an unofficial simulator of Krux, made for study, teaching and presentations. It is not a wallet.",
    "notice.p1": "<strong>Do not use real funds.</strong> Do not load seeds, keys or backups that control, or will control, real bitcoin. A web browser is not a safe place for keys.",
    "notice.p2": "<strong>Not official.</strong> Not affiliated with or endorsed by the Krux project. Krux is © Krux contributors, MIT license, and runs here unmodified.",
    "notice.p3": "<strong>No warranty.</strong> Provided as is. Behavior may differ from a real device. You are responsible for how you use it.",
    "notice.ok": "I understand",
  },

  pt: {
    "title": "Simulador Krux",
    "meta.description": "A Krux rodando no navegador, para estudar e apresentar.",
    "ui.lang": "Idioma da página",
    "bar.session": "Sessão",
    "bar.shot": "Capturar tela",
    "bar.shot.title": "Baixar a tela atual em PNG",
    "bar.present": "Apresentar",
    "bar.present.title": "Esconde os painéis e aumenta o aparelho (Esc para sair)",
    "bar.change": "Trocar versão",
    "mat.label": "Aparelho",

    "launcher.lead": "A Krux de verdade, rodando no navegador, para estudar e apresentar.",
    "launcher.version": "Versão",
    "launcher.device": "Dispositivo",
    "launcher.lang": "Idioma da Krux",
    "launcher.start": "Ligar",
    "launcher.fine": "O cartão SD e as configurações ficam salvos neste navegador. Nada sai do seu computador.",
    "launcher.notice": "Apenas para fins educacionais. Ler o aviso",
    "launcher.latest": "{v} (mais recente)",
    "launcher.keepLang": "Manter o que estiver salvo",

    "lcd.label": "Tela da Krux",
    "keys.hint": "Clique na tela para tocar. Teclado: Enter, ↓ e ↑ fazem as vezes dos botões.",
    "present.exit": "Sair da apresentação",

    "cam.title": "Câmera",
    "cam.source": "Fonte da câmera",
    "cam.webcam": "Webcam",
    "cam.screen": "Tela ou janela",
    "cam.image": "Imagem de QR",
    "cam.drop": "Arraste uma imagem de QR para cá ou cole com {key}",
    "cam.paste": "Colar imagem",
    "cam.choose": "Escolher arquivo",
    "cam.empty": "A prévia do que a Krux vai ver aparece aqui.",
    "cam.hint": "Marque o QR para a Krux ler só aquela parte: arraste sobre a prévia ou use \"Selecionar área\".",
    "cam.pick": "Selecionar área",
    "cam.full": "Usar a imagem toda",
    "cam.stop": "Parar",
    "cam.status.reading": "lendo",
    "cam.status.waiting": "a Krux está esperando",
    "cam.status.off": "desligada na Krux",
    "cam.lastQR": "Último QR lido: {n} bytes, às {time}",
    "cam.denied": "Permissão negada. Libere o acesso no navegador e tente de novo.",
    "cam.notFound": "Nenhuma câmera encontrada.",
    "cam.cantOpen": "Não deu para abrir essa fonte: {err}",
    "cam.notImage": "Esse arquivo não é uma imagem que o navegador consiga abrir.",
    "cam.imageLoaded": "Imagem carregada como fonte da câmera.",
    "cam.imagePasted": "Imagem colada como fonte da câmera.",
    "cam.dragFail": "Não consegui pegar essa imagem do outro site. Copie a imagem (botão direito, Copiar imagem) e cole aqui.",
    "cam.clipNoImage": "A área de transferência não tem uma imagem. Copie a imagem do QR (não o link) e cole de novo.",
    "cam.clipNoImageBtn": "A área de transferência não tem uma imagem. Copie a imagem do QR e tente de novo.",
    "cam.clipUnsupported": "Este navegador não deixa o botão ler a área de transferência. Use {key}.",
    "cam.clipDenied": "O navegador não liberou a área de transferência. Use {key}.",

    "picker.title": "Marque o QR code",
    "picker.text": "Arraste um retângulo em volta do QR. A Krux vai ler só essa parte. Dá para refazer quantas vezes quiser. Você também pode soltar ou colar outra imagem aqui.",
    "picker.all": "Usar a imagem toda",
    "picker.done": "Pronto",

    "sd.title": "Cartão SD",
    "sd.drop": "Solte arquivos aqui para gravar no cartão",
    "sd.add": "Adicionar arquivos",
    "sd.zip": "Baixar .zip",
    "sd.import": "Importar .zip",
    "sd.folder": "Usar uma pasta do computador",
    "sd.folderStop": "Parar de usar a pasta",
    "sd.folderNote": "O cartão agora espelha a pasta \"{name}\": o que a Krux gravar aparece lá. Arquivos colocados na pasta por fora entram ao reiniciar a Krux.",
    "sd.folderLoaded": "Pasta \"{name}\" carregada. Reiniciando a Krux com ela.",
    "sd.folderWriteFail": "Não consegui gravar na pasta: {err}",
    "sd.clear": "Esvaziar cartão",
    "sd.clearConfirm": "Confirmar: esvaziar",
    "sd.cleared": "Cartão esvaziado.",
    "sd.empty": "Cartão vazio. Adicione uma PSBT, um backup ou qualquer arquivo para a Krux ler.",
    "sd.download": "Baixar",
    "sd.delete": "Apagar",
    "sd.status.one": "1 arquivo, {size}",
    "sd.status.many": "{n} arquivos, {size}",
    "sd.tooBig": "Arquivo grande demais para enviar com a Krux ligada. Ele entra no cartão no próximo boot.",
    "sd.written.one": "Arquivo gravado no cartão.",
    "sd.written.many": "{n} arquivos gravados no cartão.",
    "sd.zipEmpty": "O cartão está vazio.",
    "sd.zipName": "cartao-sd-krux.zip",
    "sd.zipBad": "Não foi possível abrir esse .zip.",
    "sd.imported.one": "1 arquivo importado para o cartão.",
    "sd.imported.many": "{n} arquivos importados para o cartão.",

    "buttons.title": "Botões",
    "buttons.enter": "Enter",
    "buttons.next": "Próximo",
    "buttons.prev": "Anterior",

    "session.title": "Sessão",
    "session.restart": "Reiniciar a Krux",
    "session.link": "Copiar link desta configuração",
    "session.flash": "Apagar memória interna",
    "session.flashConfirm": "Confirmar: apagar",
    "session.flashErased": "Memória interna apagada.",
    "session.hint": "A memória interna guarda configurações, PIN e o aceite do aviso inicial da Krux deste dispositivo.",
    "session.log": "Registro da Krux",
    "session.linkCopied": "Link copiado. Ele abre direto nesta versão, dispositivo e idioma.",
    "session.label": "Krux {v} no {device}",
    "session.docTitle": "Krux {v}, {device}",

    "boot.python": "Carregando o Python…",
    "boot.krux": "Carregando a Krux…",
    "boot.boot": "Ligando…",
    "boot.crash": "A Krux parou com um erro.",
    "boot.restart": "Reiniciar",
    "boot.off": "A Krux foi desligada.",
    "boot.on": "Ligar",
    "boot.indexFail": "Não foi possível carregar a lista de versões: {err}",
    "boot.fetchFail": "{status} ao baixar {url}",

    "blocked.title": "Abra pelo servidor local",
    "blocked.p1": "O simulador precisa de um recurso do navegador (memória compartilhada) que não funciona abrindo o arquivo direto.",
    "blocked.p2": "Na pasta do projeto, rode <code>python3 serve.py</code> e abra <a href=\"http://localhost:8000\">http://localhost:8000</a>.",

    "notice.kicker": "Antes de começar",
    "notice.title": "Apenas para fins educacionais",
    "notice.intro": "Este é um simulador não oficial da Krux, feito para estudo, ensino e apresentações. Não é uma carteira.",
    "notice.p1": "<strong>Não use fundos reais.</strong> Não carregue seeds, chaves ou backups que controlem, ou vão controlar, bitcoin de verdade. Um navegador não é um lugar seguro para chaves.",
    "notice.p2": "<strong>Não é oficial.</strong> Sem vínculo com o projeto Krux nem endosso dele. A Krux é © Krux contributors, licença MIT, e roda aqui sem alterações.",
    "notice.p3": "<strong>Sem garantia.</strong> Fornecido como está. O comportamento pode ser diferente de um aparelho real. O uso é por sua conta.",
    "notice.ok": "Entendi",
  },
};

const LOCALE = { en: "en-US", pt: "pt-BR" };

function pick() {
  const q = new URLSearchParams(location.search).get("ui");
  if (q && STRINGS[q.slice(0, 2).toLowerCase()]) return q.slice(0, 2).toLowerCase();
  try {
    const saved = localStorage.getItem("krux-web:ui");
    if (saved && STRINGS[saved]) return saved;
  } catch { /* private mode */ }
  return DEFAULT_UI;
}

let current = pick();
const listeners = [];

export function uiLang() {
  return current;
}

export function locale() {
  return LOCALE[current];
}

export function t(key, vars) {
  let s = STRINGS[current][key] ?? STRINGS.en[key] ?? key;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return s;
}

// Applies the strings to the static markup:
//   data-i18n="key"        text content
//   data-i18n-html="key"   inner HTML (trusted strings from this file only)
//   data-i18n-title="key"  title attribute
//   data-i18n-aria="key"   aria-label attribute
export function applyStatic(root = document) {
  document.documentElement.lang = LOCALE[current];
  document.title = t("title");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("meta.description"));
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of root.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);
  for (const el of root.querySelectorAll("[data-i18n-title]")) el.title = t(el.dataset.i18nTitle);
  for (const el of root.querySelectorAll("[data-i18n-aria]")) el.setAttribute("aria-label", t(el.dataset.i18nAria));
}

export function setUILang(lang) {
  if (!STRINGS[lang] || lang === current) return;
  current = lang;
  try { localStorage.setItem("krux-web:ui", lang); } catch { /* private mode */ }
  applyStatic();
  for (const fn of listeners) fn(lang);
}

export function onUILang(fn) {
  listeners.push(fn);
}
