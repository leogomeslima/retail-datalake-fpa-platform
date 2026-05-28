import { DashboardPage } from "./pages/DashboardPage";
import { EvolutionPage } from "./pages/EvolutionPage";
import { ForecastPage } from "./pages/ForecastPage";
import { MlForecastPage } from "./pages/MlForecastPage";
import { PdvPage } from "./pages/PdvPage";

function App() {
  if (window.location.pathname.startsWith("/pdv")) return <PdvPage />;
  if (window.location.pathname.startsWith("/evolucao")) return <EvolutionPage />;
  if (window.location.pathname.startsWith("/previsao-ml")) return <MlForecastPage />;
  if (window.location.pathname.startsWith("/forecast")) return <ForecastPage />;
  return <DashboardPage />;
}

export default App;
