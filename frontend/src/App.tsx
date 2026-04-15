import { Sidebar } from './components/Sidebar';
import { ChatPage } from './pages/ChatPage';
import { WizardPage } from './pages/WizardPage';
import { DashboardPage } from './pages/DashboardPage';
import { OpsRoomPage } from './pages/OpsRoomPage';
import { SimulationPage } from './pages/SimulationPage';
import { useConfigStore } from './store/useConfigStore';

export default function App() {
  const view = useConfigStore((s) => s.view);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">
        {view === 'chat' && <ChatPage />}
        {view === 'wizard' && <WizardPage />}
        {view === 'dashboard' && <DashboardPage />}
        {view === 'opsroom' && <OpsRoomPage />}
        {view === 'simulation' && <SimulationPage />}
      </main>
    </div>
  );
}
