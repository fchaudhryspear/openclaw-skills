#!/usr/bin/env python3
"""
NexDev Phase 2B.4 — Generative UX/UI Development
==================================================
Generates production-ready React components from specs and wireframes.
Supports responsive design, accessibility, and modern UI patterns.
"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime


class UIGenerator:
    """Generates React UI components from specifications."""
    
    # Component templates
    COMPONENT_TEMPLATES = {
        "dashboard": {
            "imports": [
                "import React, { useState, useEffect } from 'react';",
                "import { Card, Grid, Typography, Box, CircularProgress } from '@mui/material';",
            ],
            "template": '''
export default function Dashboard() {{
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    fetchDashboardData().then(d => {{
      setData(d);
      setLoading(false);
    }});
  }}, []);

  if (loading) return <CircularProgress />;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>{title}</Typography>
      <Grid container spacing={3}>
        {cards}
      </Grid>
    </Box>
  );
}}
''',
        },
        "form": {
            "imports": [
                "import React, { useState } from 'react';",
                "import { TextField, Button, Box, Alert, Stack } from '@mui/material';",
            ],
            "template": '''
export default function {name}Form() {{
  const [formData, setFormData] = useState({{{initial_state}}});
  const [errors, setErrors] = useState({{}});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleChange = (e) => {{
    setFormData({{ ...formData, [e.target.name]: e.target.value }});
    setErrors({{ ...errors, [e.target.name]: '' }});
  }};

  const validate = () => {{
    const newErrors = {{}};
    {validations}
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }};

  const handleSubmit = async (e) => {{
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {{
      await api.{endpoint}(formData);
      setSuccess(true);
    }} catch (err) {{
      setErrors({{ submit: err.message }});
    }} finally {{
      setSubmitting(false);
    }}
  }};

  return (
    <Box component="form" onSubmit={{handleSubmit}} sx={{{{ maxWidth: 500, mx: 'auto', p: 3 }}}}>
      {{success && <Alert severity="success">Success!</Alert>}}
      {{errors.submit && <Alert severity="error">{{errors.submit}}</Alert>}}
      <Stack spacing={2}>
        {fields}
        <Button type="submit" variant="contained" disabled={{submitting}}>
          {{submitting ? 'Submitting...' : 'Submit'}}
        </Button>
      </Stack>
    </Box>
  );
}}
''',
        },
        "table": {
            "imports": [
                "import React, { useState, useEffect } from 'react';",
                "import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, "
                "TablePagination, TextField, Box, IconButton } from '@mui/material';",
                "import { Edit, Delete, Search } from '@mui/icons-material';",
            ],
            "template": '''
export default function {name}Table() {{
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');

  useEffect(() => {{
    fetchData().then(d => {{ setData(d); setLoading(false); }});
  }}, []);

  const filteredData = data.filter(row =>
    Object.values(row).some(val =>
      String(val).toLowerCase().includes(search.toLowerCase())
    )
  );

  return (
    <Box>
      <TextField
        placeholder="Search..."
        value={{search}}
        onChange={{(e) => setSearch(e.target.value)}}
        InputProps={{{{ startAdornment: <Search /> }}}}
        sx={{{{ mb: 2, width: 300 }}}}
      />
      <TableContainer component={{Paper}}>
        <Table>
          <TableHead>
            <TableRow>
              {headers}
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {{filteredData
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((row) => (
              <TableRow key={{row.id}}>
                {cells}
                <TableCell>
                  <IconButton><Edit /></IconButton>
                  <IconButton color="error"><Delete /></IconButton>
                </TableCell>
              </TableRow>
            ))}}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={{filteredData.length}}
        page={{page}}
        onPageChange={{(_, p) => setPage(p)}}
        rowsPerPage={{rowsPerPage}}
        onRowsPerPageChange={{(e) => {{ setRowsPerPage(parseInt(e.target.value)); setPage(0); }}}}
      />
    </Box>
  );
}}
''',
        },
        "auth_login": {
            "imports": [
                "import React, { useState } from 'react';",
                "import { TextField, Button, Box, Typography, Alert, Paper, Link } from '@mui/material';",
            ],
            "template": '''
export default function LoginPage() {{
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {{
    e.preventDefault();
    setError('');
    setLoading(true);
    try {{
      const response = await fetch('/api/auth/login', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ email, password }}),
      }});
      if (!response.ok) throw new Error('Invalid credentials');
      const {{ token }} = await response.json();
      localStorage.setItem('token', token);
      window.location.href = '/dashboard';
    }} catch (err) {{
      setError(err.message);
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <Box sx={{{{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}}}>
      <Paper sx={{{{ p: 4, maxWidth: 400, width: '100%' }}}}>
        <Typography variant="h5" gutterBottom>Sign In</Typography>
        {{error && <Alert severity="error" sx={{{{ mb: 2 }}}}>{{error}}</Alert>}}
        <form onSubmit={{handleSubmit}}>
          <TextField fullWidth label="Email" type="email" value={{email}}
            onChange={{(e) => setEmail(e.target.value)}} margin="normal" required />
          <TextField fullWidth label="Password" type="password" value={{password}}
            onChange={{(e) => setPassword(e.target.value)}} margin="normal" required />
          <Button fullWidth type="submit" variant="contained" sx={{{{ mt: 2 }}}} disabled={{loading}}>
            {{loading ? 'Signing in...' : 'Sign In'}}
          </Button>
        </form>
        <Typography sx={{{{ mt: 2, textAlign: 'center' }}}}>
          Don't have an account? <Link href="/register">Sign Up</Link>
        </Typography>
      </Paper>
    </Box>
  );
}}
''',
        },
    }
    
    def generate_from_spec(self, spec_data: Dict) -> Dict:
        """Generate a complete UI project from a specification."""
        files = []
        
        # Analyze user stories to determine needed components
        stories = spec_data.get("user_stories", [])
        
        for story in stories:
            title = story.get("title", "").lower()
            
            if "auth" in title or "login" in title:
                files.append(self._generate_auth_pages())
            
            if "dashboard" in title or "analytics" in title:
                files.append(self._generate_dashboard(spec_data))
            
            if any(w in title for w in ["management", "crud", "list"]):
                name = story.get("title", "Item").replace(" ", "")
                files.append(self._generate_crud_pages(name, story))
        
        # Always generate layout and routing
        files.append(self._generate_app_layout(spec_data))
        files.append(self._generate_router(files))
        files.append(self._generate_api_client())
        files.append(self._generate_package_json(spec_data))
        
        return {
            "files": files,
            "framework": "React",
            "ui_library": "Material UI",
            "generated_at": datetime.now().isoformat(),
        }
    
    def _generate_auth_pages(self) -> Dict:
        return {
            "path": "src/pages/Login.jsx",
            "language": "jsx",
            "description": "Login page with email/password authentication",
            "content": "\n".join(self.COMPONENT_TEMPLATES["auth_login"]["imports"]) + 
                       self.COMPONENT_TEMPLATES["auth_login"]["template"],
        }
    
    def _generate_dashboard(self, spec_data: Dict) -> Dict:
        title = spec_data.get("title", "Dashboard")
        return {
            "path": "src/pages/Dashboard.jsx",
            "language": "jsx",
            "description": "Main dashboard with metrics cards",
            "content": f"""import React, {{ useState, useEffect }} from 'react';
