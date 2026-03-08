/**
 * AppLayout — Main navigation layout with sidebar drawer.
 * Provides authenticated app shell with navigation to all Mission Control sections.
 * Uses MUI Drawer + AppBar pattern.
 * @module AppLayout
 */
import React from 'react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { Box, Drawer, AppBar, Toolbar, Typography, Button, List, ListItem, ListItemButton, ListItemText, CssBaseline } from '@mui/material';

const drawerWidth = 240;

interface AppLayoutProps {
  component: React.ReactElement;
  title: string;
}

const AppLayout: React.FC<AppLayoutProps> = ({ component, title }) => {
  const { signOut } = useAuthenticator();

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Mission Control — Credologi
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Button color="inherit" onClick={() => signOut()}>
            Sign Out
          </Button>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            <ListItem disablePadding>
              <ListItemButton onClick={() => window.location.pathname === '/' ? null : (window.location.pathname = '/')}>
                <ListItemText primary="Dashboard" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton onClick={() => window.location.pathname === '/users' ? null : (window.location.pathname = '/users')}>
                <ListItemText primary="Users" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton onClick={() => window.location.pathname === '/security-alerts' ? null : (window.location.pathname = '/security-alerts')}>
                <ListItemText primary="Security" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton onClick={() => window.location.pathname === '/test-runner' ? null : (window.location.pathname = '/test-runner')}>
                <ListItemText primary="Tests" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Typography variant="h4" gutterBottom>{title}</Typography>
        {component}
      </Box>
    </Box>
  );
};

export default AppLayout;
