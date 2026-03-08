/**
 * TestRunner — Backend integration test runner.
 * Triggers CodeBuild test suite or inline health checks via the API.
 * Shows real-time test results with pass/fail/skip indicators.
 * @module TestRunner
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { fetchAuthSession } from 'aws-amplify/auth';
import { Paper, Typography, Button, CircularProgress, Alert, Box, List, ListItem, ListItemIcon, ListItemText, Chip, Collapse, LinearProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

interface TestResult {
  name: string;
  status: 'PASS' | 'FAIL' | 'SKIP' | 'RUNNING';
  reason?: string;
}

interface TestRunResult {
  status: string;
  mode: string;
  tests_run: number;
  passed: number;
  failed: number;
  skipped: number;
  results: TestResult[];
  timestamp: string;
}

const TestRunner: React.FC = () => {
  const [runResult, setRunResult] = useState<TestRunResult | null>(null);
  const [liveTests, setLiveTests] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [expandedTest, setExpandedTest] = useState<string | null>(null);

  const testNames = ['Cognito', 'SecurityHub', 'Snowflake'];

  const runTests = useMutation({
    mutationFn: async () => {
      setIsRunning(true);
      setRunResult(null);
      setLiveTests([]);

      // Animate tests appearing one by one
      const animatedTests: TestResult[] = [];
      for (const name of testNames) {
        animatedTests.push({ name, status: 'RUNNING' });
        setLiveTests([...animatedTests]);
        // Small delay for visual effect
        await new Promise(r => setTimeout(r, 300));
      }

      // Actually call the API
      const { tokens } = await fetchAuthSession();
      const res = await fetch(import.meta.env.VITE_API_URL + 'run-tests', {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokens?.idToken?.toString()}` }
      });
      if (!res.ok) throw new Error('Failed to start tests');
      const data: TestRunResult = await res.json();

      // Animate results coming in one by one
      for (let i = 0; i < data.results.length; i++) {
        const updated = [...animatedTests];
        updated[i] = data.results[i];
        setLiveTests([...updated]);
        await new Promise(r => setTimeout(r, 500));
      }

      setRunResult(data);
      setIsRunning(false);
      return data;
    },
    onError: () => {
      setIsRunning(false);
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS': return <CheckCircleIcon sx={{ color: '#4caf50', fontSize: 28 }} />;
      case 'FAIL': return <CancelIcon sx={{ color: '#f44336', fontSize: 28 }} />;
      case 'SKIP': return <SkipNextIcon sx={{ color: '#9e9e9e', fontSize: 28 }} />;
      case 'RUNNING': return <HourglassEmptyIcon sx={{ color: '#ff9800', fontSize: 28, animation: 'spin 1s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} />;
      default: return <HourglassEmptyIcon sx={{ color: '#bbb', fontSize: 28 }} />;
    }
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'PASS': return <Chip label="PASSED" color="success" size="small" sx={{ fontWeight: 700 }} />;
      case 'FAIL': return <Chip label="FAILED" color="error" size="small" sx={{ fontWeight: 700 }} />;
      case 'SKIP': return <Chip label="SKIPPED" color="default" size="small" />;
      case 'RUNNING': return <Chip label="TESTING..." color="warning" size="small" variant="outlined" />;
      default: return <Chip label="PENDING" color="default" size="small" variant="outlined" />;
    }
  };

  const allDone = runResult !== null;
  const overallStatus = allDone
    ? (runResult.failed > 0 ? 'FAILED' : 'PASSED')
    : (isRunning ? 'RUNNING' : 'IDLE');

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">Test Runner</Typography>
        {allDone && (
          <Chip
            label={overallStatus === 'PASSED' ? `ALL TESTS PASSED (${runResult.passed}/${runResult.tests_run})` : `${runResult.failed} TESTS FAILED`}
            color={overallStatus === 'PASSED' ? 'success' : 'error'}
            sx={{ fontWeight: 700, fontSize: '0.85rem' }}
          />
        )}
      </Box>

      <Button
        variant="contained"
        size="large"
        startIcon={isRunning ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
        onClick={() => runTests.mutate()}
        disabled={isRunning}
        sx={{ mb: 3 }}
      >
        {isRunning ? 'Running Tests...' : 'Run All Tests'}
      </Button>

      {runTests.error && <Alert severity="error" sx={{ mb: 2 }}>{(runTests.error as Error).message}</Alert>}

      {/* Progress bar while running */}
      {isRunning && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress color="warning" />
        </Box>
      )}

      {/* Test Results List */}
      {liveTests.length > 0 && (
        <List sx={{ bgcolor: 'background.paper', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
          {liveTests.map((test, idx) => (
            <React.Fragment key={test.name}>
              <ListItem
                sx={{
                  borderBottom: idx < liveTests.length - 1 ? '1px solid' : 'none',
                  borderColor: 'divider',
                  cursor: test.reason ? 'pointer' : 'default',
                  transition: 'background-color 0.3s',
                  bgcolor: test.status === 'PASS' ? 'rgba(76,175,80,0.04)'
                    : test.status === 'FAIL' ? 'rgba(244,67,54,0.04)'
                    : test.status === 'RUNNING' ? 'rgba(255,152,0,0.04)'
                    : 'inherit',
                  '&:hover': test.reason ? { bgcolor: 'rgba(0,0,0,0.04)' } : {},
                }}
                onClick={() => test.reason && setExpandedTest(expandedTest === test.name ? null : test.name)}
              >
                <ListItemIcon sx={{ minWidth: 44 }}>
                  {getStatusIcon(test.status)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {test.name} Connectivity
                    </Typography>
                  }
                  secondary={
                    test.status === 'RUNNING' ? 'Testing connection...'
                    : test.status === 'PASS' ? 'Service is reachable and responding'
                    : test.status === 'FAIL' ? 'Service is not responding'
                    : test.reason || 'Test skipped'
                  }
                />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {getStatusChip(test.status)}
                  {test.reason && (expandedTest === test.name ? <ExpandLessIcon /> : <ExpandMoreIcon />)}
                </Box>
              </ListItem>
              {test.reason && (
                <Collapse in={expandedTest === test.name}>
                  <Box sx={{ px: 4, py: 1, bgcolor: 'grey.50', borderBottom: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Details:</strong> {test.reason}
                    </Typography>
                  </Box>
                </Collapse>
              )}
            </React.Fragment>
          ))}
        </List>
      )}

      {/* Summary */}
      {allDone && (
        <Box sx={{ mt: 3, p: 2, borderRadius: 1, bgcolor: runResult.failed > 0 ? 'rgba(244,67,54,0.05)' : 'rgba(76,175,80,0.05)', border: '1px solid', borderColor: runResult.failed > 0 ? 'error.light' : 'success.light' }}>
          <Typography variant="subtitle2" gutterBottom>Test Summary</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Chip label={`${runResult.passed} Passed`} color="success" size="small" variant="outlined" />
            {runResult.failed > 0 && <Chip label={`${runResult.failed} Failed`} color="error" size="small" variant="outlined" />}
            {runResult.skipped > 0 && <Chip label={`${runResult.skipped} Skipped`} color="default" size="small" variant="outlined" />}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Completed: {new Date(runResult.timestamp).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CST • Mode: {runResult.mode}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default TestRunner;
