import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchGame } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, ExternalLink, ShoppingCart } from "lucide-react";

const SOURCE_LABELS = {
    "instant-gaming": "Instant Gaming",
    g2a: "G2A",
    micromania: "Micromania",
};

function PriceRow({ p, isBest }) {
    return (
        <a
            href={p.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className={[
                "group flex items-center justify-between p-4 rounded-xl border transition-all duration-200",
                isBest
                    ? "bg-accent-glow border-accent/20 hover:border-accent/35"
                    : "bg-card border-border hover:border-border-md",
            ].join(" ")}
        >
            <div className="flex items-center gap-3">
                <div
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${isBest ? "bg-accent" : "bg-tx-dim"}`}
                />
                <div>
                    <p
                        className={`text-sm font-medium ${isBest ? "text-tx" : "text-tx-muted"}`}
                    >
                        {SOURCE_LABELS[p.source] ?? p.source}
                    </p>
                    {p.original_price && p.original_price > p.price && (
                        <p className="text-xs line-through text-tx-dim">
                            {Number(p.original_price).toFixed(2)} €
                        </p>
                    )}
                </div>
                {p.discount_pct > 0 && (
                    <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-deal-dim text-deal border border-deal/15">
                        -{p.discount_pct}%
                    </span>
                )}
            </div>

            <div className="flex items-center gap-3">
                <span
                    className={`font-semibold text-base font-display ${isBest ? "text-accent" : "text-tx"}`}
                >
                    {Number(p.price).toFixed(2)} €
                </span>
                {p.url && (
                    <ExternalLink
                        className="w-3.5 h-3.5 text-tx-muted opacity-0 group-hover:opacity-100 transition-opacity"
                        aria-hidden="true"
                    />
                )}
            </div>
        </a>
    );
}

function LoadingState() {
    return (
        <div className="min-h-screen bg-bg">
            <div className="max-w-3xl mx-auto px-6 py-10">
                <Skeleton className="h-4 w-16 rounded mb-10 bg-raised" />
                <div className="flex gap-8">
                    <Skeleton className="w-44 aspect-[3/4] rounded-xl shrink-0 bg-raised" />
                    <div className="flex-1 space-y-4 pt-2">
                        <Skeleton className="h-7 w-3/4 rounded bg-raised" />
                        <Skeleton className="h-5 w-1/4 rounded bg-raised" />
                        <div className="space-y-2.5 pt-4">
                            {[1, 2, 3].map((i) => (
                                <Skeleton
                                    key={i}
                                    className="h-16 w-full rounded-xl bg-raised"
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function GameDetailPage() {
    const { id } = useParams();
    const [game, setGame] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        fetchGame(id)
            .then((data) => {
                setGame(data);
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, [id]);

    if (loading) return <LoadingState />;

    const backLink = (
        <Link
            to="/"
            className="inline-flex items-center gap-2 text-xs font-medium font-display tracking-[0.06em] mb-10 text-tx-muted hover:text-tx transition-colors group"
        >
            <ArrowLeft
                className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform"
                aria-hidden="true"
            />
            RETOUR
        </Link>
    );

    if (error)
        return (
            <div className="min-h-screen bg-bg">
                <div className="max-w-3xl mx-auto px-6 py-10">
                    {backLink}
                    <div className="rounded-xl p-4 text-sm bg-danger/5 border border-danger/20 text-danger">
                        {error}
                    </div>
                </div>
            </div>
        );

    const bestPrice = game.prices?.[0]?.price;
    const bestDiscount = Math.max(
        ...(game.prices?.map((p) => p.discount_pct ?? 0) ?? [0]),
    );

    return (
        <div className="min-h-screen bg-bg">
            {/* Atmosphere glow */}
            {game.image_url && (
                <div
                    className="fixed inset-0 pointer-events-none opacity-[0.04] blur-[60px]"
                    style={{
                        backgroundImage: `url(${game.image_url})`,
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                    }}
                />
            )}

            <div className="relative max-w-3xl mx-auto px-6 py-10">
                {backLink}

                {/* Hero */}
                <div className="flex flex-col sm:flex-row gap-8 mb-12">
                    {/* Cover */}
                    <div className="shrink-0 w-40 sm:w-48">
                        <div className="relative rounded-xl overflow-hidden aspect-3/4 shadow-2xl bg-raised border border-border">
                            {game.image_url ? (
                                <img
                                    src={game.image_url}
                                    alt={game.title}
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-4xl text-tx-dim">
                                    ◻
                                </div>
                            )}
                            {bestDiscount > 0 && (
                                <div className="absolute top-2.5 left-2.5">
                                    <span className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded bg-deal-dim text-deal border border-deal/20">
                                        -{bestDiscount}%
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Meta */}
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                        <h1 className="font-display tracking-tight leading-tight text-[clamp(2rem,5vw,3.5rem)] text-tx mb-3">
                            {game.title}
                        </h1>

                        <div className="flex items-baseline gap-3 mb-6">
                            {}
                            <span
                                className="font-display font-bold text-accent leading-none"
                                style={{
                                    fontSize: "2.8rem",
                                    letterSpacing: "-0.04em",
                                }}
                            >
                                {bestPrice != null
                                    ? `${Number(bestPrice).toFixed(2)} €`
                                    : "—"}
                            </span>
                            {bestDiscount > 0 && (
                                <span className="text-sm font-medium px-2 py-0.5 rounded-lg bg-deal-dim text-deal border border-deal/15">
                                    -{bestDiscount}%
                                </span>
                            )}
                        </div>

                        <div className="inline-flex items-center gap-2 self-start text-xs font-display tracking-[0.04em] px-3 py-2 rounded-lg bg-raised border border-border text-tx-muted">
                            <ShoppingCart
                                className="w-3.5 h-3.5"
                                aria-hidden="true"
                            />
                            {game.prices?.length ?? 0} BOUTIQUE
                            {game.prices?.length !== 1 ? "S" : ""}
                        </div>
                    </div>
                </div>

                <div className="border-t border-border mb-8" />

                {/* Prices */}
                <section>
                    <p className="text-[10px] font-semibold font-display uppercase tracking-[0.12em] text-tx-dim mb-4">
                        Comparatif boutiques
                    </p>
                    <div className="space-y-2">
                        {game.prices?.length ? (
                            game.prices.map((p, i) => (
                                <PriceRow key={p.id} p={p} isBest={i === 0} />
                            ))
                        ) : (
                            <p className="text-sm text-tx-muted">
                                Aucun prix disponible
                            </p>
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
}
