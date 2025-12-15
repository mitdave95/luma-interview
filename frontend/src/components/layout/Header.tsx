import { cn } from '../../utils/cn';

type ActivePage = 'dashboard' | 'scraper';

interface HeaderProps {
  activePage: ActivePage;
  onPageChange: (page: ActivePage) => void;
}

export default function Header({ activePage, onPageChange }: HeaderProps) {
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <h1 className="text-xl font-bold text-white">Luma API Dashboard</h1>

          <nav className="flex gap-1">
            <button
              onClick={() => onPageChange('dashboard')}
              className={cn(
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                activePage === 'dashboard'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
              )}
            >
              Server Dashboard
            </button>
            <button
              onClick={() => onPageChange('scraper')}
              className={cn(
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                activePage === 'scraper'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
              )}
            >
              URL Scraper
            </button>
          </nav>
        </div>

        <div className="text-xs text-gray-500">
          Real-time visualization & AI tools
        </div>
      </div>
    </header>
  );
}
