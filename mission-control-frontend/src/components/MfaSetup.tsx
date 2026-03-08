/**
 * MfaSetup — TOTP MFA setup wizard for the current user.
 * Three-step flow: check status → generate QR code → verify TOTP code.
 * Uses AWS Amplify Auth for TOTP provisioning.
 * @module MfaSetup
 */
import React, { useState } from 'react';
import { setUpTOTP, verifyTOTPSetup, updateMFAPreference, fetchMFAPreference, fetchUserAttributes } from 'aws-amplify/auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Paper, Typography, Button, TextField, Box, Alert, Chip, CircularProgress, Stepper, Step, StepLabel, Card, CardContent } from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import QrCode2Icon from '@mui/icons-material/QrCode2';

const MfaSetup: React.FC = () => {
  const queryClient = useQueryClient();
  const [setupStep, setSetupStep] = useState(0);
  const [totpUri, setTotpUri] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Check current MFA status
  const { data: mfaStatus, isLoading } = useQuery({
    queryKey: ['mfaPreference'],
    queryFn: async () => {
      try {
        const pref = await fetchMFAPreference();
        const attrs = await fetchUserAttributes();
        return {
          enabled: pref.preferred === 'TOTP' || (pref.enabled?.includes('TOTP') ?? false),
          preferred: pref.preferred || 'NONE',
          email: attrs.email || '',
        };
      } catch {
        return { enabled: false, preferred: 'NONE', email: '' };
      }
    },
  });

  // Start TOTP setup
  const startSetup = useMutation({
    mutationFn: async () => {
      const output = await setUpTOTP();
      const uri = output.getSetupUri('Mission Control');
      setTotpUri(uri.toString());
      setSecretKey(output.sharedSecret);
      setSetupStep(1);
    },
    onError: (err: Error) => setError(err.message),
  });

  // Verify TOTP code
  const verifySetup = useMutation({
    mutationFn: async () => {
      await verifyTOTPSetup({ code: verifyCode });
      await updateMFAPreference({ totp: 'PREFERRED' });
      setSetupStep(2);
      setSuccess('MFA enabled successfully! You will need your authenticator app for future logins.');
      queryClient.invalidateQueries({ queryKey: ['mfaPreference'] });
    },
    onError: (err: Error) => setError('Invalid code. Please try again. ' + err.message),
  });

  // Disable MFA
  const disableMfa = useMutation({
    mutationFn: async () => {
      await updateMFAPreference({ totp: 'NOT_PREFERRED' });
      setSuccess('MFA has been disabled.');
      setSetupStep(0);
      setTotpUri('');
      setSecretKey('');
      queryClient.invalidateQueries({ queryKey: ['mfaPreference'] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading) return <CircularProgress />;

  return (
    <Paper sx={{ p: 3, maxWidth: 700 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <SecurityIcon color="primary" />
        <Typography variant="h5">Multi-Factor Authentication (MFA)</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      {/* Current Status */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Current Status</Typography>
              <Typography variant="body2" color="text.secondary">
                {mfaStatus?.email && `Account: ${mfaStatus.email}`}
              </Typography>
            </Box>
            <Chip
              icon={mfaStatus?.enabled ? <CheckCircleIcon /> : undefined}
              label={mfaStatus?.enabled ? 'MFA ENABLED' : 'MFA NOT ENABLED'}
              color={mfaStatus?.enabled ? 'success' : 'warning'}
              sx={{ fontWeight: 700 }}
            />
          </Box>
        </CardContent>
      </Card>

      {/* If MFA is already enabled — show disable option */}
      {mfaStatus?.enabled && setupStep === 0 && (
        <Box>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Your account is protected with TOTP-based MFA. You'll need your authenticator app each time you sign in.
          </Typography>
          <Button variant="outlined" color="error" onClick={() => disableMfa.mutate()} disabled={disableMfa.isPending}>
            {disableMfa.isPending ? <CircularProgress size={20} /> : 'Disable MFA'}
          </Button>
        </Box>
      )}

      {/* If MFA not enabled — show setup flow */}
      {!mfaStatus?.enabled && (
        <Box>
          {setupStep === 0 && (
            <Box>
              <Typography variant="body1" sx={{ mb: 2 }}>
                Add an extra layer of security to your account by enabling MFA. You'll need an authenticator app like Google Authenticator, Authy, or 1Password.
              </Typography>
              <Button
                variant="contained"
                size="large"
                startIcon={<QrCode2Icon />}
                onClick={() => startSetup.mutate()}
                disabled={startSetup.isPending}
              >
                {startSetup.isPending ? <CircularProgress size={20} color="inherit" /> : 'Set Up MFA'}
              </Button>
            </Box>
          )}

          {setupStep >= 1 && (
            <Stepper activeStep={setupStep - 1} sx={{ mb: 3 }}>
              <Step completed={setupStep > 1}><StepLabel>Scan QR Code</StepLabel></Step>
              <Step completed={setupStep > 2}><StepLabel>Verify Code</StepLabel></Step>
              <Step completed={setupStep > 2}><StepLabel>Done</StepLabel></Step>
            </Stepper>
          )}

          {setupStep === 1 && (
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                Step 1: Scan this QR code with your authenticator app
              </Typography>
              
              {/* QR Code via Google Charts API */}
              <Box sx={{ textAlign: 'center', my: 2 }}>
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`}
                  alt="TOTP QR Code"
                  style={{ border: '4px solid #e0e0e0', borderRadius: 8 }}
                />
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Can't scan? Enter this key manually:
              </Typography>
              <TextField
                value={secretKey}
                fullWidth
                size="small"
                InputProps={{ readOnly: true }}
                sx={{ mb: 3, fontFamily: 'monospace' }}
              />

              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                Step 2: Enter the 6-digit code from your app
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                <TextField
                  label="Verification Code"
                  value={verifyCode}
                  onChange={e => { setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6)); setError(''); }}
                  placeholder="123456"
                  inputProps={{ maxLength: 6, style: { letterSpacing: '0.5em', fontWeight: 700, fontSize: '1.2rem' } }}
                  sx={{ width: 200 }}
                />
                <Button
                  variant="contained"
                  onClick={() => verifySetup.mutate()}
                  disabled={verifyCode.length !== 6 || verifySetup.isPending}
                  sx={{ mt: 0.5 }}
                >
                  {verifySetup.isPending ? <CircularProgress size={20} color="inherit" /> : 'Verify & Enable'}
                </Button>
              </Box>
            </Box>
          )}

          {setupStep === 2 && (
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <CheckCircleIcon sx={{ fontSize: 64, color: '#4caf50', mb: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>MFA Enabled Successfully!</Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                Your account is now protected. You'll need your authenticator app each time you sign in.
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default MfaSetup;
