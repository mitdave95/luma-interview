import { WebSocketProvider } from './context/WebSocketContext';
import Header from './components/layout/Header';
import ServerDashboardPage from './pages/ServerDashboardPage';

function App() {
  return (
    <WebSocketProvider>
      <div className="h-screen flex flex-col">
        <Header />
        <main className="flex-1 overflow-hidden">
          <ServerDashboardPage />
        </main>
      </div>
    </WebSocketProvider>
  );
}

export default App;
