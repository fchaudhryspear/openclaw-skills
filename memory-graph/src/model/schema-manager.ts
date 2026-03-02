/**
 * Schema Manager - Defines and validates node/edge schemas
 */

import { NodeType, NodeSchema, PropertyType, EdgeType, PropertyDefinition } from './types';

export class SchemaManager {
  private nodeSchemas: Map<NodeType, NodeSchema>;
  private edgeSchemas: Map<EdgeType, NodeSchema>;
  private tagHierarchy: Map<string, string[]>;

  constructor() {
    this.nodeSchemas = new Map();
    this.edgeSchemas = new Map();
    this.tagHierarchy = new Map();
    this.initializeDefaultSchemas();
  }

  private initializeDefaultSchemas(): void {
    // Default node schemas
    this.nodeSchemas.set('person', {
      required: ['name'],
      properties: {
        name: { type: PropertyType.STRING, required: true },
        email: { type: PropertyType.STRING },
        role: { type: PropertyType.STRING },
        skills: { type: PropertyType.ARRAY },
        createdAt: { type: PropertyType.DATE },
      },
    });

    this.nodeSchemas.set('project', {
      required: ['name', 'status'],
      properties: {
        name: { type: PropertyType.STRING, required: true },
        status: { type: PropertyType.STRING, required: true },
        priority: { type: PropertyType.NUMBER },
        deadline: { type: PropertyType.DATE },
        budget: { type: PropertyType.NUMBER },
        team: { type: PropertyType.ARRAY },
      },
    });

    this.nodeSchemas.set('task', {
      required: ['title', 'status'],
      properties: {
        title: { type: PropertyType.STRING, required: true },
        description: { type: PropertyType.STRING },
        status: { type: PropertyType.STRING, required: true },
        priority: { type: PropertyType.NUMBER },
        dueDate: { type: PropertyType.DATE },
        estimatedHours: { type: PropertyType.NUMBER },
        completedAt: { type: PropertyType.DATE },
      },
    });

    this.nodeSchemas.set('meeting', {
      required: ['title', 'startTime'],
      properties: {
        title: { type: PropertyType.STRING, required: true },
        startTime: { type: PropertyType.DATE, required: true },
        endTime: { type: PropertyType.DATE },
        attendees: { type: PropertyType.ARRAY },
        location: { type: PropertyType.STRING },
        notes: { type: PropertyType.STRING },
      },
    });

    this.nodeSchemas.set('document', {
      required: ['title', 'type'],
      properties: {
        title: { type: PropertyType.STRING, required: true },
        type: { type: PropertyType.STRING, required: true },
        content: { type: PropertyType.STRING },
        url: { type: PropertyType.STRING },
        author: { type: PropertyType.STRING },
        version: { type: PropertyType.STRING },
      },
    });

    this.nodeSchemas.set('idea', {
      required: ['title'],
      properties: {
        title: { type: PropertyType.STRING, required: true },
        description: { type: PropertyType.STRING },
        confidence: { type: PropertyType.NUMBER },
        feasibility: { type: PropertyType.NUMBER },
        source: { type: PropertyType.STRING },
      },
    });

    this.nodeSchemas.set('note', {
      required: ['content'],
      properties: {
        content: { type: PropertyType.STRING, required: true },
        title: { type: PropertyType.STRING },
        category: { type: PropertyType.STRING },
        importance: { type: PropertyType.NUMBER },
      },
    });

    this.nodeSchemas.set('resource', {
      required: ['name', 'url'],
      properties: {
        name: { type: PropertyType.STRING, required: true },
        url: { type: PropertyType.STRING, required: true },
        type: { type: PropertyType.STRING },
        rating: { type: PropertyType.NUMBER },
        lastAccessed: { type: PropertyType.DATE },
      },
    });

    this.nodeSchemas.set('concept', {
      required: ['name'],
      properties: {
        name: { type: PropertyType.STRING, required: true },
        definition: { type: PropertyType.STRING },
        examples: { type: PropertyType.ARRAY },
        relatedTerms: { type: PropertyType.ARRAY },
      },
    });

    // Default edge schemas
    this.edgeSchemas.set('related_to', {
      required: [],
      properties: {
        strength: { type: PropertyType.NUMBER },
        context: { type: PropertyType.STRING },
      },
    });

    this.edgeSchemas.set('part_of', {
      required: [],
      properties: {
        hierarchy: { type: PropertyType.NUMBER },
      },
    });

    this.edgeSchemas.set('depends_on', {
      required: [],
      properties: {
        criticality: { type: PropertyType.STRING },
      },
    });

    this.edgeSchemas.set('created_by', {
      required: [],
      properties: {},
    });

    this.edgeSchemas.set('references', {
      required: [],
      properties: {
        citation: { type: PropertyType.STRING },
        page: { type: PropertyType.NUMBER },
      },
    });

    this.edgeSchemas.set('tags', {
      required: [],
      properties: {},
    });

    this.edgeSchemas.set('similar_to', {
      required: [],
      properties: {
        similarity: { type: PropertyType.NUMBER },
        algorithm: { type: PropertyType.STRING },
      },
    });

    this.edgeSchemas.set('contradicts', {
      required: [],
      properties: {
        explanation: { type: PropertyType.STRING },
      },
    });

    this.edgeSchemas.set('updates', {
      required: [],
      properties: {
        changeSummary: { type: PropertyType.STRING },
      },
    });
  }

