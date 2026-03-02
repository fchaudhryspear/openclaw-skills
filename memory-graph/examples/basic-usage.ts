/**
 * Basic Usage Example - Demonstrate Memory Graph Features
 */

import { MemoryGraph } from '../src/api/memory-graph';
import { AccessLevel, Role } from '../src/model/types';

async function main() {
  console.log('🧠 Typed Memory Graph Demo\n');

  // Initialize the graph
  const graph = await MemoryGraph.create({
    storagePath: './demo-storage',
    encryptionKey: 'my-secure-encryption-key-2024',
    defaultAccessLevel: AccessLevel.PRIVATE,
    auditEnabled: true,
    userId: 'demo-user',
  });

  try {
    // ========================================
    // 1. Create Nodes
    // ========================================
    console.log('📌 Creating nodes...');

    const projectNode = await graph.createNode({
      id: 'project-alpha',
      type: 'project',
      properties: {
        name: 'Project Alpha',
        status: 'active',
        priority: 9,
        deadline: new Date('2024-12-31'),
        budget: 50000,
      },
      tags: ['work', 'priority', 'Q4'],
    });
    console.log(`   ✓ Created project: ${projectNode.id}`);

    const taskNode = await graph.createNode({
      id: 'task-design-system',
      type: 'task',
      properties: {
        title: 'Design System Implementation',
        description: 'Build a comprehensive design system for Project Alpha',
        status: 'in-progress',
        priority: 8,
        estimatedHours: 40,
      },
      tags: ['design', 'development', 'work'],
    });
    console.log(`   ✓ Created task: ${taskNode.id}`);

    const ideaNode = await graph.createNode({
      id: 'idea-ai-assistant',
      type: 'idea',
      properties: {
        title: 'AI-Powered Task Assistant',
        description: 'Smart assistant that helps prioritize and schedule tasks',
        confidence: 7,
        feasibility: 8,
      },
      tags: ['innovation', 'ai', 'product'],
    });
    console.log(`   ✓ Created idea: ${ideaNode.id}`);

    const personNode = await graph.createNode({
      id: 'person-sarah-chen',
      type: 'person',
      properties: {
        name: 'Sarah Chen',
        email: 'sarah@example.com',
        role: 'Product Manager',
        skills: ['product-management', 'agile', 'strategy'],
      },
      tags: ['team', 'stakeholder'],
    });
    console.log(`   ✓ Created person: ${personNode.id}`);

    // ========================================
    // 2. Create Relationships (Edges)
    // ========================================
    console.log('\n🔗 Creating relationships...');

    const taskDependsOnIdea = await graph.createEdge({
      from: 'task-design-system',
      to: 'idea-ai-assistant',
      type: 'depends_on',
      properties: { criticality: 'high' },
    });
    console.log(`   ✓ Edge: task → depends_on → idea`);

    const personCreatedTask = await graph.createEdge({
      from: 'person-sarah-chen',
      to: 'task-design-system',
      type: 'created_by',
    });
    console.log(`   ✓ Edge: person → created_by → task`);

    const ideaRelatedToProject = await graph.createEdge({
      from: 'idea-ai-assistant',
      to: 'project-alpha',
      type: 'related_to',
      properties: { strength: 0.9, context: 'Core feature for Project Alpha' },
    });
    console.log(`   ✓ Edge: idea → related_to → project`);

    // ========================================
    // 3. Query Nodes
    // ========================================
    console.log('\n🔍 Querying nodes...');

    // Query by type
    const allTasks = await graph.query({
      match: { labels: ['task'] },
    });
    console.log(`   Found ${allTasks.nodes.length} task(s)`);

    // Query by tag
    const workItems = await graph.query({
      match: { tags: ['work'] },
    });
    console.log(`   Found ${workItems.nodes.length} item(s) tagged 'work'`);

    // Query with ordering
    const highPriorityTasks = await graph.query({
      match: { labels: ['task'] },
      where: { status: 'in-progress' },
      orderBy: { field: 'priority', direction: 'desc' },
    });
    console.log(`   Found ${highPriorityTasks.nodes.length} in-progress task(s), ordered by priority`);

    // ========================================
    // 4. Parse Wiki-Links
    // ========================================
    console.log('\n📝 Parsing wiki-links...');

    const wikiContent = `
      The [[project-alpha]] is making great progress on the [[task-design-system]].
      
      Sarah Chen mentioned in [[meeting-stakeholder-update]] that the timeline looks good.
      
      Key priorities: #urgent #work #Q4
      
      Related ideas: [[idea-ai-assistant]] provides additional value.
    `;

    const parseResult = await graph.parseAndCreate(wikiContent, {
      autoCreateNodes: true,
      autoCreateEdges: true,
    });

    console.log(`   ✓ Parsed ${parseResult.links.length} wiki-links`);
    console.log(`   ✓ Created ${parseResult.createdNodes.length} new nodes`);
    console.log(`   ✓ Created ${parseResult.createdEdges.length} new edges`);

    // ========================================
    // 5. Update Node Properties
    // ========================================
    console.log('\n✏️ Updating nodes...');

    const updatedTask = await graph.updateNode('task-design-system', {
      properties: {
        status: 'completed',
        completedAt: new Date(),
        actualHours: 38,
      },
      tags: ['design', 'development', 'work', 'done'],
    });
    console.log(`   ✓ Updated task status to: ${updatedTask.properties.status}`);

    // ========================================
    // 6. Access Control Demo
    // ========================================
    console.log('\n🔐 Access control demo...');

    // Create a restricted node
    await graph.createNode({
      id: 'confidential-strategy',
      type: 'note',
      properties: {
        title: 'Confidential Strategy Notes',
        content: 'Secret roadmap information...',
      },
      tags: ['confidential'],
      accessLevel: AccessLevel.RESTRICTED,
    });

    // Grant access to specific user
    await graph.grantAccess('confidential-strategy', 'user-sarah');
    console.log('   ✓ Granted access to user-sarah');

    // Revoke access
    await graph.revokeAccess('confidential-strategy', 'user-sarah');
    console.log('   ✓ Revoked access from user-sarah');

    // ========================================
    // 7. Statistics
    // ========================================
    console.log('\n📊 Graph statistics...');

    const stats = await graph.getStats();
    console.log(`   Total nodes: ${stats.totalNodes}`);
    console.log(`   Total edges: ${stats.totalEdges}`);
    console.log(`   Nodes by type:`, stats.nodesByType);
    console.log(`   Tags distribution:`, stats.tagsDistribution);

    // ========================================
    // 8. Export and Backup
    // ========================================
    console.log('\n💾 Exporting data...');

    const backupPath = await graph.backup();
    console.log(`   ✓ Backup created at: ${backupPath}`);

    const exportedData = await graph.exportJSON();
    console.log(`   ✓ Exported ${JSON.stringify(exportedData).length} bytes of JSON`);

    console.log('\n✅ Demo completed successfully!');
  } catch (error) {
    console.error('❌ Error:', error);
    throw error;
  } finally {
    await graph.shutdown();
  }
}

// Run the demo
main().catch(console.error);
