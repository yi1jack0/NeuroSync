// Minimal IndexedDB wrapper: user presets (JSON) and user sound files (Blobs). Nothing leaves the device.
const DB = 'neurosync';
type Store = 'presets' | 'sounds';
let dbp: Promise<IDBDatabase> | null = null;

function db(): Promise<IDBDatabase> {
  dbp ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore('presets');
      req.result.createObjectStore('sounds');
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbp;
}

function tx<T>(store: Store, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return db().then((d) => new Promise<T>((resolve, reject) => {
    const t = d.transaction(store, mode);
    const r = fn(t.objectStore(store));
    // Resolve on *commit*, not on request success: otherwise closing the tab right after
    // "Saved" could still lose the write.
    t.oncomplete = () => resolve(r.result);
    t.onerror = t.onabort = () => reject(t.error ?? r.error);
  }));
}

export const idbGetAll = <T>(store: Store) => tx<T[]>(store, 'readonly', (s) => s.getAll() as IDBRequest<T[]>);
export const idbGet = <T>(store: Store, key: string) => tx<T | undefined>(store, 'readonly', (s) => s.get(key) as IDBRequest<T | undefined>);
export const idbPut = (store: Store, key: string, value: unknown) => tx(store, 'readwrite', (s) => s.put(value, key));
export const idbDelete = (store: Store, key: string) => tx(store, 'readwrite', (s) => s.delete(key));
