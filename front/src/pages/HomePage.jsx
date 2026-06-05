import { useState, useEffect } from "react";
import { fetchGames } from "@/lib/api";
import GameCard from "@/components/GameCard";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Zap, Gamepad2 } from "lucide-react";

export default function HomePage() {
    const [query, setQuery] = useState("");
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [debouncedQuery, setDebouncedQuery] = useState("");

    useEffect(() => {
        const t = setTimeout(() => setDebouncedQuery(query), 350);
        return () => clearTimeout(t);
    }, [query]);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        fetchGames({ q: debouncedQuery })
            .then((data) => {
                if (!cancelled) {
                    setGames(data);
                    setLoading(false);
                }
            })
            .catch((err) => {
                if (!cancelled) {
                    setError(err.message);
                    setLoading(false);
                }
            });
        return () => {
            cancelled = true;
        };
    }, [debouncedQuery]);

    return (
        <div className="min-h-screen bg-bg">
            {/* Header */}
            <header className="sticky top-0 z-40 bg-bg/90 backdrop-blur-xl border-b border-border">
                <div className="max-w-7xl mx-auto px-6 h-14 flex items-center gap-6">
                    <div className="flex items-center gap-2 mr-auto">
                        <Zap
                            className="w-4 h-4 text-accent"
                            aria-hidden="true"
                        />
                        <span className="font-display font-semibold text-sm tracking-tight text-tx">
                            GAMESCOUT
                        </span>
                    </div>

                    <div className="relative w-64">
                        <Search
                            className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-tx-muted pointer-events-none"
                            aria-hidden="true"
                        />
                        <Input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Rechercher un jeu…"
                            className="pl-8 h-8 text-sm rounded-lg bg-raised border-border text-tx placeholder:text-tx-muted focus-visible:border-accent focus-visible:ring-accent/20"
                        />
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-12">
                {/* Hero */}
                <div className="mb-12">
                    <div className="inline-flex items-center gap-2 text-xs font-medium font-display tracking-[0.08em] px-3 py-1 rounded-full mb-5 bg-accent-dim text-accent border border-accent/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                        PRIX EN TEMPS RÉEL
                    </div>

                    <h1 className="font-display tracking-tight leading-none text-[clamp(2.5rem,6vw,4.5rem)] text-tx mb-4">
                        Trouve le meilleur prix
                        <br />
                        <span className="text-accent">
                            avant tout le monde.
                        </span>
                    </h1>

                    <p className="text-sm text-tx-muted">
                        {!loading && `${games.length} jeux indexés`}
                        {debouncedQuery &&
                            ` · résultats pour "${debouncedQuery}"`}
                    </p>
                </div>

                {/* Error */}
                {error && (
                    <div className="rounded-xl p-4 text-sm mb-8 bg-danger/5 border border-danger/20 text-danger">
                        {error}
                    </div>
                )}

                {/* Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                    {loading
                        ? Array.from({ length: 18 }).map((_, i) => (
                              <div
                                  key={i}
                                  className="rounded-xl overflow-hidden bg-card border border-border"
                              >
                                  <Skeleton className="aspect-[3/4] w-full bg-raised" />
                                  <div className="p-3 space-y-2">
                                      <Skeleton className="h-3 w-4/5 rounded bg-raised" />
                                      <Skeleton className="h-3 w-1/2 rounded bg-raised" />
                                  </div>
                              </div>
                          ))
                        : games.map((game) => (
                              <GameCard key={game.id} game={game} />
                          ))}
                </div>

                {!loading && !error && games.length === 0 && (
                    <div className="text-center py-32 text-tx-muted">
                        <Gamepad2
                            className="w-10 h-10 mx-auto mb-4 opacity-20"
                            aria-hidden="true"
                        />
                        <p className="font-medium text-sm">Aucun jeu trouvé</p>
                        <p className="text-xs mt-1 text-tx-dim">
                            Essayez un autre titre
                        </p>
                    </div>
                )}
            </main>
        </div>
    );
}
