/**
 * SecurityAlerts — AWS SecurityHub findings viewer with remediation workflow.
 * Displays active and resolved security findings with severity indicators.
 * Supports search/filter, inline resolution, and automated remediation.
 * @module SecurityAlerts
 * @version 2.3.0
 */
import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAuthSession } from 'aws-amplify/auth';
import {
  Table, TableBody, TableCell, TableHead, TableRow, TextField,
  CircularProgress, Alert, Paper, Typography, Box, Chip,
  Button, Dialog, DialogTitle, DialogContent, DialogActions,
  RadioGroup, FormControlLabel, Radio, FormControl, FormLabel,
  Snackbar, IconButton, Tooltip, Collapse, Divider, LinearProgress,
  List, ListItem, ListItemIcon, ListItemText, Tab, Tabs,
} from '@mui/material';
import SecurityIcon         from '@mui/icons-material/Security';
import CheckCircleIcon      from '@mui/icons-material/CheckCircle';
import BlockIcon            from '@mui/icons-material/Block';
import NotificationsIcon    from '@mui/icons-material/Notifications';
import ExpandMoreIcon       from '@mui/icons-material/ExpandMore';
import ExpandLessIcon       from '@mui/icons-material/ExpandLess';
import AutoFixHighIcon      from '@mui/icons-material/AutoFixHigh';
import PlayArrowIcon        from '@mui/icons-material/PlayArrow';
import HourglassEmptyIcon   from '@mui/icons-material/HourglassEmpty';
import ErrorOutlineIcon     from '@mui/icons-material/ErrorOutline';
import MenuBookIcon         from '@mui/icons-material/MenuBook';
import TerminalIcon         from '@mui/icons-material/Terminal';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

// ── Types ────────────────────────────────────────────────────────────────────
interface SecurityAlert {
  id: string;
  type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  timestamp: string;
  createdAt: string;
  status: 'ACTIVE' | 'RESOLVED';
  workflowStatus: string;
  resolutionDate: string | null;
}

type ResolutionAction = 'RESOLVED' | 'SUPPRESSED' | 'NOTIFIED';

interface ResolvePayload {
  findingId: string;
  action: ResolutionAction;
  note: string;
}

interface RemediationStep {
  name:   string;
  status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED';
  error?: string;
}

interface RemediationPreview {
  dryRun:           boolean;
  findingId:        string;
  strategy:         string;
  label:            string;
  description:      string;
  canAutomate:      boolean;
  estimatedMinutes: number | null;
  steps:            RemediationStep[];
  resource:         { type: string; id: string; region: string } | null;
  playbook:         RemediationPlaybook | null;
}

interface RemediationPlaybook {
  summary:     string;
  steps:       string[];
  cveId:       string | null;
  cliCommands: string[];
  docsUrl:     string;
}

interface RemediationJob {
  jobId:         string;
  findingId:     string;
  strategy:      string;
  label?:        string;   // populated by backend; may be absent on older polled records
  status:        'RUNNING' | 'COMPLETED' | 'FAILED' | 'PLAYBOOK' | 'PARTIAL';
  externalJobId?: string;
  externalType?:  string;
  steps:          RemediationStep[];
  canAutomate?:   boolean;
  playbook?:      RemediationPlaybook;
  buildLogs?:     string;
  startedAt?:     string;
  completedAt?:   string;
  triggeredBy?:   string;
  message?:       string;
}

// ── Constants ────────────────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  CRITICAL: 'error',
  HIGH:     'warning',
  MEDIUM:   'info',
  LOW:      'default',
};

const STATUS_COLORS: Record<string, 'error' | 'success' | 'default'> = {
  ACTIVE:   'error',
  RESOLVED: 'success',
};

