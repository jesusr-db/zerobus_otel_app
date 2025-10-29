import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { TimeRangeSelector } from './TimeRangeSelector';
import { ServiceDetailPanel } from './ServiceDetailPanel';
import { useServiceContext } from '../contexts/ServiceContext';
import { useTimeRange } from '../contexts/TimeRangeContext';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { selectedService, setSelectedService } = useServiceContext();
  const { timeRange, setTimeRange } = useTimeRange();

  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/map', label: 'Dependency Map' },
    { path: '/services', label: 'Services' },
  ];

  return (
    <div className="min-h-screen bg-background dark">
      <div className="flex h-screen">
        <aside className="w-64 border-r border-border bg-card">
          <div className="flex h-16 items-center border-b border-border px-6">
            <h1 className="text-xl font-bold text-foreground">Observability</h1>
          </div>
          
          <nav className="space-y-1 p-4">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`block rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
            <div className="text-sm text-muted-foreground">
              Real-time service monitoring
            </div>
            <div className="flex items-center gap-4">
              <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
              <div className="text-xs text-muted-foreground">
                Auto-refresh: 30s
              </div>
            </div>
          </header>

          <main className="flex-1 overflow-auto p-6">
            {children}
          </main>
        </div>

        {selectedService && (
          <ServiceDetailPanel
            serviceName={selectedService}
            timeRange={timeRange}
            onClose={() => setSelectedService(null)}
          />
        )}
      </div>
    </div>
  );
}
