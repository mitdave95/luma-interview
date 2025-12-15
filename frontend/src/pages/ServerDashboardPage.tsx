import { useState, useCallback } from 'react';
import { Wifi, WifiOff, RefreshCw, Clock, Layers, Activity, Play, Settings } from 'lucide-react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import { useWebSocket } from '../context/WebSocketContext';
import { cn } from '../utils/cn';
import { TIER_CONFIGS } from '../utils/constants';
import { UserTier, QueueInfo, ActiveJob } from '../types/api';
import { makeRequest } from '../api/client';

// Simulation types
interface SimulationConfig {
  free: number;
  developer: number;
  pro: number;
  enterprise: number;
}

interface SimulatedRequest {
  id: string;
  tier: UserTier;
  status: 'pending' | 'sending' | 'success' | 'rate_limited' | 'error';
  httpStatus?: number;
  jobId?: string;
  error?: string;
  sentAt?: Date;
  completedAt?: Date;
  priority?: string;
}

const tierColors: Record<string, string> = {
  free: 'text-gray-400 bg-gray-600',
  developer: 'text-blue-400 bg-blue-600',
  pro: 'text-purple-400 bg-purple-600',
  enterprise: 'text-amber-400 bg-amber-600',
};

const priorityColors: Record<string, { text: string; bg: string; border: string }> = {
  critical: { text: 'text-amber-400', bg: 'bg-amber-600', border: 'border-amber-500' },
  high: { text: 'text-purple-400', bg: 'bg-purple-600', border: 'border-purple-500' },
  normal: { text: 'text-blue-400', bg: 'bg-blue-600', border: 'border-blue-500' },
};

const statusColors: Record<SimulatedRequest['status'], string> = {
  pending: 'bg-gray-600 text-gray-300',
  sending: 'bg-blue-600 text-blue-100',
  success: 'bg-green-600 text-green-100',
  rate_limited: 'bg-yellow-600 text-yellow-100',
  error: 'bg-red-600 text-red-100',
};

// Priority mapping based on tier
const tierPriority: Record<UserTier, string> = {
  enterprise: 'critical',
  pro: 'high',
  developer: 'normal',
  free: 'normal',
};

