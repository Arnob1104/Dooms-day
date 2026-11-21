import { useState } from "react";
import BookingView from "./views/BookingView";
import MoviesView from "./views/MoviesView";
import RewatchView from "./views/RewatchView";

const TABS = [
  { id: "movies", label: "Movies" },
  { id: "rewatch", label: "Rewatch Plan" },
  { id: "booking", label: "Booking" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("movies");

  return (
    <div className="app">
      <header className="header">
        <h1>
          Doomsday <span>Ready</span>
        </h1>
        <p>Catch up on the MCU and book your opening-night watch party.</p>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "movies" && <MoviesView />}
        {tab === "rewatch" && <RewatchView />}
        {tab === "booking" && <BookingView />}
      </main>
    </div>
  );
}