import {{ Card, CardContent, Grid, Typography, Box, CircularProgress }} from '@mui/material';

export default function Dashboard() {{
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    fetch('/api/dashboard/stats', {{
      headers: {{ Authorization: `Bearer ${{localStorage.getItem('token')}}` }}
    }})
      .then(r => r.json())
      .then(data => {{ setStats(data); setLoading(false); }})
      .catch(() => setLoading(false));
  }}, []);

  if (loading) return <Box sx={{{{ display: 'flex', justifyContent: 'center', p: 4 }}}}><CircularProgress /></Box>;

  const cards = [
    {{ title: 'Total Users', value: stats?.totalUsers || 0, color: '#1976d2' }},
    {{ title: 'Active Today', value: stats?.activeToday || 0, color: '#2e7d32' }},
    {{ title: 'Revenue', value: `${{stats?.revenue || 0}}`, color: '#ed6c02' }},
    {{ title: 'Open Tickets', value: stats?.openTickets || 0, color: '#d32f2f' }},
  ];

  return (
    <Box sx={{{{ p: 3 }}}}>
      <Typography variant="h4" gutterBottom>{title}</Typography>
      <Grid container spacing={{3}}>
        {{cards.map((card, i) => (
          <Grid item xs={{12}} sm={{6}} md={{3}} key={{i}}>
            <Card sx={{{{ borderTop: `4px solid ${{card.color}}` }}}}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>{{card.title}}</Typography>
                <Typography variant="h4">{{card.value}}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}}
      </Grid>
    </Box>
  );
}}
""",
        }
    
    def _generate_crud_pages(self, name: str, story: Dict) -> Dict:
        return {
            "path": f"src/pages/{name}List.jsx",
            "language": "jsx",
            "description": f"CRUD list page for {name}",
            "content": f"""import React, {{ useState, useEffect }} from 'react';
import {{ Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
         Button, Box, Typography, IconButton, TextField, Chip }} from '@mui/material';
import {{ Edit, Delete, Add, Search }} from '@mui/icons-material';

