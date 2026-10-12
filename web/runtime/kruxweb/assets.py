# Krux Web Simulator - access to static assets served next to the page.
import os

FONT_DIR = "/krux/fonts"


def fetch_bytes(url):
    """Synchronous fetch (allowed inside Web Workers)."""
    from js import XMLHttpRequest, Uint8Array

    xhr = XMLHttpRequest.new()
    xhr.open("GET", url, False)
    xhr.responseType = "arraybuffer"
    xhr.send(None)
    if xhr.status != 200:
        raise OSError("fetch failed (%s): %s" % (xhr.status, url))
    return Uint8Array.new(xhr.response).to_bytes()


def font_bytes(name):
    path = os.path.join(FONT_DIR, name + ".kfnt")
    if not os.path.exists(path):
        import _kxio

        data = fetch_bytes(_kxio.fontsURL + name + ".kfnt")
        os.makedirs(FONT_DIR, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return data
    with open(path, "rb") as f:
        return f.read()
