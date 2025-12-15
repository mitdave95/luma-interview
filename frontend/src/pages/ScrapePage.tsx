import { useState, useCallback } from 'react';
import { Globe, FileText, Loader2, AlertCircle, Copy, Check } from 'lucide-react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import { scrapeWithPlaywright, ScrapeResponse } from '../api/client';

export default function ScrapePage() {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScrapeResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const handleScrape = useCallback(async () => {
    if (!url) {
      setError('Please enter a URL');
      return;
    }

    // Validate URL
    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await scrapeWithPlaywright(url);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [url]);

  const copyToClipboard = useCallback(() => {
    if (result?.markdown) {
      navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center gap-4 mb-6">
        <h2 className="text-xl font-bold text-white">URL Scraper</h2>
        <span className="text-sm text-gray-400">Convert web pages to markdown using Claude</span>
      </div>

      <div className="space-y-6">
        {/* Input Section */}
        <Card>
          <div className="space-y-4">
            {/* URL Input */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                URL to Scrape
              </label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isLoading}
                  />
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-500">
              Uses Playwright headless browser on the server to render JavaScript and fetch the full page content.
            </p>

            {/* Scrape Button */}
            <Button
              onClick={handleScrape}
              disabled={isLoading || !url}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Scraping & Converting...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Scrape & Convert to Markdown
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* Error Display */}
        {error && (
          <Card className="border-red-500 border-2">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-400">Error</h3>
                <p className="text-sm text-gray-300 mt-1">{error}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Result Display */}
        {result && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-white">Converted Markdown</h3>
                <Badge size="sm" className="bg-blue-600">
                  {result.source}
                </Badge>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={copyToClipboard}
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </>
                )}
              </Button>
            </div>

            {result.url && (
              <p className="text-xs text-gray-500 mb-4">
                Source: <a href={result.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{result.url}</a>
              </p>
            )}

            <div className="bg-gray-900 rounded-md p-4 max-h-[600px] overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                {result.markdown}
              </pre>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
