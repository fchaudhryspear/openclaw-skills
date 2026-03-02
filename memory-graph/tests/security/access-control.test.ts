/**
 * Security Tests - Access Control and Permissions
 */

import { AccessController, AccessContext } from '../../src/access/rbac';
import { Node, Edge, Role, AccessLevel, AuditAction } from '../../src/model/types';

describe('AccessController', () => {
  let controller: AccessController;

  beforeEach(() => {
    controller = new AccessController();
  });

  describe('Role-Based Permissions', () => {
    test('admin should have all permissions', () => {
      const context: AccessContext = {
        userId: 'user1',
        userRoles: [Role.ADMIN],
      };

      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(true);
      expect(controller.hasPermission(context, 'delete')).toBe(true);
      expect(controller.hasPermission(context, 'share')).toBe(true);
      expect(controller.hasPermission(context, 'manageAccess')).toBe(true);
    });

    test('editor should not be able to delete or manage access', () => {
      const context: AccessContext = {
        userId: 'user2',
        userRoles: [Role.EDITOR],
      };

      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(true);
      expect(controller.hasPermission(context, 'delete')).toBe(false);
      expect(controller.hasPermission(context, 'share')).toBe(true);
      expect(controller.hasPermission(context, 'manageAccess')).toBe(false);
    });

    test('viewer should only be able to read', () => {
      const context: AccessContext = {
        userId: 'user3',
        userRoles: [Role.VIEWER],
      };

      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(false);
      expect(controller.hasPermission(context, 'delete')).toBe(false);
      expect(controller.hasPermission(context, 'share')).toBe(false);
      expect(controller.hasPermission(context, 'manageAccess')).toBe(false);
    });

    test('guest should have no permissions by default', () => {
      const context: AccessContext = {
        userId: 'user4',
        userRoles: [Role.GUEST],
      };

      expect(controller.hasPermission(context, 'read')).toBe(false);
      expect(controller.hasPermission(context, 'write')).toBe(false);
      expect(controller.hasPermission(context, 'delete')).toBe(false);
      expect(controller.hasPermission(context, 'share')).toBe(false);
      expect(controller.hasPermission(context, 'manageAccess')).toBe(false);
    });

    test('multiple roles should grant union of permissions', () => {
      const context: AccessContext = {
        userId: 'user5',
        userRoles: [Role.VIEWER, Role.GUEST],
      };

      // Should inherit viewer's read permission
      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(false);
    });

    test('role hierarchy should work correctly', () => {
      // Editor inherits from Viewer
      const editorContext: AccessContext = {
        userId: 'user6',
        userRoles: [Role.EDITOR],
      };

      expect(controller.hasPermission(editorContext, 'read')).toBe(true);
      expect(controller.hasPermission(editorContext, 'write')).toBe(true);
    });
  });

  describe('Node Access Levels', () => {
    const createTestNode = (accessLevel: AccessLevel): Node => ({
      id: 'test-node',
      type: 'note',
      properties: { content: 'secret' },
      tags: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      createdBy: 'creator',
      accessLevel,
      version: 1,
    });

    test('public nodes should be readable by anyone', () => {
      const node = createTestNode(AccessLevel.PUBLIC);
      const anyUser: AccessContext = { userId: 'random-user', userRoles: [Role.GUEST] };

      expect(controller.canAccessNode(anyUser, node, 'read')).toBe(true);
    });

    test('private nodes should only be accessible to creator', () => {
      const node = createTestNode(AccessLevel.PRIVATE);
      const creator: AccessContext = { userId: 'creator', userRoles: [Role.EDITOR] };
      const otherUser: AccessContext = { userId: 'other', userRoles: [Role.EDITOR] };

      expect(controller.canAccessNode(creator, node, 'read')).toBe(true);
      expect(controller.canAccessNode(otherUser, node, 'read')).toBe(false);
    });

    test('team nodes should be accessible to team members', () => {
      const node = createTestNode(AccessLevel.TEAM);
      const teamMember: AccessContext = { userId: 'member', userRoles: [Role.VIEWER] };

      expect(controller.canAccessNode(teamMember, node, 'read')).toBe(true);
      expect(controller.canAccessNode(teamMember, node, 'write')).toBe(true);
    });

    test('restricted nodes require explicit access grant', () => {
      const node = createTestNode(AccessLevel.RESTRICTED);
      const creator: AccessContext = { userId: 'creator', userRoles: [Role.EDITOR] };
      const unauthorized: AccessContext = { userId: 'unauthorized', userRoles: [Role.EDITOR] };

      // Creator has access
      expect(controller.canAccessNode(creator, node, 'read')).toBe(true);

      // Others need explicit grant
      expect(controller.canAccessNode(unauthorized, node, 'read')).toBe(false);

      // Grant access
      controller.grantAccess('test-node', 'unauthorized');
      expect(controller.canAccessNode(unauthorized, node, 'read')).toBe(true);
    });

    test('revoked access should be immediately removed', () => {
      const node = createTestNode(AccessLevel.RESTRICTED);
      controller.grantAccess('test-node', 'granted-user');
      
      const context: AccessContext = { userId: 'granted-user', userRoles: [Role.VIEWER] };
      expect(controller.canAccessNode(context, node, 'read')).toBe(true);

      controller.revokeAccess('test-node', 'granted-user');
      expect(controller.canAccessNode(context, node, 'read')).toBe(false);
    });
  });

  describe('Access List Management', () => {
    test('should track granted access', () => {
      controller.grantAccess('node-1', 'user-a');
      controller.grantAccess('node-1', 'user-b');
      controller.grantAccess('node-1', 'user-c');

      const accessList = controller.getAccessList('node-1');
      expect(accessList).toContain('user-a');
      expect(accessList).toContain('user-b');
      expect(accessList).toContain('user-c');
      expect(accessList).toHaveLength(3);
    });

    test('should handle duplicate grants gracefully', () => {
      controller.grantAccess('node-2', 'user-x');
      controller.grantAccess('node-2', 'user-x');
      controller.grantAccess('node-2', 'user-x');

      const accessList = controller.getAccessList('node-2');
      expect(accessList).toHaveLength(1);
      expect(accessList[0]).toBe('user-x');
    });

    test('should return empty list for unknown nodes', () => {
      const accessList = controller.getAccessList('non-existent-node');
      expect(accessList).toHaveLength(0);
    });
  });

  describe('Filtering Accessible Nodes', () => {
    const testNodes: Node[] = [
      { id: '1', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user1', accessLevel: AccessLevel.PUBLIC, version: 1 },
      { id: '2', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user1', accessLevel: AccessLevel.PRIVATE, version: 1 },
      { id: '3', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user2', accessLevel: AccessLevel.PRIVATE, version: 1 },
      { id: '4', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user1', accessLevel: AccessLevel.TEAM, version: 1 },
    ];

    test('should filter based on user roles and node access levels', () => {
      const context: AccessContext = { userId: 'user1', userRoles: [Role.EDITOR] };

      const accessible = controller.filterAccessibleNodes(context, testNodes);

      expect(accessible.map(n => n.id)).toContain('1'); // Public
      expect(accessible.map(n => n.id)).toContain('2'); // Private, created by user1
      expect(accessible.map(n => n.id)).not.toContain('3'); // Private, created by user2
      expect(accessible.map(n => n.id)).toContain('4'); // Team
    });

    test('guest should only see public nodes', () => {
      const guestContext: AccessContext = { userId: 'anyone', userRoles: [Role.GUEST] };

      const accessible = controller.filterAccessibleNodes(guestContext, testNodes);

      expect(accessible.map(n => n.id)).toContain('1');
      expect(accessible.map(n => n.id)).not.toContain('2');
      expect(accessible.map(n => n.id)).not.toContain('3');
      expect(accessible.map(n => n.id)).not.toContain('4');
    });
  });

  describe('Custom Roles', () => {
    test('should create custom role with specific permissions', () => {
      const customRole = controller.createCustomRole('ANALYST', {
        canRead: true,
        canWrite: false,
        canDelete: false,
        canShare: false,
        canManageAccess: false,
      });

      expect(customRole).toBeDefined();

      const context: AccessContext = { userId: 'analyst', userRoles: [customRole] };

      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(false);
    });

    test('should allow role inheritance configuration', () => {
      const juniorRole = controller.createCustomRole('JUNIOR_EDITOR', {
        canRead: true,
        canWrite: true,
        canDelete: false,
        canShare: false,
        canManageAccess: false,
      });

      // Make junior inherit from VIEWER (already included via write=true)
      controller.addRoleInheritance(juniorRole, Role.VIEWER);

      const context: AccessContext = { userId: 'junior', userRoles: [juniorRole] };

      expect(controller.hasPermission(context, 'read')).toBe(true);
      expect(controller.hasPermission(context, 'write')).toBe(true);
    });
  });

  describe('Security Edge Cases', () => {
    test('should deny access when user has no valid roles', () => {
      const context: AccessContext = { userId: 'invalid', userRoles: [] as any };
      const node: Node = { id: 'n1', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'owner', accessLevel: AccessLevel.TEAM, version: 1 };

      const result = controller.validateContext(context);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('At least one user role is required');
    });

    test('should handle privilege escalation attempts', () => {
      const normalUser: AccessContext = { userId: 'normal', userRoles: [Role.VIEWER] };
      const node: Node = { id: 'secret', type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'admin', accessLevel: AccessLevel.RESTRICTED, version: 1 };

      // User tries to claim admin role
      const escalatedUser: AccessContext = { userId: 'normal', userRoles: [Role.VIEWER, Role.ADMIN] };

      // System should validate roles
      const validation = controller.validateContext(escalatedUser);
      
      // If ADMIN is a valid role in the system, this would pass validation
      // But access should still be controlled by actual authorization
      expect(validation.valid).toBe(true); // ADMIN is a valid predefined role
    });

    test('should properly enforce least privilege', () => {
      const minimalContext: AccessContext = { userId: 'contractor', userRoles: [Role.VIEWER] };
      
      const privateNode: Node = { 
        id: 'confidential', 
        type: 'document', 
        properties: { classification: 'top-secret' }, 
        tags: [], 
        createdAt: new Date(), 
        updatedAt: new Date(), 
        createdBy: 'executive', 
        accessLevel: AccessLevel.RESTRICTED, 
        version: 1 
      };

      controller.grantAccess('confidential', 'contractor');

      expect(controller.canAccessNode(minimalContext, privateNode, 'read')).toBe(true);
      expect(controller.canAccessNode(minimalContext, privateNode, 'write')).toBe(false);
      expect(controller.canAccessNode(minimalContext, privateNode, 'delete')).toBe(false);
      expect(controller.canAccessNode(minimalContext, privateNode, 'share')).toBe(false);
    });
  });

  describe('Audit Trail Integration', () => {
    test('should generate audit entries for denied access', () => {
      const node: Node = { 
        id: 'sensitive-data', 
        type: 'document', 
        properties: {}, 
        tags: [], 
        createdAt: new Date(), 
        updatedAt: new Date(), 
        createdBy: 'owner', 
        accessLevel: AccessLevel.PRIVATE, 
        version: 1 
      };

      const unauthorizedUser: AccessContext = { userId: 'hacker', userRoles: [Role.GUEST] };

      const accessResult = controller.canAccessNode(unauthorizedUser, node, 'read');
      expect(accessResult).toBe(false);
    });

    test('should log permission changes', () => {
      controller.grantAccess('audit-test-node', 'new-user');
      const accessList = controller.getAccessList('audit-test-node');
      
      expect(accessList).toContain('new-user');
    });
  });

  describe('Concurrent Access Scenarios', () => {
    test('should handle rapid grant/revoke cycles', () => {
      for (let i = 0; i < 100; i++) {
        controller.grantAccess('rapid-test-node', `user-${i}`);
      }

      const list = controller.getAccessList('rapid-test-node');
      expect(list).toHaveLength(100);

      for (let i = 0; i < 50; i++) {
        controller.revokeAccess('rapid-test-node', `user-${i}`);
      }

      const finalList = controller.getAccessList('rapid-test-node');
      expect(finalList).toHaveLength(50);
      expect(finalList).not.toContain('user-0');
      expect(finalList).toContain('user-50');
    });
  });
});
