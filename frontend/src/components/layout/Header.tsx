export default function Header() {
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Luma API Server Dashboard</h1>
        <div className="text-xs text-gray-500">
          Real-time queue and rate limit visualization
        </div>
      </div>
    </header>
  );
}
