import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ServiceProvider } from './contexts/ServiceContext';
import { TimeRangeProvider } from './contexts/TimeRangeContext';
import { DashboardView } from './pages/DashboardView';
import { DependencyMapView } from './pages/DependencyMapView';
import { ServicesListView } from './pages/ServicesListView';
import { TracesView } from './pages/TracesView';

function App() {
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);

  return (
    <BrowserRouter>
      <TimeRangeProvider>
        <ServiceProvider>
          <Layout selectedTrace={selectedTrace} setSelectedTrace={setSelectedTrace}>
            <Routes>
              <Route path="/" element={<DashboardView />} />
              <Route path="/map" element={<DependencyMapView />} />
              <Route path="/services" element={<ServicesListView />} />
              <Route path="/traces" element={<TracesView onTraceClick={(traceId) => setSelectedTrace(traceId)} />} />
            </Routes>
          </Layout>
        </ServiceProvider>
      </TimeRangeProvider>
    </BrowserRouter>
  );
}

export default App;