const ACTION_INFO: Record<ResolutionAction, { label: string; description: string; icon: React.ReactNode; color: string }> = {
  RESOLVED: {
    label:       'Resolve',
    description: 'Mark as remediated — the underlying issue has been fixed.',
    icon:        <CheckCircleIcon fontSize="small" />,
    color:       '#4caf50',
  },
  SUPPRESSED: {
    label:       'Suppress',
    description: 'False positive or accepted risk — hide from active view.',
    icon:        <BlockIcon fontSize="small" />,
    color:       '#ff9800',
  },
  NOTIFIED: {
    label:       'Acknowledge',
    description: 'Acknowledged and under investigation — keep visible.',
    icon:        <NotificationsIcon fontSize="small" />,
    color:       '#2196f3',
  },
};

const JOB_STATUS_COLOR: Record<string, string> = {
  RUNNING:   '#2196f3',
  COMPLETED: '#4caf50',
  FAILED:    '#f44336',
  PARTIAL:   '#ff9800',
  PLAYBOOK:  '#9c27b0',
};

const STEP_STATUS_ICON = {
  PENDING: <FiberManualRecordIcon fontSize="small" sx={{ color: 'text.disabled' }} />,
  RUNNING: <CircularProgress size={14} />,
  DONE:    <CheckCircleIcon    fontSize="small" sx={{ color: '#4caf50' }} />,
  FAILED:  <ErrorOutlineIcon   fontSize="small" sx={{ color: '#f44336' }} />,
};

const API_URL = import.meta.env.VITE_API_URL;

// ── API Functions ────────────────────────────────────────────────────────────
async function getAuthHeaders(): Promise<Record<string, string>> {
  const { tokens } = await fetchAuthSession();
  return { Authorization: `Bearer ${tokens?.idToken?.toString()}` };
}

const fetchAlerts = async (): Promise<SecurityAlert[]> => {
  const headers = await getAuthHeaders();
  const res = await fetch(API_URL + 'security-alerts', { headers });
  if (!res.ok) throw new Error('Failed to fetch alerts');
  const data = await res.json();
  return data.alerts || [];
};

const resolveAlert = async (payload: ResolvePayload): Promise<any> => {
  const headers = await getAuthHeaders();
  const res = await fetch(API_URL + 'security-alerts/resolve', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Failed to resolve alert');
  }
  return res.json();
};

const fetchRemediationPreview = async (findingId: string): Promise<RemediationPreview> => {
  const headers = await getAuthHeaders();
  const res = await fetch(API_URL + 'security-alerts/remediate', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ findingId, dryRun: true }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Failed to fetch remediation preview');
  }
  return res.json();
};

const startRemediation = async (findingId: string): Promise<RemediationJob> => {
  const headers = await getAuthHeaders();
  const res = await fetch(API_URL + 'security-alerts/remediate', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ findingId, dryRun: false }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Failed to start remediation');
  }
  return res.json();
};

