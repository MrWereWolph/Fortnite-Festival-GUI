const OWNED_STORAGE_KEY = "fnfest_gui5_owned_track_ids";

export function loadOwnedTrackIds() {
  try {
    const raw = localStorage.getItem(OWNED_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(parsed.map(Number).filter(Number.isFinite));
  } catch {
    return new Set();
  }
}

export function saveOwnedTrackIds(ownedIds) {
  const ids = Array.from(ownedIds).map(Number).filter(Number.isFinite);
  localStorage.setItem(OWNED_STORAGE_KEY, JSON.stringify(ids));
}

export function toggleOwnedTrackId(trackId) {
  const id = Number(trackId);
  const ownedIds = loadOwnedTrackIds();

  if (ownedIds.has(id)) {
    ownedIds.delete(id);
  } else {
    ownedIds.add(id);
  }

  saveOwnedTrackIds(ownedIds);
  return ownedIds;
}

export function clearOwnedTrackIds() {
  localStorage.removeItem(OWNED_STORAGE_KEY);
}
