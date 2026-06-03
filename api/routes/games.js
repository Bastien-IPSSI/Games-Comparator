import { Router } from "express";
import pool from "../db.js";

const router = Router();

// GET /api/games?q=elden&platform=PC
router.get("/", async (req, res) => {
  try {
    const { q = "", platform } = req.query;
    const search = `%${q.toLowerCase().replace(/\s+/g, " ").trim()}%`;

    let sql = `
      SELECT
        g.id,
        g.title,
        g.platform,
        g.image_url,
        MIN(p.price)  AS best_price,
        p.source      AS best_source,
        p.url         AS best_url
      FROM games g
      JOIN prices p ON p.game_id = g.id
      JOIN (
        SELECT game_id, source, MAX(scraped_at) AS max_scraped_at
        FROM prices
        GROUP BY game_id, source
      ) latest ON latest.game_id = p.game_id
             AND latest.source = p.source
             AND latest.max_scraped_at = p.scraped_at
      WHERE g.normalized_title LIKE ?
    `;
    const params = [search];

    if (platform) {
      sql += " AND g.platform = ?";
      params.push(platform);
    }

    sql += " GROUP BY g.id ORDER BY best_price ASC";

    const [rows] = await pool.query(sql, params);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/games/:id
router.get("/:id", async (req, res) => {
  try {
    const [games] = await pool.query("SELECT * FROM games WHERE id = ?", [req.params.id]);
    if (!games.length) return res.status(404).json({ error: "Game not found" });

    const [prices] = await pool.query(
      `SELECT p.*
       FROM prices p
       JOIN (
         SELECT source, MAX(scraped_at) AS max_scraped_at
         FROM prices
         WHERE game_id = ?
         GROUP BY source
       ) latest ON latest.source = p.source
              AND latest.max_scraped_at = p.scraped_at
       WHERE p.game_id = ?
       ORDER BY p.price ASC`,
      [req.params.id, req.params.id]
    );

    res.json({ ...games[0], prices });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/games/:id/history?source=instant-gaming
router.get("/:id/history", async (req, res) => {
  try {
    const { source } = req.query;
    if (!source) return res.status(400).json({ error: "source is required" });

    const [rows] = await pool.query(
      `SELECT price, original_price, discount_pct, scraped_at
       FROM prices
       WHERE game_id = ? AND source = ?
       ORDER BY scraped_at ASC`,
      [req.params.id, source]
    );

    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
