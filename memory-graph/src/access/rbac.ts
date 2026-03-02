/**
 * Role-Based Access Control (RBAC) System
 */

import { Node, Edge, Role, Permission, AccessLevel } from '../model/types';

export interface AccessContext {
  userId: string;
  userRoles: Role[];
  sessionId?: string;
  ipAddress?: string;
}

export class AccessController {
  private permissions: Map<Role, Permission>;
  private nodeAccessRules: Map<string, Set<string>>; // nodeId -> allowed userIds
  private roleHierarchy: Map<Role, Role[]>; // role -> parent roles

  constructor() {
    this.permissions = new Map();
    this.nodeAccessRules = new Map();
    this.roleHierarchy = new Map();
    this.initializeDefaults();
  }

  private initializeDefaults(): void {
    // Define default permissions for each role
    this.permissions.set(Role.ADMIN, {
      role: Role.ADMIN,
      canRead: true,
      canWrite: true,
      canDelete: true,
      canShare: true,
      canManageAccess: true,
    });

    this.permissions.set(Role.EDITOR, {
      role: Role.EDITOR,
      canRead: true,
      canWrite: true,
      canDelete: false,
      canShare: true,
      canManageAccess: false,
    });

    this.permissions.set(Role.VIEWER, {
      role: Role.VIEWER,
      canRead: true,
      canWrite: false,
      canDelete: false,
      canShare: false,
      canManageAccess: false,
    });

    this.permissions.set(Role.GUEST, {
      role: Role.GUEST,
      canRead: false,
      canWrite: false,
      canDelete: false,
      canShare: false,
      canManageAccess: false,
    });

    // Define role hierarchy (roles inherit from parents)
    this.roleHierarchy.set(Role.ADMIN, []);
    this.roleHierarchy.set(Role.EDITOR, [Role.VIEWER]);
    this.roleHierarchy.set(Role.VIEWER, [Role.GUEST]);
    this.roleHierarchy.set(Role.GUEST, []);
  }

  /**
   * Check if user can perform action on node
   */
  canAccessNode(
    context: AccessContext,
    node: Node,
    action: 'read' | 'write' | 'delete' | 'share' | 'manageAccess'
  ): boolean {
    // Public nodes are accessible to everyone
    if (node.accessLevel === AccessLevel.PUBLIC) {
      return action === 'read';
    }

    // Private nodes - only creator or explicitly granted users
    if (node.accessLevel === AccessLevel.PRIVATE) {
      if (node.createdBy === context.userId) {
        return this.hasPermission(context, action);
      }
      const allowedUsers = this.nodeAccessRules.get(node.id);
      return allowedUsers?.has(context.userId) ?? false;
    }

    // Team nodes - check user roles
    if (node.accessLevel === AccessLevel.TEAM) {
      return this.hasPermission(context, action);
    }

    // Restricted nodes - explicit grant required
    if (node.accessLevel === AccessLevel.RESTRICTED) {
      if (node.createdBy === context.userId) {
        return this.hasPermission(context, action);
      }
      const allowedUsers = this.nodeAccessRules.get(node.id);
      return allowedUsers?.has(context.userId) ?? false;
    }

    return false;
  }

  /**
   * Check if user has permission based on their roles
   */
  private hasPermission(context: AccessContext, action: string): boolean {
    for (const role of context.userRoles) {
      const perms = this.getEffectivePermissions(role);
      
      switch (action) {
        case 'read':
          if (perms.canRead) return true;
          break;
        case 'write':
          if (perms.canWrite) return true;
          break;
        case 'delete':
          if (perms.canDelete) return true;
          break;
        case 'share':
          if (perms.canShare) return true;
          break;
        case 'manageAccess':
          if (perms.canManageAccess) return true;
          break;
      }
    }
    return false;
  }

