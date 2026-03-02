/**
 * Wiki-Links Parser - Extract links, tags, and relationships from text
 */

import { WikiLink, TagDefinition } from '../model/types';

export interface ParseOptions {
  extractWikiLinks: boolean;
  extractTags: boolean;
  extractQueryBlocks: boolean;
  normalizeLinks: boolean;
}

export class WikiParser {
  private defaultOptions: ParseOptions;
  private tagDefinitions: Map<string, TagDefinition>;
  private linkAliases: Map<string, string>;

  constructor(options: Partial<ParseOptions> = {}) {
    this.defaultOptions = {
      extractWikiLinks: true,
      extractTags: true,
      extractQueryBlocks: true,
      normalizeLinks: true,
      ...options,
    };
    
    this.tagDefinitions = new Map();
    this.linkAliases = new Map();
    this.initializeDefaults();
  }

  private initializeDefaults(): void {
    // Initialize common tag definitions
    const commonTags = [
      { name: 'work', parent: undefined, aliases: ['professional', 'job'] },
      { name: 'personal', parent: undefined, aliases: ['private', 'home'] },
      { name: 'idea', parent: undefined, aliases: ['concept', 'thought'] },
      { name: 'task', parent: undefined, aliases: ['todo', 'action'] },
      { name: 'reference', parent: undefined, aliases: ['src', 'source'] },
      { name: 'urgent', parent: undefined, aliases: ['high-priority', 'critical'] },
      { name: 'important', parent: undefined, aliases: ['priority'] },
    ];

    for (const tag of commonTags) {
      this.tagDefinitions.set(tag.name, tag);
      for (const alias of tag.aliases) {
        this.tagDefinitions.set(alias, { ...tag, name: tag.name });
      }
    }
  }

  /**
   * Parse text and extract all wiki-links and tags
   */
  parse(text: string, options: Partial<ParseOptions> = {}): {
    links: WikiLink[];
    tags: string[];
    queries: string[];
    cleanText: string;
  } {
    const opts = { ...this.defaultOptions, ...options };
    const results = {
      links: [] as WikiLink[],
      tags: [] as string[],
      queries: [] as string[],
      cleanText: text,
    };

    if (opts.extractWikiLinks) {
      results.links = this.extractWikiLinks(text);
    }

    if (opts.extractTags) {
      results.tags = this.extractTags(text);
    }

    if (opts.extractQueryBlocks) {
      results.queries = this.extractQueryBlocks(text);
    }

    return results;
  }

  /**
   * Extract wiki-links in format [[page]] or [[page|alias]]
   */
  private extractWikiLinks(text: string): WikiLink[] {
    const links: WikiLink[] = [];
    const wikiLinkRegex = /\[\[(.+?)\]\]/g;
    
    let match;
    while ((match = wikiLinkRegex.exec(text)) !== null) {
      const fullMatch = match[0];
      const content = match[1];
      const startIndex = match.index;
      
      let target: string;
      let type: WikiLink['type'] = 'link';

      // Check for query blocks
      if (content.startsWith('?')) {
        type = 'query';
        target = content.substring(1);
      } 
      // Check for inline tags #tag
      else if (content.startsWith('#')) {
        type = 'tag';
        target = content.substring(1);
      }
      // Standard wiki-link with optional alias [[target|alias]]
      else if (content.includes('|')) {
        const parts = content.split('|');
        target = parts[0].trim();
      } else {
        target = content.trim();
      }

      // Normalize link target
      if (this.defaultOptions.normalizeLinks) {
        target = this.normalizeLink(target);
      }

      // Get context (surrounding text)
      const contextStart = Math.max(0, startIndex - 50);
      const contextEnd = Math.min(text.length, startIndex + fullMatch.length + 50);
      const context = text.substring(contextStart, contextEnd).trim();

      links.push({
        target,
        context,
        position: {
          start: startIndex,
          end: startIndex + fullMatch.length,
        },
        type,
      });
    }

    return links;
  }

  /**
   * Extract hashtag-style tags
   */
  private extractTags(text: string): string[] {
    const tags: string[] = [];
    const tagRegex = /#([a-zA-Z][a-zA-Z0-9_-]*)/g;
    
    let match;
    while ((match = tagRegex.exec(text)) !== null) {
      const tag = match[1];
      const normalized = this.normalizeTag(tag);
      
      if (!tags.includes(normalized)) {
        tags.push(normalized);
      }
    }

    return tags;
  }

  /**
   * Extract query blocks in format ?query{...}
   */
  private extractQueryBlocks(text: string): string[] {
    const queries: string[] = [];
    const queryRegex = /\?(\w+)\{([^}]+)\}/g;
    
    let match;
    while ((match = queryRegex.exec(text)) !== null) {
      queries.push(match[0]);
    }

