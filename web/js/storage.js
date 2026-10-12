// Persistent storage for the simulated SD card and the device's internal
// flash, kept in IndexedDB.
//   * The SD card is shared by every device and version (like a real card).
//   * Flash is per device (settings, PIN, disclaimer), and survives "firmware"
//     version changes like on real hardware.

const DB_NAME = "krux-web";
const STORE = "files";

let dbPromise = null;

function db() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

function tx(mode, fn) {
  return db().then(
    (d) =>
      new Promise((resolve, reject) => {
        const t = d.transaction(STORE, mode);
        const out = fn(t.objectStore(STORE));
        t.oncomplete = () => resolve(out && "result" in out ? out.result : out);
        t.onerror = () => reject(t.error);
      }),
  );
}

// Maps a Krux path ("sd/x", "flash/y") to a storage key and back.
export function storageKey(device, path) {
  if (path.startsWith("sd/")) return "sd|" + path.slice(3);
  if (path.startsWith("flash/")) return "flash|" + device + "|" + path.slice(6);
  return null;
}

function keyToPath(key) {
  const parts = key.split("|");
  if (parts[0] === "sd") return { area: "sd", path: "sd/" + parts.slice(1).join("|") };
  return { area: "flash", device: parts[1], path: "flash/" + parts.slice(2).join("|") };
}

export async function putFile(device, path, data) {
  const key = storageKey(device, path);
  if (key) await tx("readwrite", (s) => s.put(new Uint8Array(data), key));
}

export async function deleteFile(device, path) {
  const key = storageKey(device, path);
  if (key) await tx("readwrite", (s) => s.delete(key));
}

async function allEntries() {
  const d = await db();
  return new Promise((resolve, reject) => {
    const out = [];
    const req = d.transaction(STORE).objectStore(STORE).openCursor();
    req.onsuccess = () => {
      const c = req.result;
      if (!c) return resolve(out);
      out.push([c.key, c.value]);
      c.continue();
    };
    req.onerror = () => reject(req.error);
  });
}

// Files to load into a device before boot: [{path, data}]
export async function filesFor(device) {
  const out = [];
  for (const [key, data] of await allEntries()) {
    const k = keyToPath(key);
    if (k.area === "sd" || k.device === device) out.push({ path: k.path, data });
  }
  return out;
}

export async function sdFiles() {
  const out = [];
  for (const [key, data] of await allEntries()) {
    const k = keyToPath(key);
    if (k.area === "sd") out.push({ path: k.path, name: k.path.slice(3), data });
  }
  out.sort((a, b) => a.name.localeCompare(b.name));
  return out;
}

export async function clearArea(area, device) {
  for (const [key] of await allEntries()) {
    const k = keyToPath(key);
    if (k.area === area && (area === "sd" || k.device === device)) {
      await tx("readwrite", (s) => s.delete(key));
    }
  }
}
