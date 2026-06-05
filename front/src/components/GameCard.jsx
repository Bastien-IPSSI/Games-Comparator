import { Link } from "react-router-dom";

export default function GameCard({ game }) {
    const { id, title, image_url, best_price, best_source, discount_pct } =
        game;

    return (
        <Link
            to={`/games/${id}`}
            className="group block rounded-xl overflow-hidden border border-border bg-card transition-all duration-500 ease-out hover:-translate-y-1.5 hover:shadow-xl hover:shadow-black/10 hover:border-border-md"
        >
            {/* Image Wrapper */}
            <div className="relative aspect-3/4 overflow-hidden bg-raised">
                {image_url ? (
                    <img
                        src={image_url}
                        alt={title}
                        loading="lazy"
                        className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-110"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-4xl select-none text-tx-dim">
                        ◻
                    </div>
                )}

                {/* Gradient overlay on hover - plus doux */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-out bg-gradient-to-t from-bg/90 via-bg/20 to-transparent" />

                {/* Discount badge */}
                {discount_pct > 0 && (
                    <div className="absolute top-2.5 left-2.5 z-10">
                        <span className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded-md bg-deal-dim text-deal border border-deal/20 font-display tracking-wide shadow-sm transition-transform duration-500 ease-out group-hover:scale-105">
                            -{discount_pct}%
                        </span>
                    </div>
                )}
            </div>

            {/* Info Section */}
            <div className="relative p-3 z-10 transition-transform duration-500 ease-out">
                <p className="text-sm leading-snug line-clamp-2 mb-2.5 text-tx font-display transition-colors duration-300 group-hover:text-accent">
                    {title}
                </p>
                <div className="flex items-center justify-between gap-2">
                    <span className="text-base font-semibold text-accent font-display">
                        {best_price != null
                            ? `${Number(best_price).toFixed(2)} €`
                            : "—"}
                    </span>
                    {best_source && (
                        <span className="text-[10px] uppercase tracking-widest truncate text-tx-muted transition-colors duration-300 group-hover:text-tx">
                            {best_source}
                        </span>
                    )}
                </div>
            </div>
        </Link>
    );
}