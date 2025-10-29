import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ServiceProvider } from './contexts/ServiceContext';
import { TimeRangeProvider } from './contexts/TimeRangeContext';
import { DashboardView } from './pages/DashboardView';
import { DependencyMapView } from './pages/DependencyMapView';
import { ServicesListView } from './pages/ServicesListView';

function App() {
  return (
    <BrowserRouter>
      <TimeRangeProvider>
        <ServiceProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<DashboardView />} />
              <Route path="/map" element={<DependencyMapView />} />
              <Route path="/services" element={<ServicesListView />} />
            </Routes>
          </Layout>
        </ServiceProvider>
      </TimeRangeProvider>
    </BrowserRouter>
  );
}

export default App;
