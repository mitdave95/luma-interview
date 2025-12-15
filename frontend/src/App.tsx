import { useState } from 'react';
import { WebSocketProvider } from './context/WebSocketContext';
import Header from './components/layout/Header';
import ServerDashboardPage from './pages/ServerDashboardPage';
import ScrapePage from './pages/ScrapePage';

type ActivePage = 'dashboard' | 'scraper';

function App() {
  const [activePage, setActivePage] = useState<ActivePage>('dashboard');

  return (
    <WebSocketProvider>
      <div className="h-screen flex flex-col">
        <Header activePage={activePage} onPageChange={setActivePage} />
        <main className="flex-1 overflow-hidden">
          {activePage === 'dashboard' ? <ServerDashboardPage /> : <ScrapePage />}
        </main>
      </div>
    </WebSocketProvider>
  );
}

export default App;
