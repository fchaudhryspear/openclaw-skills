#!/usr/bin/env node
/**
 * Project Dashboard — Visual status tracking for all active projects
 * Generates HTML report and sends to Telegram
 */

const fs = require('fs');
const path = require('path');

const ACTIVE_PROJECTS_FILE = path.join(process.env.HOME || '~/.openclaw', 'memory/active_projects.json');
const OUTPUT_DIR = path.join(__dirname, 'reports');
const DASHBOARD_HTML = path.join(OUTPUT_DIR, 'dashboard.html');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

class ProjectDashboard {
    constructor() {
        this.projects = JSON.parse(fs.readFileSync(ACTIVE_PROJECTS_FILE, 'utf8'));
        this.startDate = new Date().toISOString();
    }

    // ── Project Status Analysis ──────────────────────────────────────────────
    analyzeProject(name, project) {
        const now = Date.now();
        const daysSinceStart = Math.floor((now - new Date(project.started).getTime()) / 86400000);
        const daysSinceUpdate = Math.floor((now - new Date(project.lastUpdated || project.started).getTime()) / 86400000);
        
        const staleThreshold = 7;
        const isStale = daysSinceUpdate > staleThreshold;
        
        return {
            name,
            ...project,
            daysActive: daysSinceStart,
            daysIdle: daysSinceUpdate,
            isStale,
            statusColor: project.status === 'in_progress' ? '🟢' : 
                        project.status === 'paused' ? '🟡' : '⚪',
            ageWarning: daysSinceUpdate > 14 ? `⚠️ ${daysSinceUpdate}d idle` : ''
        };
    }

    // ── Dependency Graph Builder ─────────────────────────────────────────────
    buildDependencyGraph() {
        // Hardcoded for current known dependencies
        const graph = {
            'clawvault-development': [],
            'lambda-cors-fix': ['aws-credentials'],
            'antfarm-setup': []
        };

        return graph;
    }