function SimulationPanel({
  onRunSimulation,
  isRunning
}: {
  onRunSimulation: (config: SimulationConfig) => void;
  isRunning: boolean;
}) {
  const [config, setConfig] = useState<SimulationConfig>({
    free: 5,
    developer: 3,
    pro: 2,
    enterprise: 1,
  });

  const handleChange = (tier: UserTier, value: string) => {
    const num = Math.max(0, Math.min(50, parseInt(value) || 0));
    setConfig(prev => ({ ...prev, [tier]: num }));
  };

  const totalRequests = config.free + config.developer + config.pro + config.enterprise;

  return (
    <Card className="border-2 border-gray-600">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5 text-gray-400" />
        <h3 className="text-lg font-semibold text-white">Simulation Config</h3>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-4">
        {(Object.keys(TIER_CONFIGS) as UserTier[]).map((tier) => (
          <div key={tier} className="space-y-2">
            <label className="block text-sm font-medium text-gray-300 capitalize">
              {tier}
              <span className="text-xs text-gray-500 ml-1">
                ({TIER_CONFIGS[tier].rateLimit}/min)
              </span>
            </label>
            <input
              type="number"
              min="0"
              max="50"
              value={config[tier]}
              onChange={(e) => handleChange(tier, e.target.value)}
              className={cn(
                'w-full px-3 py-2 rounded-md border-2 bg-gray-900 text-white text-center',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800',
                tierColors[tier].split(' ')[1].replace('bg-', 'border-')
              )}
              disabled={isRunning}
            />
            <div className="text-xs text-gray-500 text-center">
              Priority: {tierPriority[tier]}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Total: <span className="font-bold text-white">{totalRequests}</span> requests
        </div>
        <Button
          onClick={() => onRunSimulation(config)}
          disabled={isRunning || totalRequests === 0}
          className="flex items-center gap-2"
        >
          {isRunning ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Simulation
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}

function SimulatedRequestsList({ requests }: { requests: SimulatedRequest[] }) {
  const statusCounts = requests.reduce((acc, req) => {
    acc[req.status] = (acc[req.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Group by tier for better visualization
  const byTier = requests.reduce((acc, req) => {
    if (!acc[req.tier]) acc[req.tier] = [];
    acc[req.tier].push(req);
    return acc;
  }, {} as Record<UserTier, SimulatedRequest[]>);

  // Sort by priority order (enterprise first, then pro, dev, free)
  const tierOrder: UserTier[] = ['enterprise', 'pro', 'developer', 'free'];

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Simulated Requests</h3>
        <div className="flex gap-2">
          {Object.entries(statusCounts).map(([status, count]) => (
            <Badge
              key={status}
              size="sm"
              className={statusColors[status as SimulatedRequest['status']]}
            >
              {status}: {count}
            </Badge>
          ))}
        </div>
      </div>

      {requests.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <Play className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>Run a simulation to see requests</p>
        </div>
      ) : (
        <div className="space-y-4 max-h-64 overflow-y-auto">
          {tierOrder.map((tier) => {
            const tierRequests = byTier[tier];
            if (!tierRequests || tierRequests.length === 0) return null;

            return (
              <div key={tier}>
                <div className="flex items-center gap-2 mb-2">
                  <div className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold',
                    tierColors[tier].split(' ')[1]
                  )}>
                    {tier.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-gray-300 capitalize">{tier}</span>
                  <span className="text-xs text-gray-500">
                    ({tierRequests.length} requests, {tierPriority[tier]} priority)
                  </span>
                </div>
                <div className="flex flex-wrap gap-1 ml-8">
                  {tierRequests.map((req) => (
                    <div
                      key={req.id}
                      className={cn(
                        'px-2 py-1 rounded text-xs font-mono',
                        statusColors[req.status]
                      )}
                      title={req.error || req.jobId || req.status}
                    >
                      {req.httpStatus || '...'}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function QueueCard({ name, queue }: { name: string; queue: QueueInfo }) {
  const colors = priorityColors[name] || priorityColors.normal;

  return (
    <Card className={cn('border-2', colors.border)}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className={cn('text-lg font-bold capitalize', colors.text)}>{name}</h3>
          <p className="text-xs text-gray-500">Weight: {queue.weight}x</p>
        </div>
        <div className={cn('w-12 h-12 rounded-full flex items-center justify-center text-white font-bold', colors.bg)}>
          {queue.length}
        </div>
      </div>

      {queue.jobs.length > 0 ? (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {queue.jobs.map((job, idx) => (
            <div
              key={job.job_id}
              className="bg-gray-900 rounded px-3 py-2 text-sm flex items-center justify-between"
            >
              <div>
                <span className="text-gray-400">#{idx + 1}</span>
                <span className="ml-2 text-gray-300 font-mono text-xs">{job.job_id.slice(0, 8)}</span>
                {job.user_id && (
                  <span className="ml-2 text-xs text-gray-500">({job.user_id})</span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {job.enqueued_at
                  ? new Date(job.enqueued_at * 1000).toLocaleTimeString()
                  : '-'}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-gray-500 text-sm py-4">Queue empty</div>
      )}
    </Card>
  );
}

const jobStatusColors: Record<string, string> = {
  queued: 'bg-blue-600 text-blue-100',
  processing: 'bg-green-600 text-green-100',
};

function ActiveJobCard({ job }: { job: ActiveJob }) {
  const colors = priorityColors[job.priority] || priorityColors.normal;
  const statusColor = jobStatusColors[job.status] || 'bg-gray-600 text-gray-100';

  return (
    <div className={cn('bg-gray-900 rounded-lg p-3 border-l-4', colors.border)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge size="sm" className={cn(colors.bg, 'text-white')}>
            {job.priority}
          </Badge>
          <Badge size="sm" className={statusColor}>
            {job.status}
          </Badge>
        </div>
        <span className="text-xs font-mono text-gray-400">{job.job_id.slice(0, 8)}</span>
      </div>

      <div className="text-xs text-gray-400 truncate mb-2">{job.prompt}</div>

      {job.status === 'processing' && job.progress !== null && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Progress</span>
            <span className="text-gray-300">{(job.progress * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-green-500 h-1.5 rounded-full transition-all"
              style={{ width: `${job.progress * 100}%` }}
            />
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 mt-2">
        <span>User: {job.user_id}</span>
        {job.created_at && (
          <span className="ml-2">
            Created: {new Date(job.created_at).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  );
}

export default function ServerDashboardPage() {
  const { status, data, lastUpdate, reconnect } = useWebSocket();
  const [isRunning, setIsRunning] = useState(false);
  const [simulatedRequests, setSimulatedRequests] = useState<SimulatedRequest[]>([]);

  const runSimulation = useCallback(async (config: SimulationConfig) => {
    setIsRunning(true);
    setSimulatedRequests([]);

    // Create request objects for all tiers
    const requests: SimulatedRequest[] = [];
    let requestId = 0;

    // Generate requests in priority order (enterprise first for better visualization)
    const tierOrder: UserTier[] = ['enterprise', 'pro', 'developer', 'free'];

    for (const tier of tierOrder) {
      const count = config[tier];
      for (let i = 0; i < count; i++) {
        requests.push({
          id: `req-${requestId++}`,
          tier,
          status: 'pending',
          priority: tierPriority[tier],
        });
      }
    }

    setSimulatedRequests([...requests]);

    // Fire all requests in parallel
    const promises = requests.map(async (req, index) => {
      // Mark as sending
      setSimulatedRequests(prev =>
        prev.map(r => r.id === req.id ? { ...r, status: 'sending' as const, sentAt: new Date() } : r)
      );

      try {
        const apiKey = TIER_CONFIGS[req.tier].apiKey;
        const response = await makeRequest<{ job_id?: string; error?: { message: string } }>(
          'POST',
          '/generate',
          apiKey,
          {
            prompt: `Simulation request ${index + 1} from ${req.tier} tier - A beautiful sunset over mountains`,
            duration: 5,
          }
        );

        const newStatus: SimulatedRequest['status'] =
          response.status === 429 ? 'rate_limited' :
          response.status >= 200 && response.status < 300 ? 'success' :
          response.status === 403 ? 'error' : // Free tier can't generate
          'error';

        setSimulatedRequests(prev =>
          prev.map(r => r.id === req.id ? {
            ...r,
            status: newStatus,
            httpStatus: response.status,
            jobId: response.data?.job_id,
            error: response.data?.error?.message,
            completedAt: new Date(),
          } : r)
        );
      } catch (err) {
        setSimulatedRequests(prev =>
          prev.map(r => r.id === req.id ? {
            ...r,
            status: 'error',
            error: String(err),
            completedAt: new Date(),
          } : r)
        );
      }
    });

    await Promise.allSettled(promises);
    setIsRunning(false);
  }, []);

  return (
    <div className="p-6 h-full overflow-y-auto">
      {/* Connection Status */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold text-white">Server Dashboard</h2>
          <div className="flex items-center gap-2">
            {status === 'connected' ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400">Connected</span>
              </>
            ) : status === 'connecting' ? (
              <>
                <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
                <span className="text-sm text-yellow-400">Connecting...</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400">Disconnected</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {lastUpdate && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Last update: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          {status !== 'connected' && (
            <Button variant="secondary" size="sm" onClick={reconnect}>
              <RefreshCw className="w-4 h-4 mr-1" />
              Reconnect
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {/* Simulation Panel */}
        <SimulationPanel onRunSimulation={runSimulation} isRunning={isRunning} />

        {/* Simulated Requests Status */}
        {simulatedRequests.length > 0 && (
          <SimulatedRequestsList requests={simulatedRequests} />
        )}

        {data ? (
          <>
            {/* Queue Overview */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Layers className="w-5 h-5 text-gray-400" />
                <h3 className="text-lg font-semibold text-white">Priority Queues</h3>
                <Badge variant="default">{data.total_queued} total</Badge>
                <span className="text-xs text-gray-500 ml-2">
                  (Critical: 10x weight, High: 5x weight, Normal: 1x weight)
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <QueueCard name="critical" queue={data.queues.critical} />
                <QueueCard name="high" queue={data.queues.high} />
                <QueueCard name="normal" queue={data.queues.normal} />
              </div>
            </section>

            {/* Concurrent Jobs */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-gray-400" />
                <h3 className="text-lg font-semibold text-white">Concurrent Jobs</h3>
                <Badge variant="info">{data.active_jobs.length} total</Badge>
                <span className="text-xs text-gray-500">
                  ({data.active_jobs.filter(j => j.status === 'processing').length} processing,
                  {' '}{data.active_jobs.filter(j => j.status === 'queued').length} queued)
                </span>
              </div>

              {data.active_jobs.length > 0 ? (
                <div className="grid grid-cols-3 gap-4">
                  {data.active_jobs.map((job) => (
                    <ActiveJobCard key={job.job_id} job={job} />
                  ))}
                </div>
              ) : (
                <Card className="text-center text-gray-500 py-8">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No concurrent jobs</p>
                </Card>
              )}
            </section>
          </>
        ) : (
          <Card className="flex items-center justify-center h-64">
            <div className="text-center text-gray-500">
              {status === 'connecting' ? (
                <>
                  <RefreshCw className="w-12 h-12 mx-auto mb-3 animate-spin opacity-50" />
                  <p>Connecting to server...</p>
                </>
              ) : (
                <>
                  <WifiOff className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Unable to connect to dashboard</p>
                  <Button variant="secondary" size="sm" onClick={reconnect} className="mt-4">
                    Try Again
                  </Button>
                </>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