export default function {name}List() {{
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    fetch('/api/{name.lower()}s', {{
      headers: {{ Authorization: `Bearer ${{localStorage.getItem('token')}}` }}
    }})
      .then(r => r.json())
      .then(data => {{ setItems(data); setLoading(false); }});
  }}, []);

  const filtered = items.filter(item =>
    JSON.stringify(item).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Box sx={{{{ p: 3 }}}}>
      <Box sx={{{{ display: 'flex', justifyContent: 'space-between', mb: 3 }}}}>
        <Typography variant="h5">{name}s</Typography>
        <Button variant="contained" startIcon={{<Add />}}>New {name}</Button>
      </Box>
      <TextField placeholder="Search..." value={{search}} onChange={{e => setSearch(e.target.value)}}
        InputProps={{{{ startAdornment: <Search sx={{{{ mr: 1 }}}} /> }}}}
        sx={{{{ mb: 2, width: 300 }}}} size="small" />
      <TableContainer component={{Paper}}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {{filtered.map(item => (
              <TableRow key={{item.id}} hover>
                <TableCell>{{item.id}}</TableCell>
                <TableCell>{{item.name}}</TableCell>
                <TableCell><Chip label={{item.status}} size="small" /></TableCell>
                <TableCell>{{new Date(item.createdAt).toLocaleDateString()}}</TableCell>
                <TableCell>
                  <IconButton size="small"><Edit /></IconButton>
                  <IconButton size="small" color="error"><Delete /></IconButton>
                </TableCell>
              </TableRow>
            ))}}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}}
""",
        }
    
    def _generate_app_layout(self, spec_data: Dict) -> Dict:
        title = spec_data.get("title", "App")
        return {
            "path": "src/App.jsx",
            "language": "jsx",
            "description": "Main app layout with navigation",
            "content": f"""import React from 'react';
import {{ BrowserRouter, Routes, Route, Navigate }} from 'react-router-dom';
import {{ ThemeProvider, createTheme, CssBaseline }} from '@mui/material';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

const theme = createTheme({{
  palette: {{ mode: 'light', primary: {{ main: '#1976d2' }} }},
}});

function PrivateRoute({{ children }}) {{
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
}}

export default function App() {{
  return (
    <ThemeProvider theme={{theme}}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={{<Login />}} />
          <Route path="/*" element={{
            <PrivateRoute>
              <Layout title="{title}">
                <Routes>
                  <Route path="/" element={{<Dashboard />}} />
                  <Route path="/dashboard" element={{<Dashboard />}} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}}
""",
        }
    
    def _generate_router(self, existing_files: List) -> Dict:
        return {
            "path": "src/components/Layout.jsx",
            "language": "jsx",
            "description": "App layout with sidebar navigation",
            "content": """import React, { useState } from 'react';
import { Box, Drawer, AppBar, Toolbar, Typography, List, ListItem,
         ListItemIcon, ListItemText, IconButton, Avatar } from '@mui/material';
import { Dashboard, Menu, Logout, Settings } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const DRAWER_WIDTH = 240;

export default function Layout({ children, title = 'App' }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const menuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard' },
    { text: 'Settings', icon: <Settings />, path: '/settings' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton color="inherit" onClick={() => setMobileOpen(!mobileOpen)} sx={{ mr: 2, display: { sm: 'none' } }}>
            <Menu />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>{title}</Typography>
          <IconButton color="inherit" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }}>
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer variant="permanent" sx={{ width: DRAWER_WIDTH, '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}>
        <Toolbar />
        <List>
          {menuItems.map((item) => (
            <ListItem button key={item.text} onClick={() => navigate(item.path)}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, ml: { sm: `${DRAWER_WIDTH}px` } }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
""",
        }
    
    def _generate_api_client(self) -> Dict:
        return {
            "path": "src/services/api.js",
            "language": "javascript",
            "description": "API client with auth headers",
            "content": """const API_BASE = process.env.REACT_APP_API_URL || '/api';

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, data) => request(path, { method: 'POST', body: JSON.stringify(data) }),
  put: (path, data) => request(path, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (path) => request(path, { method: 'DELETE' }),
};
""",
        }
    
    def _generate_package_json(self, spec_data: Dict) -> Dict:
        title = spec_data.get("title", "app").lower().replace(" ", "-")
        return {
            "path": "package.json",
            "language": "json",
            "description": "NPM package configuration",
            "content": json.dumps({
                "name": title,
                "version": "1.0.0",
                "private": True,
                "dependencies": {
                    "react": "^18.3.0",
                    "react-dom": "^18.3.0",
                    "react-router-dom": "^6.22.0",
                    "@mui/material": "^5.15.0",
                    "@mui/icons-material": "^5.15.0",
                    "@emotion/react": "^11.11.0",
                    "@emotion/styled": "^11.11.0",
                },
                "scripts": {
                    "start": "react-scripts start",
                    "build": "react-scripts build",
                    "test": "react-scripts test",
                },
            }, indent=2),
        }


if __name__ == "__main__":
    gen = UIGenerator()
    
    spec = {
        "title": "Property Manager Pro",
        "user_stories": [
            {"title": "User Authentication", "description": "Login/register"},
            {"title": "Analytics Dashboard", "description": "Overview metrics"},
            {"title": "Ticket Management", "description": "CRUD for tickets"},
        ],
    }
    
    result = gen.generate_from_spec(spec)
    print(f"Generated {len(result['files'])} UI files:")
    for f in result["files"]:
        lines = f["content"].count("\n")
        print(f"  {f['path']} ({lines} lines) — {f['description']}")
    print(f"\n✅ UI Generator tested")