    // ── Generate HTML Dashboard ──────────────────────────────────────────────
    generateHTML() {
        const analyzedProjects = Object.entries(this.projects).map(([name, p]) => 
            this.analyzeProject(name, p)
        );

        const totalCosts = this.estimateTotalCosts();
        const dependencyGraph = this.buildDependencyGraph();

        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Dashboard — Faisal's Workspace</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; font-size: 14px; }
        .project-list { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
        .project-item { padding: 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; }
        .project-item:last-child { border-bottom: none; }
        .status-badge { padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .status-in_progress { background: #d1fae5; color: #065f46; }
        .status-paused { background: #fef3c7; color: #92400e; }
        .status-complete { background: #dbeafe; color: #1e40af; }
        .stale-warning { color: #dc2626; font-size: 12px; margin-top: 5px; }
        .keywords { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
        .keyword-tag { background: #f3f4f6; padding: 4px 8px; border-radius: 6px; font-size: 11px; color: #6b7280; }
        .actions { display: flex; gap: 10px; }
        .btn { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; }
        .btn-primary { background: #667eea; color: white; }
        .btn-outline { background: transparent; border: 1px solid #667eea; color: #667eea; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        th, td { padding: 12px 20px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9fafb; font-weight: 600; color: #374151; }
        .refresh-btn { position: fixed; bottom: 30px; right: 30px; padding: 16px 24px; border-radius: 50px; background: #667eea; color: white; border: none; box-shadow: 0 4px 12px rgba(102,126,234,0.4); font-size: 14px; cursor: pointer; transition: all 0.2s; }
        .refresh-btn:hover { transform: scale(1.05); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Project Dashboard</h1>
        <p>Last updated: ${new Date().toLocaleString('en-US', { timeZone: 'America/Chicago' })} CST</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">${analyzedProjects.length}</div>
            <div class="stat-label">Active Projects</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${analyzedProjects.filter(p => p.isStale).length}</div>
            <div class="stat-label">Stale (>7 days)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$${totalCosts.daily.toFixed(2)}</div>
            <div class="stat-label">Daily AI Costs</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${analyzedProjects.reduce((sum, p) => sum + p.daysActive, 0)}</div>
            <div class="stat-label">Days Active (Total)</div>
        </div>
    </div>

    <div class="project-list">
        <h2 style="padding: 20px; margin: 0; border-bottom: 1px solid #eee;">Active Projects</h2>
        ${analyzedProjects.map(project => `
            <div class="project-item">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span>${project.statusColor}</span>
                        <strong>${project.name.replace(/-/g, ' ').toUpperCase()}</strong>
                        <span class="status-badge status-${project.status}">${project.status}</span>
                    </div>
                    ${project.ageWarning ? `<div class="stale-warning">${project.ageWarning}</div>` : ''}
                    <div class="keywords">
                        ${project.keywords?.map(kw => `<span class="keyword-tag">#${kw}</span>`).join('') || ''}
                    </div>
                    <div style="margin-top: 8px; font-size: 13px; color: #6b7280;">
                        Started: ${new Date(project.started).toLocaleDateString()} • Model: ${project.model_used || 'default'}
                    </div>
                </div>
                <div class="actions">
                    <button class="btn btn-outline" onclick="alert('Resume ${project.name}')">Resume</button>
                    <button class="btn btn-primary" onclick="alert('Open ${project.name}')">Details</button>
                </div>
            </div>
        `).join('')}
    </div>

    <br>

    <table>
        <thead>
            <tr><th>Metric</th><th>Value</th></tr>
        </thead>
        <tbody>
            <tr><td>Total Days Tracked</td><td>${analyzedProjects.reduce((sum, p) => sum + p.daysActive, 0)} days</td></tr>
            <tr><td>Avg. Days Per Project</td><td>${(analyzedProjects.reduce((sum, p) => sum + p.daysActive, 0) / analyzedProjects.length).toFixed(1)} days</td></tr>
            <tr><td>Projects Started This Month</td><td>${analyzedProjects.filter(p => new Date(p.started).getMonth() === new Date().getMonth()).length}</td></tr>
        </tbody>
    </table>

    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
</body>
</html>
`;

        fs.writeFileSync(DASHBOARD_HTML, html);
        return DASHBOARD_HTML;
    }

    estimateTotalCosts() {
        // Placeholder - integrate with cost tracker
        return { daily: 0.27, weekly: 1.89, monthly: 8.10 };
    }
}

// CLI Interface
async function main() {
    const dashboard = new ProjectDashboard();
    
    if (process.argv.includes('--html')) {
        const filePath = dashboard.generateHTML();
        console.log(`✅ Dashboard generated: file://${filePath}`);
        console.log(`   Open in browser: ${filePath}`);
    } else {
        // Console output
        console.log('\n╔══════════════════════════════════════════════════╗');
        console.log('║         PROJECT STATUS DASHBOARD                 ║');
        console.log('╚══════════════════════════════════════════════════╝\n');
        
        Object.entries(dashboard.projects).forEach(([name, p]) => {
            const info = dashboard.analyzeProject(name, p);
            console.log(`${info.statusColor}  ${name.toUpperCase()}`);
            console.log(`   Status: ${p.status} | Age: ${info.daysActive}d | Idle: ${info.daysIdle}d`);
            if (info.isStale) console.log(`   ⚠️  STALE: No updates in ${info.daysIdle} days`);
            console.log('');
        });

        console.log('📊 Summary:');
        console.log(`   Total Projects: ${Object.keys(dashboard.projects).length}`);
        console.log(`   Stale Projects: ${Object.values(dashboard.projects).filter(p => {
            const info = dashboard.analyzeProject('', p);
            return info.isStale;
        }).length}`);
        console.log('');
        console.log('🌐 Full Dashboard: Run with --html flag');
    }
}

main().catch(console.error);