const fetchRemediationStatus = async (jobId: string): Promise<RemediationJob> => {
  const headers = await getAuthHeaders();
  const res = await fetch(API_URL + `security-alerts/remediation-status?jobId=${jobId}`, { headers });
  if (!res.ok) throw new Error('Failed to fetch remediation status');
  return res.json();
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

// ── Sub-component: Remediation Job Tracker ───────────────────────────────────
interface JobTrackerProps {
  job: RemediationJob;
  onClose: () => void;
  onRefresh: () => void;
}

const JobTracker: React.FC<JobTrackerProps> = ({ job, onClose, onRefresh }) => {
  const [activeTab, setActiveTab] = useState(0);
  const statusColor = JOB_STATUS_COLOR[job.status] || '#666';
  const isRunning   = job.status === 'RUNNING';
  const isDone      = job.status === 'COMPLETED';
  const isFailed    = job.status === 'FAILED';

  return (
    <Box>
      {/* Status Banner */}
      <Box sx={{ p: 2, bgcolor: `${statusColor}10`, border: `1px solid ${statusColor}40`, borderRadius: 1, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          {isRunning ? <CircularProgress size={16} sx={{ color: statusColor }} /> :
           isDone    ? <CheckCircleIcon sx={{ color: statusColor, fontSize: 18 }} /> :
           isFailed  ? <ErrorOutlineIcon sx={{ color: statusColor, fontSize: 18 }} /> :
                       <AutoFixHighIcon sx={{ color: statusColor, fontSize: 18 }} />}
          <Typography variant="subtitle2" sx={{ color: statusColor, fontWeight: 700 }}>
            {job.status === 'RUNNING'   ? 'Remediation in Progress' :
             job.status === 'COMPLETED' ? 'Remediation Complete ✓' :
             job.status === 'FAILED'    ? 'Remediation Failed' :
             job.status === 'PARTIAL'   ? 'Partially Remediated' :
             'Playbook Generated'}
          </Typography>
        </Box>
        {isRunning && <LinearProgress sx={{ borderRadius: 1, mt: 1 }} />}
        <Typography variant="caption" color="text.secondary">
          Job ID: {job.jobId}
          {job.startedAt && ` · Started: ${formatDate(job.startedAt)}`}
          {job.completedAt && ` · Done: ${formatDate(job.completedAt)}`}
        </Typography>
      </Box>

      {/* Tabs: Steps | Playbook | Logs */}
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
        <Tab label="Steps" />
        {job.playbook && <Tab label="Playbook" />}
        {job.buildLogs && <Tab label="Logs" />}
      </Tabs>

      {/* Steps Tab */}
      {activeTab === 0 && (
        <List dense>
          {(job.steps || []).map((step, i) => (
            <ListItem key={i} sx={{ py: 0.25 }}>
              <ListItemIcon sx={{ minWidth: 28 }}>
                {STEP_STATUS_ICON[step.status] || STEP_STATUS_ICON.PENDING}
              </ListItemIcon>
              <ListItemText
                primary={step.name}
                secondary={step.error || null}
                primaryTypographyProps={{ variant: 'body2' }}
                secondaryTypographyProps={{ color: 'error', variant: 'caption' }}
              />
            </ListItem>
          ))}
          {(!job.steps || job.steps.length === 0) && (
            <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
              No step details available.
            </Typography>
          )}
        </List>
      )}

      {/* Playbook Tab — always at index 1 when present */}
      {activeTab === 1 && job.playbook && (
        <Box sx={{ px: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {job.playbook.summary}
          </Typography>
          <Typography variant="subtitle2" gutterBottom>Steps</Typography>
          <List dense>
            {job.playbook.steps.map((s, i) => (
              <ListItem key={i} sx={{ py: 0.25 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>{i + 1}.</Typography>
                </ListItemIcon>
                <ListItemText primary={s} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItem>
            ))}
          </List>
          {job.playbook.cliCommands.length > 0 && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <TerminalIcon fontSize="small" color="action" />
                <Typography variant="subtitle2">CLI Commands</Typography>
              </Box>
              <Box sx={{
                bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1,
                p: 1.5, fontFamily: 'monospace', fontSize: '0.78rem',
                whiteSpace: 'pre-wrap', overflowX: 'auto',
              }}>
                {job.playbook.cliCommands.join('\n')}
              </Box>
            </>
          )}
          <Box sx={{ mt: 1.5 }}>
            <Button size="small" href={job.playbook.docsUrl} target="_blank" startIcon={<MenuBookIcon />}>
              AWS Docs
            </Button>
          </Box>
        </Box>
      )}

      {/* Logs Tab — at index 1 when no playbook, or index 2 when playbook also present */}
      {job.buildLogs && activeTab === (job.playbook ? 2 : 1) && (
        <Box>
          <Button
            size="small"
            variant="outlined"
            href={job.buildLogs}
            target="_blank"
            startIcon={<TerminalIcon />}
          >
            Open CodeBuild Logs
          </Button>
        </Box>
      )}

      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 1, mt: 2, justifyContent: 'flex-end' }}>
        {isRunning && (
          <Button size="small" variant="outlined" onClick={onRefresh} startIcon={<CircularProgress size={14} />}>
            Refresh
          </Button>
        )}
        <Button size="small" onClick={onClose}>Close</Button>
      </Box>
    </Box>
  );
};

// ── Sub-component: Remediation Preview ───────────────────────────────────────
interface PreviewPanelProps {
  preview: RemediationPreview;
  onConfirm: () => void;
  onCancel:  () => void;
  loading:   boolean;
}

const PreviewPanel: React.FC<PreviewPanelProps> = ({ preview, onConfirm, onCancel, loading }) => {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box>
      {/* Strategy header */}
      <Box sx={{
        p: 2, mb: 2, borderRadius: 1,
        bgcolor: preview.canAutomate ? '#e8f5e9' : '#f3e5f5',
        border: `1px solid ${preview.canAutomate ? '#c8e6c9' : '#e1bee7'}`,
        display: 'flex', alignItems: 'flex-start', gap: 1.5,
      }}>
        {preview.canAutomate
          ? <AutoFixHighIcon sx={{ color: '#4caf50', mt: 0.25 }} />
          : <MenuBookIcon    sx={{ color: '#9c27b0', mt: 0.25 }} />}
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>{preview.label}</Typography>
          <Typography variant="body2" color="text.secondary">{preview.description}</Typography>
          {preview.estimatedMinutes && (
            <Chip
              label={`~${preview.estimatedMinutes} min`}
              size="small"
              icon={<HourglassEmptyIcon />}
              sx={{ mt: 0.75, fontSize: '0.72rem' }}
            />
          )}
        </Box>
      </Box>

      {/* Resource */}
      {preview.resource && (
        <Box sx={{ mb: 2, p: 1.5, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary">Affected Resource</Typography>
          <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
            {preview.resource.type}: {preview.resource.id || '(resolving…)'}
          </Typography>
        </Box>
      )}

      {/* Tabs */}
      {preview.playbook ? (
        <>
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 1.5 }}>
            <Tab label="What will happen" />
            <Tab label="Manual Playbook" />
          </Tabs>
          {activeTab === 0 && (
            <List dense>
              {preview.steps.map((s, i) => (
                <ListItem key={i} sx={{ py: 0.25 }}>
                  <ListItemIcon sx={{ minWidth: 28 }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>{i + 1}.</Typography>
                  </ListItemIcon>
                  <ListItemText primary={s.name} primaryTypographyProps={{ variant: 'body2' }} />
                </ListItem>
              ))}
            </List>
          )}
          {activeTab === 1 && preview.playbook && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{preview.playbook.summary}</Typography>
              {preview.playbook.cliCommands.length > 0 && (
                <Box sx={{
                  bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1,
                  p: 1.5, fontFamily: 'monospace', fontSize: '0.78rem',
                  whiteSpace: 'pre-wrap', overflowX: 'auto',
                }}>
                  {preview.playbook.cliCommands.join('\n')}
                </Box>
              )}
            </Box>
          )}
        </>
      ) : (
        <>
          <Typography variant="subtitle2" gutterBottom>Steps to be executed:</Typography>
          <List dense>
            {preview.steps.map((s, i) => (
              <ListItem key={i} sx={{ py: 0.25 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>{i + 1}.</Typography>
                </ListItemIcon>
                <ListItemText primary={s.name} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItem>
            ))}
          </List>
        </>
      )}

      {!preview.canAutomate && (
        <Alert severity="info" sx={{ mt: 2 }}>
          This finding type requires human judgment. Use the playbook above to remediate manually, then mark it as Resolved.
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 1, mt: 2.5, justifyContent: 'flex-end' }}>
        <Button onClick={onCancel} disabled={loading}>Cancel</Button>
        {preview.canAutomate && (
          <Button
            variant="contained"
            onClick={onConfirm}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
            sx={{ bgcolor: '#4caf50', '&:hover': { bgcolor: '#388e3c' } }}
          >
            {loading ? 'Starting…' : 'Run Remediation'}
          </Button>
        )}
      </Box>
    </Box>
  );
};

// ── Main Component ───────────────────────────────────────────────────────────
const SecurityAlerts: React.FC = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string[]>(['CRITICAL', 'HIGH']);
  const [statusFilter,   setStatusFilter]   = useState<string[]>(['ACTIVE', 'RESOLVED']);

  // Resolution dialog
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [selectedAlert,     setSelectedAlert]     = useState<SecurityAlert | null>(null);
  const [resolveAction,     setResolveAction]     = useState<ResolutionAction>('RESOLVED');
  const [resolveNote,       setResolveNote]       = useState('');
  const [expandedRow,       setExpandedRow]       = useState<string | null>(null);

  // Remediation dialog state machine
  type RemediatePhase = 'idle' | 'loading-preview' | 'preview' | 'confirming' | 'tracking';
  const [remediateDialogOpen, setRemediateDialogOpen] = useState(false);
  const [remediateAlert,      setRemediateAlert]      = useState<SecurityAlert | null>(null);
  const [remediatePhase,      setRemediatePhase]      = useState<RemediatePhase>('idle');
  const [remediationPreview,  setRemediationPreview]  = useState<RemediationPreview | null>(null);
  const [remediationJob,      setRemediationJob]      = useState<RemediationJob | null>(null);
  const [previewError,        setPreviewError]        = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Snackbar
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });

  const { data: alerts = [], isLoading, error } = useQuery({
    queryKey:       ['securityAlerts'],
    queryFn:        fetchAlerts,
    refetchInterval: 300000,
  });

  const resolveMutation = useMutation({
    mutationFn: resolveAlert,
    onSuccess: (data) => {
      setSnackbar({ open: true, message: `Finding ${data.action?.toLowerCase() || 'resolved'} successfully`, severity: 'success' });
      setResolveDialogOpen(false);
      setSelectedAlert(null);
      setResolveNote('');
      queryClient.invalidateQueries({ queryKey: ['securityAlerts'] });
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message, severity: 'error' });
    },
  });

  // ── Remediation handlers ──────────────────────────────────────────────────

  const openRemediateDialog = async (alert: SecurityAlert) => {
    setRemediateAlert(alert);
    setRemediatePhase('loading-preview');
    setPreviewError(null);
    setRemediationPreview(null);
    setRemediationJob(null);
    setRemediateDialogOpen(true);

    try {
      const preview = await fetchRemediationPreview(alert.id);
      setRemediationPreview(preview);
      setRemediatePhase('preview');
    } catch (e: any) {
      setPreviewError(e.message || 'Failed to load remediation preview');
      setRemediatePhase('preview'); // still show dialog with error
    }
  };

  const handleConfirmRemediation = async () => {
    if (!remediateAlert) return;
    setRemediatePhase('confirming');

    try {
      const job = await startRemediation(remediateAlert.id);
      setRemediationJob(job);
      setRemediatePhase('tracking');

      // Start polling if still running
      if (job.status === 'RUNNING' && job.jobId) {
        startPolling(job.jobId);
      }

      setSnackbar({ open: true, message: `Remediation started: ${job.label}`, severity: 'success' });
    } catch (e: any) {
      setSnackbar({ open: true, message: e.message || 'Failed to start remediation', severity: 'error' });
      setRemediatePhase('preview');
    }
  };

  const startPolling = (jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const updated = await fetchRemediationStatus(jobId);
        setRemediationJob(updated);
        if (updated.status !== 'RUNNING') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          if (updated.status === 'COMPLETED') {
            queryClient.invalidateQueries({ queryKey: ['securityAlerts'] });
          }
        }
      } catch { /* ignore poll errors */ }
    }, 5000);
  };

  const handleRefreshJob = async () => {
    if (!remediationJob?.jobId) return;
    try {
      const updated = await fetchRemediationStatus(remediationJob.jobId);
      setRemediationJob(updated);
    } catch { /* ignore */ }
  };

  const closeRemediateDialog = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    setRemediateDialogOpen(false);
    setRemediatePhase('idle');
    setRemediationPreview(null);
    setRemediationJob(null);
    setPreviewError(null);
  };

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  // ── Filters / counts ──────────────────────────────────────────────────────

  const filteredAlerts = alerts.filter(alert => {
    const matchesSeverity = severityFilter.includes(alert.severity);
    const matchesStatus   = statusFilter.includes(alert.status);
    const matchesText     = !filter
      || alert.type.toLowerCase().includes(filter.toLowerCase())
      || alert.description.toLowerCase().includes(filter.toLowerCase());
    return matchesSeverity && matchesStatus && matchesText;
  });

  const severityCounts: Record<string, number> = {};
  const statusCounts:   Record<string, number> = {};
  alerts.forEach(a => {
    severityCounts[a.severity] = (severityCounts[a.severity] || 0) + 1;
    statusCounts[a.status]     = (statusCounts[a.status]     || 0) + 1;
  });

  const openResolveDialog = (alert: SecurityAlert) => {
    setSelectedAlert(alert);
    setResolveAction('RESOLVED');
    setResolveNote('');
    setResolveDialogOpen(true);
  };

  const handleResolve = () => {
    if (!selectedAlert) return;
    resolveMutation.mutate({ findingId: selectedAlert.id, action: resolveAction, note: resolveNote });
  };

  if (isLoading) return <CircularProgress />;
  if (error)     return <Alert severity="error">{(error as Error).message}</Alert>;

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon color="primary" />
          <Typography variant="h5">System Security Alerts</Typography>
        </Box>
        <Chip
          label={`${statusCounts['ACTIVE'] || 0} Active`}
          color={statusCounts['ACTIVE'] ? 'error' : 'success'}
          variant="filled"
          size="medium"
        />
      </Box>

      {/* Severity Filters */}
      <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap' }}>
        <Typography variant="subtitle2" sx={{ alignSelf: 'center', mr: 1, color: 'text.secondary' }}>Severity:</Typography>
        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
          <Chip
            key={sev}
            label={`${sev} (${severityCounts[sev] || 0})`}
            color={SEVERITY_COLORS[sev]}
            variant={severityFilter.includes(sev) ? 'filled' : 'outlined'}
            onClick={() => setSeverityFilter(prev => prev.includes(sev) ? prev.filter(s => s !== sev) : [...prev, sev])}
            size="small"
            sx={{ cursor: 'pointer', fontWeight: severityFilter.includes(sev) ? 700 : 400 }}
          />
        ))}
      </Box>

      {/* Status Filters */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="subtitle2" sx={{ alignSelf: 'center', mr: 1, color: 'text.secondary' }}>Status:</Typography>
        {['ACTIVE', 'RESOLVED'].map(st => (
          <Chip
            key={st}
            label={`${st} (${statusCounts[st] || 0})`}
            color={STATUS_COLORS[st]}
            variant={statusFilter.includes(st) ? 'filled' : 'outlined'}
            onClick={() => setStatusFilter(prev => prev.includes(st) ? prev.filter(s => s !== st) : [...prev, st])}
            size="small"
            sx={{ cursor: 'pointer', fontWeight: statusFilter.includes(st) ? 700 : 400 }}
          />
        ))}
      </Box>

      <TextField
        label="Search by type or description"
        value={filter}
        onChange={e => setFilter(e.target.value)}
        fullWidth margin="normal" size="small"
      />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Showing {filteredAlerts.length} of {alerts.length} alerts
      </Typography>

      {/* ── Table ─────────────────────────────────────────────────────────── */}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell />
            <TableCell>Status</TableCell>
            <TableCell>Severity</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Detected</TableCell>
            <TableCell>Resolution Date</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredAlerts.map(alert => (
            <React.Fragment key={alert.id}>
              <TableRow
                sx={{
                  bgcolor: alert.status === 'RESOLVED' ? 'rgba(76,175,80,0.04)' : 'inherit',
                  opacity: alert.status === 'RESOLVED' ? 0.8 : 1,
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <TableCell sx={{ width: 32, px: 0.5 }}>
                  <IconButton size="small" onClick={() => setExpandedRow(expandedRow === alert.id ? null : alert.id)}>
                    {expandedRow === alert.id ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </TableCell>
                <TableCell>
                  <Chip
                    label={alert.status}
                    color={STATUS_COLORS[alert.status] || 'default'}
                    size="small"
                    variant={alert.status === 'RESOLVED' ? 'outlined' : 'filled'}
                  />
                </TableCell>
                <TableCell>
                  <Chip label={alert.severity} color={SEVERITY_COLORS[alert.severity]} size="small" />
                </TableCell>
                <TableCell>{alert.description}</TableCell>
                <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary', maxWidth: 200 }}>{alert.type}</TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>{formatDate(alert.createdAt)}</TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                  {alert.resolutionDate ? (
                    <Typography variant="body2" sx={{ color: 'success.main', fontWeight: 500 }}>
                      {formatDate(alert.resolutionDate)}
                    </Typography>
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.disabled' }}>—</Typography>
                  )}
                </TableCell>
                <TableCell align="center">
                  {alert.status === 'ACTIVE' ? (
                    <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                      {/* ── Auto-Remediate ── */}
                      <Tooltip title="Run automated remediation workflow">
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          startIcon={<AutoFixHighIcon />}
                          onClick={() => openRemediateDialog(alert)}
                          sx={{ textTransform: 'none', fontSize: '0.72rem', px: 1.25 }}
                        >
                          Auto-Remediate
                        </Button>
                      </Tooltip>
                      {/* ── Manual resolve / suppress / acknowledge ── */}
                      <Tooltip title="Manually resolve / suppress / acknowledge">
                        <Button
                          size="small"
                          variant="outlined"
                          color="primary"
                          startIcon={<CheckCircleIcon />}
                          onClick={() => openResolveDialog(alert)}
                          sx={{ textTransform: 'none', fontSize: '0.72rem', px: 1.25 }}
                        >
                          Resolve
                        </Button>
                      </Tooltip>
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.disabled">{alert.workflowStatus}</Typography>
                  )}
                </TableCell>
              </TableRow>

              {/* Expanded detail row */}
              <TableRow>
                <TableCell colSpan={8} sx={{ py: 0, borderBottom: expandedRow === alert.id ? undefined : 'none' }}>
                  <Collapse in={expandedRow === alert.id} timeout="auto" unmountOnExit>
                    <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, my: 1 }}>
                      <Typography variant="subtitle2" gutterBottom>Finding Details</Typography>
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, fontSize: '0.85rem' }}>
                        <Box><strong>ID:</strong> {alert.id}</Box>
                        <Box><strong>Workflow:</strong> {alert.workflowStatus}</Box>
                        <Box><strong>Type:</strong> {alert.type}</Box>
                        <Box><strong>Last Updated:</strong> {formatDate(alert.timestamp)}</Box>
                      </Box>
                      <Typography variant="body2" sx={{ mt: 1 }}>{alert.description}</Typography>
                    </Box>
                  </Collapse>
                </TableCell>
              </TableRow>
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      {filteredAlerts.length === 0 && <Typography sx={{ mt: 2 }}>No alerts matching filters.</Typography>}

      {/* ── Auto-Remediate Dialog ──────────────────────────────────────────── */}
      <Dialog
        open={remediateDialogOpen}
        onClose={remediatePhase !== 'confirming' ? closeRemediateDialog : undefined}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoFixHighIcon color="success" />
          Auto-Remediate Security Finding
        </DialogTitle>

        <DialogContent>
          {/* Finding alert banner */}
          {remediateAlert && (
            <Alert
              severity={remediateAlert.severity === 'CRITICAL' ? 'error' : remediateAlert.severity === 'HIGH' ? 'warning' : 'info'}
              sx={{ mb: 2 }}
            >
              <Typography variant="subtitle2">{remediateAlert.description}</Typography>
              <Typography variant="caption" color="text.secondary">{remediateAlert.type}</Typography>
            </Alert>
          )}

          {/* Phase: loading preview */}
          {remediatePhase === 'loading-preview' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
              <CircularProgress size={20} />
              <Typography>Analyzing finding and selecting remediation strategy…</Typography>
            </Box>
          )}

          {/* Phase: preview error */}
          {remediatePhase === 'preview' && previewError && (
            <Alert severity="error">{previewError}</Alert>
          )}

          {/* Phase: preview */}
          {remediatePhase === 'preview' && !previewError && remediationPreview && (
            <PreviewPanel
              preview={remediationPreview}
              onConfirm={handleConfirmRemediation}
              onCancel={closeRemediateDialog}
              loading={false as boolean}
            />
          )}

          {/* Phase: confirming (spinner) */}
          {remediatePhase === 'confirming' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
              <CircularProgress size={20} />
              <Typography>Starting remediation workflow…</Typography>
            </Box>
          )}

          {/* Phase: tracking */}
          {remediatePhase === 'tracking' && remediationJob && (
            <JobTracker
              job={remediationJob}
              onClose={closeRemediateDialog}
              onRefresh={handleRefreshJob}
            />
          )}
        </DialogContent>

        {/* Hide default actions when sub-component handles them */}
        {(remediatePhase === 'loading-preview' || remediatePhase === 'confirming') && (
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={closeRemediateDialog} disabled={remediatePhase === 'confirming'}>Cancel</Button>
          </DialogActions>
        )}
        {remediatePhase === 'preview' && previewError && (
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={closeRemediateDialog}>Close</Button>
          </DialogActions>
        )}
      </Dialog>

      {/* ── Resolution Dialog (manual) ────────────────────────────────────── */}
      <Dialog open={resolveDialogOpen} onClose={() => setResolveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon color="primary" />
          Manually Resolve Finding
        </DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box sx={{ mb: 3 }}>
              <Alert
                severity={selectedAlert.severity === 'CRITICAL' ? 'error' : selectedAlert.severity === 'HIGH' ? 'warning' : 'info'}
                sx={{ mb: 2 }}
              >
                <Typography variant="subtitle2">{selectedAlert.description}</Typography>
                <Typography variant="caption" color="text.secondary">{selectedAlert.type}</Typography>
              </Alert>

              <FormControl component="fieldset" sx={{ width: '100%', mb: 2 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontWeight: 600 }}>Resolution Action</FormLabel>
                <RadioGroup value={resolveAction} onChange={(e) => setResolveAction(e.target.value as ResolutionAction)}>
                  {(Object.entries(ACTION_INFO) as [ResolutionAction, typeof ACTION_INFO[ResolutionAction]][]).map(([key, info]) => (
                    <FormControlLabel
                      key={key}
                      value={key}
                      control={<Radio sx={{ color: info.color, '&.Mui-checked': { color: info.color } }} />}
                      label={
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            {info.icon}
                            <Typography variant="body1" fontWeight={600}>{info.label}</Typography>
                          </Box>
                          <Typography variant="caption" color="text.secondary">{info.description}</Typography>
                        </Box>
                      }
                      sx={{
                        border: '1px solid',
                        borderColor: resolveAction === key ? info.color : 'divider',
                        borderRadius: 1, mb: 1, mx: 0, px: 1.5, py: 0.5,
                        bgcolor: resolveAction === key ? `${info.color}08` : 'transparent',
                      }}
                    />
                  ))}
                </RadioGroup>
              </FormControl>

              <TextField
                label="Resolution Notes"
                placeholder="Describe what was done to remediate this finding..."
                multiline rows={3} fullWidth
                value={resolveNote}
                onChange={(e) => setResolveNote(e.target.value)}
                helperText="Notes are recorded in SecurityHub audit trail"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setResolveDialogOpen(false)} disabled={resolveMutation.isPending}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleResolve}
            disabled={resolveMutation.isPending}
            startIcon={resolveMutation.isPending ? <CircularProgress size={16} /> : ACTION_INFO[resolveAction].icon}
            sx={{ bgcolor: ACTION_INFO[resolveAction].color, '&:hover': { filter: 'brightness(0.9)' } }}
          >
            {resolveMutation.isPending ? 'Processing...' : ACTION_INFO[resolveAction].label}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Snackbar ──────────────────────────────────────────────────────── */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default SecurityAlerts;