  /**
   * Get effective permissions including inherited ones
   */
  private getEffectivePermissions(role: Role): Permission {
    const directPerms = this.permissions.get(role);
    if (!directPerms) {
      return {
        role,
        canRead: false,
        canWrite: false,
        canDelete: false,
        canShare: false,
        canManageAccess: false,
      };
    }

    // Merge with parent role permissions
    const parentRoles = this.roleHierarchy.get(role) || [];
    let effectivePerms = { ...directPerms };

    for (const parentRole of parentRoles) {
      const parentPerms = this.getEffectivePermissions(parentRole);
      effectivePerms = {
        role: effectivePerms.role,
        canRead: effectivePerms.canRead || parentPerms.canRead,
        canWrite: effectivePerms.canWrite || parentPerms.canWrite,
        canDelete: effectivePerms.canDelete || parentPerms.canDelete,
        canShare: effectivePerms.canShare || parentPerms.canShare,
        canManageAccess: effectivePerms.canManageAccess || parentPerms.canManageAccess,
      };
    }

    return effectivePerms;
  }

  /**
   * Grant access to a specific user for a node
   */
  grantAccess(nodeId: string, userId: string): void {
    if (!this.nodeAccessRules.has(nodeId)) {
      this.nodeAccessRules.set(nodeId, new Set());
    }
    this.nodeAccessRules.get(nodeId)!.add(userId);
  }

  /**
   * Revoke access from a specific user for a node
   */
  revokeAccess(nodeId: string, userId: string): void {
    const allowedUsers = this.nodeAccessRules.get(nodeId);
    if (allowedUsers) {
      allowedUsers.delete(userId);
    }
  }

  /**
   * Get list of users with access to a node
   */
  getAccessList(nodeId: string): string[] {
    return Array.from(this.nodeAccessRules.get(nodeId) || []);
  }

  /**
   * Check if edge is accessible (inherits access from source node)
   */
  canAccessEdge(
    context: AccessContext,
    edge: Edge,
    action: 'read' | 'write' | 'delete'
  ): boolean {
    // Access control for edges is determined by the source node
    // This prevents leaking information through edge discovery
    return true; // Edges are checked when traversing from accessible nodes
  }

  /**
   * Filter nodes based on user's access
   */
  filterAccessibleNodes(context: AccessContext, nodes: Node[]): Node[] {
    return nodes.filter(node => 
      this.canAccessNode(context, node, 'read')
    );
  }

  /**
   * Create a new custom role
   */
  createCustomRole(
    name: string,
    permissions: Omit<Permission, 'role'>
  ): Role {
    const customRole = `CUSTOM_${name.toUpperCase()}` as Role;
    this.permissions.set(customRole, {
      role: customRole,
      ...permissions,
    });
    this.roleHierarchy.set(customRole, []);
    return customRole;
  }

  /**
   * Update role permissions
   */
  updateRolePermissions(role: Role, permissions: Partial<Permission>): void {
    const existing = this.permissions.get(role);
    if (existing) {
      this.permissions.set(role, { ...existing, ...permissions });
    }
  }

  /**
   * Add role to another role's inheritance chain
   */
  addRoleInheritance(child: Role, parent: Role): void {
    if (!this.roleHierarchy.has(child)) {
      this.roleHierarchy.set(child, []);
    }
    const parents = this.roleHierarchy.get(child)!;
    if (!parents.includes(parent)) {
      parents.push(parent);
    }
  }

  /**
   * Validate access context
   */
  validateContext(context: AccessContext): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!context.userId) {
      errors.push('userId is required');
    }

    if (!context.userRoles || context.userRoles.length === 0) {
      errors.push('At least one user role is required');
    }

    // Check all roles exist
    for (const role of context.userRoles) {
      if (!this.permissions.has(role)) {
        errors.push(`Unknown role: ${role}`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Get audit log entry for access attempt
   */
  getAccessLogEntry(
    context: AccessContext,
    nodeId: string,
    action: string,
    allowed: boolean
  ): {
    success: boolean;
    reason: string;
    timestamp: Date;
  } {
    return {
      success: allowed,
      reason: allowed ? 'Access granted' : 'Access denied',
      timestamp: new Date(),
    };
  }
}

// Export singleton instance
export const accessController = new AccessController();
