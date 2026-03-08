/**
 * Mission Control — Application entry point.
 * Configures AWS Amplify, React Query, and React Router.
 * Wraps app in Authenticator for Cognito auth.
 * @module Main
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Amplify } from 'aws-amplify';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import Users from './components/Users';
import DataFlows from './components/DataFlows';
import SecurityAlerts from './components/SecurityAlerts';
import TestRunner from './components/TestRunner';
import AppLayout from './AppLayout';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_CLIENT_ID,
      loginWith: {
        username: true,
      },
    }
  }
});

const queryClient = new QueryClient();
const theme = createTheme();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <Authenticator hideSignUp>
          <Router>
            <Routes>
              <Route path="/" element={<AppLayout component={<DataFlows />} title="Data Lake Flows" />} />
              <Route path="/users" element={<AppLayout component={<Users />} title="User Management" />} />
              <Route path="/flows" element={<AppLayout component={<DataFlows />} title="Data Lake Flows" />} />
              <Route path="/security-alerts" element={<AppLayout component={<SecurityAlerts />} title="Security Alerts" />} />
              <Route path="/test-runner" element={<AppLayout component={<TestRunner />} title="Test Runner" />} />
            </Routes>
          </Router>
        </Authenticator>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>
);
