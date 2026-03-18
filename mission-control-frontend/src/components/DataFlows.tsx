/**
 * DataFlows — Lending data lake pipeline monitor.
 * Shows data flow metrics: webhook intake → S3 staging → Snowflake warehouse.
 * Displays pipeline health, record counts, and freshness indicators.
 * @module DataFlows
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAuthSession } from 'aws-amplify/auth';
import { Paper, Typography, CircularProgress, Alert, Table, TableHead, TableRow, TableCell, TableBody, Box, Chip, Grid, Card, CardContent } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';

interface FlowMetric {
  Date: string;
  FlowType: string;
  Count: number;
}

interface HealthStatus {
  status: string;
  timestamp: string;
  services: {
    dynamodb: string;
    cognito: string;
    securityhub: string;
    snowflake: string;
  };
}

interface SecuritySummary {
  total: number;
  critical: number;
  high: number;
}

const getAuthHeaders = async () => {
  const { tokens } = await fetchAuthSession();
  return { Authorization: `Bearer ${tokens?.idToken?.toString()}` };
};

const fetchHealth = async (): Promise<HealthStatus> => {
  const headers = await getAuthHeaders();
  const res = await fetch(import.meta.env.VITE_API_URL + 'health', { headers });
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
};

const fetchFlows = async (): Promise<FlowMetric[]> => {
  const headers = await getAuthHeaders();
  const res = await fetch(import.meta.env.VITE_API_URL + 'flows', { headers });
  if (!res.ok) throw new Error('Failed to fetch data flows');
  const data = await res.json();
  return data.metrics || [];
};

const fetchAlertSummary = async (): Promise<SecuritySummary> => {
  const headers = await getAuthHeaders();
  const res = await fetch(import.meta.env.VITE_API_URL + 'security-alerts', { headers });
  if (!res.ok) throw new Error('Failed to fetch alerts');
  const data = await res.json();
  const alerts = (data.alerts || []).filter((a: { status: string }) => a.status === 'ACTIVE');
  return {
    total: alerts.length,
    critical: alerts.filter((a: { severity: string }) => a.severity === 'CRITICAL').length,
    high: alerts.filter((a: { severity: string }) => a.severity === 'HIGH').length,
  };
};

const ServiceStatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'connected') return <CheckCircleIcon sx={{ color: '#4caf50', fontSize: 20 }} />;
  if (status === 'not_configured') return <RemoveCircleOutlineIcon sx={{ color: '#9e9e9e', fontSize: 20 }} />;
  if (status === 'error' || status === 'table_missing') return <ErrorIcon sx={{ color: '#f44336', fontSize: 20 }} />;
  return <WarningIcon sx={{ color: '#ff9800', fontSize: 20 }} />;
};

const statusLabel = (s: string) => {
  if (s === 'connected') return 'Connected';
  if (s === 'not_configured') return 'Not Configured';
  if (s === 'error') return 'Error';
  if (s === 'table_missing') return 'Table Missing';
  return s;
};

const statusColor = (s: string): 'success' | 'error' | 'warning' | 'default' => {
  if (s === 'connected') return 'success';
  if (s === 'not_configured') return 'default';
  return 'error';
};

const DataFlows: React.FC = () => {
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  });

  const { data: flows = [], isLoading: flowsLoading, error: flowsError } = useQuery({
    queryKey: ['dataFlows'],
    queryFn: fetchFlows,
    refetchInterval: 30000,
  });

  const { data: alertSummary } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: fetchAlertSummary,
    refetchInterval: 300000,
  });

  return (
    <Box>
      {/* System Health Banner */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5">System Health</Typography>
          {health && (
            <Chip
              label={health.status === 'healthy' ? 'ALL SYSTEMS OPERATIONAL' : 'DEGRADED'}
              color={health.status === 'healthy' ? 'success' : 'warning'}
              sx={{ fontWeight: 700, fontSize: '0.85rem' }}
            />
          )}
        </Box>

        {healthLoading && <CircularProgress size={24} />}
        {healthError && <Alert severity="error">Failed to fetch system health</Alert>}

        {health && (
          <>
            <Grid container spacing={2}>
              {Object.entries(health.services).map(([name, status]) => (
                <Grid item xs={6} sm={3} key={name}>
                  <Card variant="outlined" sx={{ textAlign: 'center', py: 1 }}>
                    <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                      <ServiceStatusIcon status={status} />
                      <Typography variant="subtitle2" sx={{ textTransform: 'capitalize', fontWeight: 600, mt: 0.5 }}>
                        {name === 'securityhub' ? 'Security Hub' : name === 'dynamodb' ? 'DynamoDB' : name.charAt(0).toUpperCase() + name.slice(1)}
                      </Typography>
                      <Chip label={statusLabel(status)} color={statusColor(status)} size="small" sx={{ mt: 0.5 }} />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Last checked: {new Date(health.timestamp).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CST
            </Typography>
          </>
        )}
      </Paper>

      {/* Security Summary */}
      {alertSummary && alertSummary.total > 0 && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: alertSummary.critical > 0 ? '#fff3f0' : '#fff8e1' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {alertSummary.critical > 0 ? (
              <ErrorIcon sx={{ color: '#f44336' }} />
            ) : (
              <WarningIcon sx={{ color: '#ff9800' }} />
            )}
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {alertSummary.total} Security Alert{alertSummary.total !== 1 ? 's' : ''}
            </Typography>
            <Chip label={`${alertSummary.critical} Critical`} color="error" size="small" />
            <Chip label={`${alertSummary.high} High`} color="warning" size="small" />
          </Box>
        </Paper>
      )}

      {/* Data Flows */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>Data Lake Flows</Typography>

        {flowsLoading && <CircularProgress size={24} />}
        {flowsError && <Alert severity="error">{(flowsError as Error).message}</Alert>}

        {!flowsLoading && !flowsError && (
          <>
            {flows.length === 0 ? (
              <Typography color="text.secondary">No data flows recorded for today.</Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Flow Type</TableCell>
                    <TableCell>Count</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {flows.map((flow, index) => (
                    <TableRow key={index}>
                      <TableCell>{flow.Date}</TableCell>
                      <TableCell>{flow.FlowType}</TableCell>
                      <TableCell>{flow.Count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </Paper>
    </Box>
  );
};

export default DataFlows;
