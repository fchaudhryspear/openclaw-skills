/**
 * SecurityAlerts — AWS SecurityHub findings viewer with remediation workflow.
 * Displays active and resolved security findings with severity indicators.
 * Supports search/filter and inline resolution/suppression of findings.
 * @module SecurityAlerts
 * @version 2.2.0
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAuthSession } from 'aws-amplify/auth';
import {
  Table, TableBody, TableCell, TableHead, TableRow, TextField,
  CircularProgress, Alert, Paper, Typography, Box, Chip,
  Button, Dialog, DialogTitle, DialogContent, DialogActions,
  RadioGroup, FormControlLabel, Radio, FormControl, FormLabel,
  Snackbar, IconButton, Tooltip, Collapse,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import BlockIcon from '@mui/icons-material/Block';
import NotificationsIcon from '@mui/icons-material/Notifications';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

// ── Types ───────────────────────────────────────────────────────────────
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

// ── Constants ───────────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  MEDIUM: 'info',
  LOW: 'default',
};

const STATUS_COLORS: Record<string, 'error' | 'success' | 'default'> = {
  ACTIVE: 'error',
  RESOLVED: 'success',
};

const ACTION_INFO: Record<ResolutionAction, { label: string; description: string; icon: React.ReactNode; color: string }> = {
  RESOLVED: {
    label: 'Resolve',
    description: 'Mark as remediated — the underlying issue has been fixed.',
    icon: <CheckCircleIcon fontSize="small" />,
    color: '#4caf50',
  },
  SUPPRESSED: {
    label: 'Suppress',
    description: 'False positive or accepted risk — hide from active view.',
    icon: <BlockIcon fontSize="small" />,
    color: '#ff9800',
  },
  NOTIFIED: {
    label: 'Acknowledge',
    description: 'Acknowledged and under investigation — keep visible.',
    icon: <NotificationsIcon fontSize="small" />,
    color: '#2196f3',
  },
};

const API_URL = import.meta.env.VITE_API_URL;

// ── API Functions ───────────────────────────────────────────────────────
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

// ── Helpers ─────────────────────────────────────────────────────────────
const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

// ── Component ───────────────────────────────────────────────────────────
const SecurityAlerts: React.FC = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string[]>(['CRITICAL', 'HIGH']);
  const [statusFilter, setStatusFilter] = useState<string[]>(['ACTIVE', 'RESOLVED']);

  // Resolution dialog state
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<SecurityAlert | null>(null);
  const [resolveAction, setResolveAction] = useState<ResolutionAction>('RESOLVED');
  const [resolveNote, setResolveNote] = useState('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // Snackbar
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });

  const { data: alerts = [], isLoading, error } = useQuery({
    queryKey: ['securityAlerts'],
    queryFn: fetchAlerts,
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

  const filteredAlerts = alerts.filter(alert => {
    const matchesSeverity = severityFilter.includes(alert.severity);
    const matchesStatus = statusFilter.includes(alert.status);
    const matchesText = !filter
      || alert.type.toLowerCase().includes(filter.toLowerCase())
      || alert.description.toLowerCase().includes(filter.toLowerCase());
    return matchesSeverity && matchesStatus && matchesText;
  });

  // Counts
  const severityCounts: Record<string, number> = {};
  const statusCounts: Record<string, number> = {};
  alerts.forEach(a => {
    severityCounts[a.severity] = (severityCounts[a.severity] || 0) + 1;
    statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
  });

  const openResolveDialog = (alert: SecurityAlert) => {
    setSelectedAlert(alert);
    setResolveAction('RESOLVED');
    setResolveNote('');
    setResolveDialogOpen(true);
  };

  const handleResolve = () => {
    if (!selectedAlert) return;
    resolveMutation.mutate({
      findingId: selectedAlert.id,
      action: resolveAction,
      note: resolveNote,
    });
  };

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;

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
        fullWidth
        margin="normal"
        size="small"
      />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Showing {filteredAlerts.length} of {alerts.length} alerts
      </Typography>

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
                  <IconButton
                    size="small"
                    onClick={() => setExpandedRow(expandedRow === alert.id ? null : alert.id)}
                  >
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
                    <Tooltip title="Resolve / Remediate">
                      <Button
                        size="small"
                        variant="outlined"
                        color="success"
                        startIcon={<CheckCircleIcon />}
                        onClick={() => openResolveDialog(alert)}
                        sx={{ textTransform: 'none', fontSize: '0.75rem' }}
                      >
                        Remediate
                      </Button>
                    </Tooltip>
                  ) : (
                    <Typography variant="caption" color="text.disabled">
                      {alert.workflowStatus}
                    </Typography>
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

      {/* ── Resolution Dialog ──────────────────────────────────────────── */}
      <Dialog
        open={resolveDialogOpen}
        onClose={() => setResolveDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon color="primary" />
          Remediate Security Finding
        </DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box sx={{ mb: 3 }}>
              <Alert severity={selectedAlert.severity === 'CRITICAL' ? 'error' : selectedAlert.severity === 'HIGH' ? 'warning' : 'info'} sx={{ mb: 2 }}>
                <Typography variant="subtitle2">{selectedAlert.description}</Typography>
                <Typography variant="caption" color="text.secondary">{selectedAlert.type}</Typography>
              </Alert>

              <FormControl component="fieldset" sx={{ width: '100%', mb: 2 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontWeight: 600 }}>Resolution Action</FormLabel>
                <RadioGroup
                  value={resolveAction}
                  onChange={(e) => setResolveAction(e.target.value as ResolutionAction)}
                >
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
                        borderRadius: 1,
                        mb: 1,
                        mx: 0,
                        px: 1.5,
                        py: 0.5,
                        bgcolor: resolveAction === key ? `${info.color}08` : 'transparent',
                      }}
                    />
                  ))}
                </RadioGroup>
              </FormControl>

              <TextField
                label="Resolution Notes"
                placeholder="Describe what was done to remediate this finding..."
                multiline
                rows={3}
                fullWidth
                value={resolveNote}
                onChange={(e) => setResolveNote(e.target.value)}
                helperText="Notes are recorded in SecurityHub audit trail"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setResolveDialogOpen(false)} disabled={resolveMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleResolve}
            disabled={resolveMutation.isPending}
            startIcon={resolveMutation.isPending ? <CircularProgress size={16} /> : ACTION_INFO[resolveAction].icon}
            sx={{
              bgcolor: ACTION_INFO[resolveAction].color,
              '&:hover': { bgcolor: ACTION_INFO[resolveAction].color, filter: 'brightness(0.9)' },
            }}
          >
            {resolveMutation.isPending ? 'Processing...' : ACTION_INFO[resolveAction].label}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Snackbar ──────────────────────────────────────────────────── */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default SecurityAlerts;
