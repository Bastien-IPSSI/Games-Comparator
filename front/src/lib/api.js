const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:3001";

export async function fetchGames({ q = "", platform = "" } = {}) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (platform) params.set("platform", platform);
    const res = await fetch(`${BASE}/api/games?${params}`);
    if (!res.ok) throw new Error("Erreur lors du chargement des jeux");
    return res.json();
}

export async function fetchGame(id) {
    const res = await fetch(`${BASE}/api/games/${id}`);
    if (!res.ok) throw new Error("Jeu introuvable");
    return res.json();
}

export async function fetchHistory(id, source) {
    const res = await fetch(
        `${BASE}/api/games/${id}/history?source=${encodeURIComponent(source)}`,
    );
    if (!res.ok) throw new Error("Historique indisponible");
    return res.json();
}
