/**
 * Users — Cognito user management panel (admin only).
 * Features: list users, create users, enable/disable, password reset, MFA reset, delete.
 * All mutations go through the Mission Control API with admin JWT.
 * @module Users
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAuthSession } from 'aws-amplify/auth';
import { Table, TableBody, TableCell, TableHead, TableRow, Button, TextField, CircularProgress, Alert, Paper, Typography, Dialog, DialogActions, DialogContent, DialogTitle, Select, MenuItem, FormControl, InputLabel, Box, Chip, FormControlLabel, Checkbox } from '@mui/material';

interface CognitoUser {
  Username: string;
  Enabled: boolean;
  UserStatus: string;
  email: string;
}

const fetchUsers = async (): Promise<CognitoUser[]> => {
  const { tokens } = await fetchAuthSession();
  const res = await fetch(import.meta.env.VITE_API_URL + 'users', {
    headers: { Authorization: `Bearer ${tokens?.idToken?.toString()}` },
  });
  if (!res.ok) throw new Error('Failed to fetch users');
  const data = await res.json();
  return data.users || [];
};

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  CONFIRMED: 'success',
  FORCE_CHANGE_PASSWORD: 'warning',
  UNCONFIRMED: 'default',
  RESET_REQUIRED: 'warning',
  COMPROMISED: 'error',
};

const Users: React.FC = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('');
  const [actionConfig, setActionConfig] = useState<{username: string, action: 'enable' | 'disable' | 'delete' | 'reset-mfa'} | null>(null);
  const [resetConfig, setResetConfig] = useState<{username: string, email: string} | null>(null);
  const [tempPassword, setTempPassword] = useState('');
  const [sendEmail, setSendEmail] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [formData, setFormData] = useState({ email: '', givenName: '', familyName: '', group: 'Users' });
  const [resultMsg, setResultMsg] = useState<{type: 'success' | 'error', text: string} | null>(null);

  const { data: users = [], isLoading, error } = useQuery({
    queryKey: ['cognitoUsers'],
    queryFn: fetchUsers,
    refetchInterval: 300000,
  });

  const actionMutation = useMutation({
    mutationFn: async ({ username, action }: { username: string; action: string }) => {
      const { tokens } = await fetchAuthSession();
      const res = await fetch(`${import.meta.env.VITE_API_URL}users/${username}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokens?.idToken?.toString()}` }
      });
      if (!res.ok) throw new Error(`Failed to ${action} user`);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cognitoUsers'] });
      setActionConfig(null);
      setResultMsg({ type: 'success', text: data.message || 'Action completed' });
    },
    onError: (err: Error) => {
      setResultMsg({ type: 'error', text: err.message });
    },
  });

  const resetMutation = useMutation({
    mutationFn: async ({ username, tempPassword, sendEmail }: { username: string; tempPassword: string; sendEmail: boolean }) => {
      const { tokens } = await fetchAuthSession();
      const res = await fetch(`${import.meta.env.VITE_API_URL}users/${username}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens?.idToken?.toString()}` },
        body: JSON.stringify({ tempPassword, sendEmail })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to reset password');
      }
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cognitoUsers'] });
      setResetConfig(null);
      setTempPassword('');
      setResultMsg({ type: 'success', text: data.message || 'Password reset successful' });
    },
    onError: (err: Error) => {
      setResultMsg({ type: 'error', text: err.message });
    },
  });

  const createMutation = useMutation({
    mutationFn: async (newUser: typeof formData) => {
      const { tokens } = await fetchAuthSession();
      const res = await fetch(import.meta.env.VITE_API_URL + 'users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens?.idToken?.toString()}` },
        body: JSON.stringify(newUser)
      });
      if (!res.ok) throw new Error('Failed to create user');
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cognitoUsers'] });
      setCreateOpen(false);
      setFormData({ email: '', givenName: '', familyName: '', group: 'Users' });
      setResultMsg({ type: 'success', text: data.message || 'User created' });
    },
    onError: (err: Error) => {
      setResultMsg({ type: 'error', text: err.message });
    },
  });

  const generateTempPassword = () => {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%';
    let pw = '';
    for (let i = 0; i < 12; i++) pw += chars[Math.floor(Math.random() * chars.length)];
    // Ensure it meets Cognito requirements
    pw = pw.slice(0, 8) + 'A' + 'a' + '1' + '!';
    setTempPassword(pw);
  };

  const filteredUsers = users.filter(user =>
    user.Username.toLowerCase().includes(filter.toLowerCase()) ||
    user.email.toLowerCase().includes(filter.toLowerCase())
  );

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;

  return (
    <Paper sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">User Management</Typography>
        <Button variant="contained" onClick={() => setCreateOpen(true)}>+ Create User</Button>
      </Box>

      {resultMsg && (
        <Alert severity={resultMsg.type} sx={{ mb: 2 }} onClose={() => setResultMsg(null)}>
          {resultMsg.text}
        </Alert>
      )}

      <TextField label="Filter by Username or Email" value={filter} onChange={e => setFilter(e.target.value)} fullWidth margin="normal" size="small" />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{filteredUsers.length} users</Typography>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Email / Username</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Enabled</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredUsers.map(user => (
            <TableRow key={user.Username} sx={{ opacity: user.Enabled ? 1 : 0.6 }}>
              <TableCell>{user.email || user.Username}</TableCell>
              <TableCell>
                <Chip label={user.UserStatus} color={STATUS_COLORS[user.UserStatus] || 'default'} size="small" />
              </TableCell>
              <TableCell>
                <Chip label={user.Enabled ? 'Yes' : 'No'} color={user.Enabled ? 'success' : 'error'} size="small" variant="outlined" />
              </TableCell>
              <TableCell>
                <Button size="small" onClick={() => setActionConfig({username: user.Username, action: user.Enabled ? 'disable' : 'enable'})}>
                  {user.Enabled ? 'Disable' : 'Enable'}
                </Button>
                <Button size="small" onClick={() => { setResetConfig({ username: user.Username, email: user.email || user.Username }); generateTempPassword(); }}>
                  Reset PW
                </Button>
                <Button size="small" color="warning" onClick={() => setActionConfig({username: user.Username, action: 'reset-mfa'})}>
                  Reset MFA
                </Button>
                <Button size="small" color="error" onClick={() => setActionConfig({username: user.Username, action: 'delete'})}>
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Confirm Enable/Disable/Delete Dialog */}
      <Dialog open={!!actionConfig} onClose={() => setActionConfig(null)}>
        <DialogTitle>Confirm {actionConfig?.action}</DialogTitle>
        <DialogContent>
          Are you sure you want to <strong>{actionConfig?.action}</strong> user <strong>{actionConfig?.username}</strong>?
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionConfig(null)}>Cancel</Button>
          <Button
            onClick={() => actionConfig && actionMutation.mutate(actionConfig)}
            color={actionConfig?.action === 'delete' ? 'error' : 'primary'}
            variant="contained"
            disabled={actionMutation.isPending}
          >
            {actionMutation.isPending ? <CircularProgress size={20} /> : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={!!resetConfig} onClose={() => { setResetConfig(null); setTempPassword(''); }} maxWidth="sm" fullWidth>
        <DialogTitle>Reset Password — {resetConfig?.username}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set a temporary password. The user will be required to change it on next login.
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              autoFocus
              label="Temporary Password"
              type="text"
              fullWidth
              value={tempPassword}
              onChange={e => setTempPassword(e.target.value)}
              helperText="Min 8 chars, uppercase, lowercase, number, symbol"
            />
            <Button variant="outlined" size="small" onClick={generateTempPassword} sx={{ whiteSpace: 'nowrap', mb: 2.5 }}>
              Generate
            </Button>
          </Box>
          <FormControlLabel
            control={<Checkbox checked={sendEmail} onChange={e => setSendEmail(e.target.checked)} />}
            label={`Email temp password to ${resetConfig?.email}`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setResetConfig(null); setTempPassword(''); }}>Cancel</Button>
          <Button
            onClick={() => resetConfig && resetMutation.mutate({ username: resetConfig.username, tempPassword, sendEmail })}
            variant="contained"
            disabled={!tempPassword || tempPassword.length < 8 || resetMutation.isPending}
          >
            {resetMutation.isPending ? <CircularProgress size={20} /> : 'Reset Password'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create User Dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New User</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Email Address" type="email" fullWidth required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
          <TextField margin="dense" label="First Name" fullWidth value={formData.givenName} onChange={e => setFormData({...formData, givenName: e.target.value})} />
          <TextField margin="dense" label="Last Name" fullWidth value={formData.familyName} onChange={e => setFormData({...formData, familyName: e.target.value})} />
          <FormControl fullWidth margin="dense">
            <InputLabel>Access Group</InputLabel>
            <Select value={formData.group} label="Access Group" onChange={e => setFormData({...formData, group: e.target.value})}>
              <MenuItem value="Users">Users</MenuItem>
              <MenuItem value="ReadOnly">ReadOnly</MenuItem>
              <MenuItem value="Admins">Admins</MenuItem>
              <MenuItem value="GlobalAdmins">GlobalAdmins</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button onClick={() => createMutation.mutate(formData)} variant="contained" disabled={!formData.email || createMutation.isPending}>
            {createMutation.isPending ? <CircularProgress size={24} /> : 'Create User'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default Users;
