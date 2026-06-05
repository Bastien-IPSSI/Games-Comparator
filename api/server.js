import dotenv from "dotenv";
import express from "express";
import cors from "cors";
import gamesRouter from "./routes/games.js";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: "http://localhost:5173" })); // Vite dev server
app.use(express.json());

app.use("/api/games", gamesRouter);

app.listen(PORT, () => {
  console.log(`API running on http://localhost:${PORT}`);
});