    return queries;
  }

  /**
   * Normalize link target for consistency
   */
  private normalizeLink(link: string): string {
    // Convert to lowercase
    let normalized = link.toLowerCase();
    
    // Replace spaces with hyphens
    normalized = normalized.replace(/\s+/g, '-');
    
    // Remove special characters except hyphens and underscores
    normalized = normalized.replace(/[^\w\-_]/g, '');
    
    // Trim hyphens from ends
    normalized = normalized.replace(/^-+|-+$/g, '');
    
    return normalized;
  }

  /**
   * Normalize tag name
   */
  private normalizeTag(tag: string): string {
    // Resolve aliases
    const definition = this.tagDefinitions.get(tag);
    if (definition && definition.name !== tag) {
      return definition.name;
    }
    
    return tag.toLowerCase();
  }

  /**
   * Create wiki-link reference
   */
  createWikiLink(target: string, alias?: string): string {
    if (alias && alias !== target) {
      return `[[${target}|${alias}]]`;
    }
    return `[[${target}]]`;
  }

  /**
   * Create tag reference
   */
  createTag(tag: string): string {
    const normalized = this.normalizeTag(tag);
    const definition = this.tagDefinitions.get(normalized);
    
    if (definition && definition.name !== normalized) {
      // Use canonical name but keep original casing if it's an alias
      return `#${normalized}`;
    }
    
    return `#${tag}`;
  }

  /**
   * Register a custom tag definition
   */
  registerTag(definition: TagDefinition): void {
    this.tagDefinitions.set(definition.name, definition);
    
    for (const alias of definition.aliases) {
      this.tagDefinitions.set(alias, { ...definition, name: definition.name });
    }
  }

  /**
   * Register link alias
   */
  registerAlias(alias: string, target: string): void {
    this.linkAliases.set(alias.toLowerCase(), target.toLowerCase());
  }

  /**
   * Resolve link alias
   */
  resolveAlias(alias: string): string | null {
    return this.linkAliases.get(alias.toLowerCase()) || null;
  }

  /**
   * Get tag definition
   */
  getTagDefinition(name: string): TagDefinition | null {
    return this.tagDefinitions.get(name) || null;
  }

  /**
   * Check if tag exists
   */
  hasTag(name: string): boolean {
    return this.tagDefinitions.has(name.toLowerCase());
  }

  /**
   * Get all registered tags
   */
  getAllTags(): string[] {
    const tags = new Set<string>();
    for (const def of this.tagDefinitions.values()) {
      tags.add(def.name);
    }
    return Array.from(tags);
  }

  /**
   * Infer node type from tag or link context
   */
  inferNodeType(tags: string[], context?: string): string {
    // Check for type hints in tags
    const typeIndicators = {
      'project': ['project', 'proj', 'planning'],
      'task': ['task', 'todo', 'action', 'to-do'],
      'meeting': ['meeting', 'call', 'sync', 'standup'],
      'person': ['person', 'contact', 'people', 'team'],
      'document': ['doc', 'document', 'file', 'pdf'],
      'idea': ['idea', 'concept', 'thought', 'brainstorm'],
      'note': ['note', 'notebook', 'journal'],
      'resource': ['resource', 'link', 'reference', 'tool'],
    };

    for (const [type, indicators] of Object.entries(typeIndicators)) {
      for (const tag of tags) {
        if (indicators.includes(tag.toLowerCase())) {
          return type;
        }
      }
    }

    // Infer from context keywords
    if (context) {
      const lowerContext = context.toLowerCase();
      if (/meet|call|zoom|teams/.test(lowerContext)) return 'meeting';
      if (/todo|need to|must|should/.test(lowerContext)) return 'task';
      if (/idea|think|what if|imagine/.test(lowerContext)) return 'idea';
    }

    return 'note'; // Default
  }

  /**
   * Build relationship suggestions from parsed content
   */
  suggestRelationships(links: WikiLink[]): Array<{
    from: string;
    to: string;
    type: string;
    confidence: number;
  }> {
    const relationships: Array<{
      from: string;
      to: string;
      type: string;
      confidence: number;
    }> = [];

    // Group links by context
    const contexts = new Map<string, string[]>();
    for (const link of links) {
      if (!contexts.has(link.context)) {
        contexts.set(link.context, []);
      }
      contexts.get(link.context)!.push(link.target);
    }

    // Links appearing together are likely related
    for (const [, targets] of contexts.entries()) {
      if (targets.length > 1) {
        for (let i = 0; i < targets.length; i++) {
          for (let j = i + 1; j < targets.length; j++) {
            relationships.push({
              from: targets[i],
              to: targets[j],
              type: 'related_to',
              confidence: 0.7,
            });
          }
        }
      }
    }

    return relationships;
  }
}

// Export singleton instance
export const wikiParser = new WikiParser();