  validateNode(type: NodeType, properties: Record<string, unknown>): { valid: boolean; errors: string[] } {
    const schema = this.nodeSchemas.get(type);
    if (!schema) {
      return { valid: false, errors: [`Unknown node type: ${type}`] };
    }

    const errors: string[] = [];

    // Check required properties
    for (const required of schema.required) {
      if (!(required in properties)) {
        errors.push(`Missing required property: ${required}`);
      }
    }

    // Validate property types
    for (const [key, value] of Object.entries(properties)) {
      const propDef = schema.properties[key];
      if (propDef) {
        if (!this.validatePropertyType(value, propDef.type)) {
          errors.push(`Invalid type for property '${key}': expected ${propDef.type}, got ${typeof value}`);
        }
        if (propDef.validator && !propDef.validator(value)) {
          errors.push(`Validation failed for property '${key}'`);
        }
      }
    }

    return { valid: errors.length === 0, errors };
  }

  validateEdge(type: EdgeType, properties: Record<string, unknown>): { valid: boolean; errors: string[] } {
    const schema = this.edgeSchemas.get(type);
    if (!schema) {
      return { valid: false, errors: [`Unknown edge type: ${type}`] };
    }

    const errors: string[] = [];

    for (const required of schema.required) {
      if (!(required in properties)) {
        errors.push(`Missing required property: ${required}`);
      }
    }

    for (const [key, value] of Object.entries(properties)) {
      const propDef = schema.properties[key];
      if (propDef && !this.validatePropertyType(value, propDef.type)) {
        errors.push(`Invalid type for property '${key}': expected ${propDef.type}, got ${typeof value}`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  private validatePropertyType(value: unknown, expectedType: PropertyType): boolean {
    if (value === undefined || value === null) return true;

    switch (expectedType) {
      case PropertyType.STRING:
        return typeof value === 'string';
      case PropertyType.NUMBER:
        return typeof value === 'number';
      case PropertyType.BOOLEAN:
        return typeof value === 'boolean';
      case PropertyType.DATE:
        return value instanceof Date;
      case PropertyType.ARRAY:
        return Array.isArray(value);
      case PropertyType.OBJECT:
        return typeof value === 'object' && !Array.isArray(value);
      default:
        return true;
    }
  }

  registerNodeType(type: NodeType, schema: NodeSchema): void {
    this.nodeSchemas.set(type, schema);
  }

  registerEdgeType(type: EdgeType, schema: NodeSchema): void {
    this.edgeSchemas.set(type, schema);
  }

  getNodeSchema(type: NodeType): NodeSchema | undefined {
    return this.nodeSchemas.get(type);
  }

  getEdgeSchema(type: EdgeType): NodeSchema | undefined {
    return this.edgeSchemas.get(type);
  }

  getAllNodeTypes(): NodeType[] {
    return Array.from(this.nodeSchemas.keys());
  }

  getAllEdgeTypes(): EdgeType[] {
    return Array.from(this.edgeSchemas.keys());
  }

  addTagToHierarchy(tag: string, parent?: string): void {
    if (parent) {
      const siblings = this.tagHierarchy.get(parent) || [];
      if (!siblings.includes(tag)) {
        siblings.push(tag);
        this.tagHierarchy.set(parent, siblings);
      }
    } else {
      if (!this.tagHierarchy.has(tag)) {
        this.tagHierarchy.set(tag, []);
      }
    }
  }

  getTagChildren(tag: string): string[] {
    return this.tagHierarchy.get(tag) || [];
  }

  hasChildTag(parent: string, child: string): boolean {
    const children = this.getTagChildren(parent);
    return children.includes(child) || children.some(c => this.hasChildTag(c, child));
  }
}

// Export singleton instance
export const schemaManager = new SchemaManager();
