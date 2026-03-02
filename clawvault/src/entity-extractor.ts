/**
 * Entity Extraction Module
 * 
 * Extracts entities from memory content for knowledge graph construction.
 * Types: Person, Organization, Project, Location, Technology, Date/Time.
 */

import { MemoryEntry } from './types';

export type EntityType = 'person' | 'organization' | 'project' | 'location' | 'technology' | 'datetime' | 'money' | 'email' | 'phone';

export interface Entity {
  id: string;
  text: string;           // Original extracted text
  type: EntityType;
  normalized?: string;    // Lowercase, trimmed version
  mentions: number;       // How many times seen
  lastSeen: number;       // Timestamp of most recent mention
  context: string[];      // Snippets where found
  relatedEntities: string[]; // IDs of frequently co-occurring entities
}

export interface ExtractionResult {
  entities: Entity[];
  relationships: Array<{
    source: string;       // Entity ID
    target: string;       // Entity ID
    type: string;         // relationship type
    confidence: number;   // 0-1
    context: string;      // Sentence/phrase showing relationship
  }>;
}

// Entity patterns and dictionaries
const PATTERNS = {
  email: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  phone: /(\+?1?[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}/g,
  
  companySuffixes: ['inc', 'llc', 'corp', 'corporation', 'limited', 'ltd', 'co', 'company', 'partners', 'holdings'],
  
  projectPrefixes: ['project', 'initiative', 'program', 'campaign', 'task'],
  
  technologyKeywords: [
    'react', 'angular', 'vue', 'nodejs', 'python', 'javascript', 'typescript',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
    'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'linux', 'windows', 'macos', 'ios', 'android',
    'graphql', 'rest', 'grpc', 'kafka', 'rabbitmq',
    'git', 'github', 'gitlab', 'jenkins', 'circleci',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas',
    'excel', 'tableau', 'powerbi', 'looker',
    'salesforce', 'hubspot', 'stripe', 'twilio', 'sendgrid'
  ],
  
  personTitles: ['mr', 'mrs', 'ms', 'dr', 'prof', 'engineer', 'manager', 'director', 'vp', 'cto', 'cfo', 'ceo'],
  
  locations: [
    'dallas', 'texas', 'new york', 'san francisco', 'seattle', 'chicago', 'boston',
    'london', 'paris', 'berlin', 'tokyo', 'singapore', 'sydney',
    'europe', 'asia', 'america', 'africa', 'north america', 'south america',
    'california', 'washington', 'new york state', 'florida'
  ]
};

export interface EntityExtractorConfig {
  enableExtraction: boolean;
  minLength: number;              // Minimum entity length
  maxMentionsToTrack: number;     // Keep top N contexts per entity
  confidenceThreshold: number;    // Minimum confidence for automatic extraction
}

export class EntityExtractor {
  private config: EntityExtractorConfig;
  private entityIndex: Map<string, Entity>;       // normalized text -> Entity
  private entityTypeIndex: Map<EntityType, Set<string>>; // type -> set of entity IDs
  private coOccurrenceMap: Map<string, Map<string, number>>; // entity -> { neighbor -> count }

  constructor(config?: Partial<EntityExtractorConfig>) {
    this.config = {
      enableExtraction: true,
      minLength: 2,
      maxMentionsToTrack: 5,
      confidenceThreshold: 0.7,
      ...config
    };

    this.entityIndex = new Map();
    this.entityTypeIndex = new Map();
    this.coOccurrenceMap = new Map();
    
    // Initialize type indexes
    const types: EntityType[] = ['person', 'organization', 'project', 'location', 'technology', 'datetime', 'money', 'email', 'phone'];
    for (const type of types) {
      this.entityTypeIndex.set(type, new Set());
    }
  }

  /**
   * Extract entities from text
   */
  extract(text: string, context?: MemoryEntry): ExtractionResult {
    if (!this.config.enableExtraction || !text || text.length < this.config.minLength) {
      return { entities: [], relationships: [] };
    }

    const entities: Entity[] = [];
    const relData: Array<{
      source: string;
      target: string;
      type: string;
      confidence: number;
      context: string;
    }> = [];
    const lower = text.toLowerCase();

    // Extract by pattern/type
    const emails = this.extractEmails(text);
    const phones = this.extractPhones(text);
    const organizations = this.extractOrganizations(lower, text);
    const projects = this.extractProjects(lower, text);
    const technologies = this.extractTechnologies(lower);
    const locations = this.extractLocations(lower);
    const persons = this.extractPersons(lower, text);
    const money = this.extractMoney(text);

    // Combine all entities
    entities.push(...emails, ...phones, ...organizations, ...projects, ...technologies, ...locations, ...persons, ...money);

    // Update entity index
    for (const entity of entities) {
      this.updateEntity(entity, text);
    }

    // Extract relationships based on proximity
    const extractedRelationships = this.extractRelationships(entities, text);
    relData.push(...extractedRelationships);

    return { entities, relationships: relData };
  }

  /**
   * Process a memory entry and extract entities
   */
  processMemory(memory: MemoryEntry): ExtractionResult {
    const result = this.extract(memory.content, memory);
    
    // Associate entities with memory
    for (const entity of result.entities) {
      if (!entity.context.includes(memory.content.substring(0, 100))) {
        const ctx = memory.content.substring(0, 200);
        entity.context.push(ctx);
        if (entity.context.length > this.config.maxMentionsToTrack) {
          entity.context.shift();
        }
      }
    }

    return result;
  }

  /**
   * Update entity in index
   */
  private updateEntity(entity: Entity, context: string): void {
    const normalized = entity.normalized || entity.text.toLowerCase().trim();
    
    if (this.entityIndex.has(normalized)) {
      const existing = this.entityIndex.get(normalized)!;
      existing.mentions++;
      existing.lastSeen = Date.now();
      
      if (!existing.context.includes(context.substring(0, 200))) {
        existing.context.push(context.substring(0, 200));
        if (existing.context.length > this.config.maxMentionsToTrack) {
          existing.context.shift();
        }
      }
    } else {
      entity.id = `${entity.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      entity.mentions = 1;
      entity.lastSeen = Date.now();
      this.entityIndex.set(normalized, entity);
      this.entityTypeIndex.get(entity.type)?.add(entity.id);
    }
  }

  /**
   * Track co-occurrence between entities
   */
  trackCoOccurrence(entityId1: string, entityId2: string): void {
    if (!this.coOccurrenceMap.has(entityId1)) {
      this.coOccurrenceMap.set(entityId1, new Map());
    }
    if (!this.coOccurrenceMap.has(entityId2)) {
      this.coOccurrenceMap.set(entityId2, new Map());
    }
    
    const map1 = this.coOccurrenceMap.get(entityId1)!;
    const map2 = this.coOccurrenceMap.get(entityId2)!;
    
    map1.set(entityId2, (map1.get(entityId2) || 0) + 1);
    map2.set(entityId1, (map2.get(entityId1) || 0) + 1);
  }

  /**
   * Get entity by ID
   */
  getEntity(id: string): Entity | undefined {
    for (const entity of this.entityIndex.values()) {
      if (entity.id === id) return entity;
    }
    return undefined;
  }

  /**
   * Get entities by type
   */
  getByType(type: EntityType): Entity[] {
    const ids = this.entityTypeIndex.get(type) || new Set();
    const entities: Entity[] = [];
    
    for (const id of ids) {
      for (const entity of this.entityIndex.values()) {
        if (entity.id === id) {
          entities.push(entity);
          break;
        }
      }
    }
    
    return entities;
  }

  /**
   * Get entities by search query
   */
  search(query: string): Entity[] {
    const lower = query.toLowerCase();
    const results: Entity[] = [];
    
    for (const entity of this.entityIndex.values()) {
      if (entity.text.toLowerCase().includes(lower) ||
          entity.normalized?.includes(lower) ||
          entity.type.includes(lower as any)) {
        results.push(entity);
      }
    }
    
    return results.sort((a, b) => b.mentions - a.mentions);
  }

  /**
   * Get most mentioned entities
   */
  getTopEntities(limit: number = 20): Entity[] {
    return Array.from(this.entityIndex.values())
      .sort((a, b) => b.mentions - a.mentions)
      .slice(0, limit);
  }

  /**
   * Get related entities for an entity
   */
  getRelatedEntities(entityId: string, limit: number = 5): Array<{ entity: Entity; coOccurrence: number }> {
    const coOccurrences = this.coOccurrenceMap.get(entityId);
    if (!coOccurrences) return [];

    const related: Array<{ entity: Entity; coOccurrence: number }> = [];
    
    for (const [otherId, count] of coOccurrences.entries()) {
      const otherEntity = this.getEntity(otherId);
      if (otherEntity) {
        related.push({ entity: otherEntity, coOccurrence: count });
      }
    }
    
    return related.sort((a, b) => b.coOccurrence - a.coOccurrence).slice(0, limit);
  }

  // --- Specific extractors ---

  private extractEmails(text: string): Entity[] {
    const matches = text.match(PATTERNS.email) || [];
    return matches.map(email => ({
      id: `email-${email}`,
      text: email,
      type: 'email' as EntityType,
      normalized: email.toLowerCase(),
      mentions: 0,
      lastSeen: Date.now(),
      context: [],
      relatedEntities: []
    }));
  }

  private extractPhones(text: string): Entity[] {
    const matches = text.match(PATTERNS.phone) || [];
    return matches.map(phone => ({
      id: `phone-${phone.replace(/\D/g, '')}`,
      text: phone.trim(),
      type: 'phone' as EntityType,
      mentions: 0,
      lastSeen: Date.now(),
      context: [],
      relatedEntities: []
    }));
  }

  private extractOrganizations(lower: string, text: string): Entity[] {
    const organizations: Entity[] = [];
    const words = lower.split(/\s+/);
    
    for (let i = 0; i < words.length; i++) {
      // Look for company patterns: Word Inc, Word LLC, etc.
      if (i + 1 < words.length && PATTERNS.companySuffixes.includes(words[i + 1])) {
        const orgName = words.slice(Math.max(0, i - 1), i + 2).join(' ').trim();
        if (orgName.length > 2) {
          organizations.push({
            id: `org-${orgName}`,
            text: orgName,
            type: 'organization',
            normalized: orgName,
            mentions: 0,
            lastSeen: Date.now(),
            context: [],
            relatedEntities: []
          });
        }
      }
    }
    
    return organizations;
  }

  private extractProjects(lower: string, text: string): Entity[] {
    const projects: Entity[] = [];
    
    for (const prefix of PATTERNS.projectPrefixes) {
      const regex = new RegExp(`${prefix}\\s+([a-z0-9-]+)`, 'gi');
      const matches = text.matchAll(regex);
      
      for (const match of matches) {
        const projectName = match[0];
        projects.push({
          id: `project-${projectName.toLowerCase()}`,
          text: projectName,
          type: 'project',
          normalized: projectName.toLowerCase(),
          mentions: 0,
          lastSeen: Date.now(),
          context: [],
          relatedEntities: []
        });
      }
    }
    
    return projects;
  }

  private extractTechnologies(lower: string): Entity[] {
    const technologies: Entity[] = [];
    
    for (const tech of PATTERNS.technologyKeywords) {
      if (lower.includes(tech)) {
        technologies.push({
          id: `tech-${tech}`,
          text: tech,
          type: 'technology',
          normalized: tech,
          mentions: 0,
          lastSeen: Date.now(),
          context: [],
          relatedEntities: []
        });
      }
    }
    
    return technologies;
  }

  private extractLocations(lower: string): Entity[] {
    const locations: Entity[] = [];
    
    for (const location of PATTERNS.locations) {
      if (lower.includes(location)) {
        locations.push({
          id: `loc-${location}`,
          text: location,
          type: 'location',
          normalized: location,
          mentions: 0,
          lastSeen: Date.now(),
          context: [],
          relatedEntities: []
        });
      }
    }
    
    return locations;
  }

  private extractPersons(lower: string, text: string): Entity[] {
    const persons: Entity[] = [];
    
    // Simple heuristic: Title followed by name
    for (const title of PATTERNS.personTitles) {
      const regex = new RegExp(`\\b${title}\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)`, 'gi');
      const matches = text.matchAll(regex);
      
      for (const match of matches) {
        const personName = match[0].replace(new RegExp(`^\\b${title}\\s+`, 'i'), '').trim();
        if (personName.length > 1) {
          persons.push({
            id: `person-${personName.toLowerCase().replace(/\s+/g, '-')}`,
            text: personName,
            type: 'person',
            normalized: personName.toLowerCase(),
            mentions: 0,
            lastSeen: Date.now(),
            context: [],
            relatedEntities: []
          });
        }
      }
    }
    
    return persons;
  }

  private extractMoney(text: string): Entity[] {
    const moneyRegex = /\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|usd|money)\b/gi;
    const matches = text.match(moneyRegex) || [];
    
    return matches.map(amount => ({
      id: `money-${amount.replace(/\D/g, '').substring(0, 10)}`,
      text: amount,
      type: 'money',
      mentions: 0,
      lastSeen: Date.now(),
      context: [],
      relatedEntities: []
    }));
  }

  private extractRelationships(entities: Entity[], text: string): Array<{
    source: string;
    target: string;
    type: string;
    confidence: number;
    context: string;
  }> {
    const relResults: Array<{
      source: string;
      target: string;
      type: string;
      confidence: number;
      context: string;
    }> = [];

    // Simple proximity-based relationships
    for (let i = 0; i < entities.length; i++) {
      for (let j = i + 1; j < entities.length; j++) {
        const e1 = entities[i];
        const e2 = entities[j];
        
        // Calculate proximity score (fewer words between = higher confidence)
        const pos1 = text.indexOf(e1.text);
        const pos2 = text.indexOf(e2.text);
        
        if (pos1 !== -1 && pos2 !== -1) {
          const distance = Math.abs(pos2 - pos1);
          const confidence = Math.max(0, 1 - (distance / 200)); // Decay over 200 chars
          
          if (confidence > 0.3 && e1.id !== e2.id) {
            // Determine relationship type
            let relType = 'associated_with';
            if (e1.type === 'person' && e2.type === 'organization') relType = 'works_at';
            else if (e2.type === 'person' && e1.type === 'organization') relType = 'works_at';
            else if (e1.type === 'technology' || e2.type === 'technology') relType = 'uses';
            else if (e1.type === 'project' || e2.type === 'project') relType = 'part_of';
            
            relResults.push({
              source: e1.id,
              target: e2.id,
              type: relType,
              confidence,
              context: text.substring(Math.min(pos1, pos2), Math.min(pos1, pos2) + 100)
            });
            
            // Track co-occurrence
            this.trackCoOccurrence(e1.id, e2.id);
          }
        }
      }
    }

    return relResults;
  }

  /**
   * Get extraction statistics
   */
  getStats(): {
    totalEntities: number;
    byType: Record<EntityType, number>;
    topEntities: Array<{ text: string; mentions: number; type: EntityType }>;
  } {
    const byType: Record<EntityType, number> = {
      person: 0, organization: 0, project: 0, location: 0,
      technology: 0, datetime: 0, money: 0, email: 0, phone: 0
    };

    for (const entity of this.entityIndex.values()) {
      byType[entity.type]++;
    }

    const topEntities = Array.from(this.entityIndex.values())
      .sort((a, b) => b.mentions - a.mentions)
      .slice(0, 10)
      .map(e => ({ text: e.text, mentions: e.mentions, type: e.type }));

    return {
      totalEntities: this.entityIndex.size,
      byType,
      topEntities
    };
  }

  /**
   * Clear all extracted entities
   */
  clear(): void {
    this.entityIndex.clear();
    for (const typeSet of this.entityTypeIndex.values()) {
      typeSet.clear();
    }
    this.coOccurrenceMap.clear();
  }
}
