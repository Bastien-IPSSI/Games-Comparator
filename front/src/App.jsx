import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import GameDetailPage from "@/pages/GameDetailPage";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/games/:id" element={<GameDetailPage />} />
            </Routes>
        </BrowserRouter>
    );
}
