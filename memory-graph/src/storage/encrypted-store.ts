/**
 * Encrypted Storage Backend - AES-256-GCM encryption at rest
 */

import * as crypto from 'crypto';
import * as fs from 'fs/promises';
import * as path from 'path';
import { Node, Edge, AuditEntry } from '../model/types';

const ENCRYPTION_ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;
const TAG_LENGTH = 16;
const KEY_DERIVATION_ITERATIONS = 100000;
const KEY_LENGTH = 32;
const SALT_LENGTH = 32;

export class EncryptedStore {
  private key: Buffer;
  private storagePath: string;
  private nodesFile: string;
  private edgesFile: string;
  private auditFile: string;

  constructor(storagePath: string, encryptionKey: string) {
    this.storagePath = storagePath;
    this.nodesFile = path.join(storagePath, 'nodes.enc');
    this.edgesFile = path.join(storagePath, 'edges.enc');
    this.auditFile = path.join(storagePath, 'audit.enc');
    this.key = this.deriveKey(encryptionKey);
  }

  /**
   * Derive encryption key from password using PBKDF2
   */
  private deriveKey(password: string): Buffer {
    const salt = process.env.ENCRYPTION_SALT 
      ? Buffer.from(process.env.ENCRYPTION_SALT, 'hex')
      : crypto.randomBytes(SALT_LENGTH);
    
    return crypto.pbkdf2Sync(password, salt, KEY_DERIVATION_ITERATIONS, KEY_LENGTH, 'sha256');
  }

  /**
   * Encrypt data with AES-256-GCM
   */
  encrypt(data: unknown): Buffer {
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ENCRYPTION_ALGORITHM, this.key, iv);
    
    const plaintext = JSON.stringify(data);
    const ciphertext = Buffer.concat([
      cipher.update(plaintext, 'utf8'),
      cipher.final(),
    ]);
    
    const tag = cipher.getAuthTag();
    
    // Format: salt (if needed) | iv | tag | ciphertext
    return Buffer.concat([iv, tag, ciphertext]);
  }

  /**
   * Decrypt data with AES-256-GCM
   */
  decrypt(encrypted: Buffer): unknown {
    if (encrypted.length < IV_LENGTH + TAG_LENGTH) {
      throw new Error('Invalid encrypted data length');
    }

    const iv = encrypted.subarray(0, IV_LENGTH);
    const tag = encrypted.subarray(IV_LENGTH, IV_LENGTH + TAG_LENGTH);
    const ciphertext = encrypted.subarray(IV_LENGTH + TAG_LENGTH);

    const decipher = crypto.createDecipheriv(ENCRYPTION_ALGORITHM, this.key, iv);
    decipher.setAuthTag(tag);

    const plaintext = Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);

    return JSON.parse(plaintext.toString('utf8'));
  }

  /**
   * Initialize storage directory and files
   */
  async initialize(): Promise<void> {
    await fs.mkdir(this.storagePath, { recursive: true });
    
    // Check if files exist, create empty if not
    try {
      await fs.access(this.nodesFile);
    } catch {
      await this.writeNodes([]);
    }
    
    try {
      await fs.access(this.edgesFile);
    } catch {
      await this.writeEdges([]);
    }
    
    try {
      await fs.access(this.auditFile);
    } catch {
      await this.writeAudit([]);
    }
  }

  /**
   * Read all nodes
   */
  async readNodes(): Promise<Node[]> {
    try {
      const encrypted = await fs.readFile(this.nodesFile);
      return this.decrypt(encrypted) as Node[];
    } catch (error) {
      if ((error as Node).code === 'ENOENT') {
        return [];
      }
      throw error;
    }
  }

  /**
   * Write all nodes
   */
  async writeNodes(nodes: Node[]): Promise<void> {
    const encrypted = this.encrypt(nodes);
    await fs.writeFile(this.nodesFile, encrypted);
  }

  /**
   * Read all edges
   */
  async readEdges(): Promise<Edge[]> {
    try {
      const encrypted = await fs.readFile(this.edgesFile);
      return this.decrypt(encrypted) as Edge[];
    } catch (error) {
      if ((error as Node).code === 'ENOENT') {
        return [];
      }
      throw error;
    }
  }

  /**
   * Write all edges
   */
  async writeEdges(edges: Edge[]): Promise<void> {
    const encrypted = this.encrypt(edges);
    await fs.writeFile(this.edgesFile, encrypted);
  }

  /**
   * Read audit log
   */
  async readAudit(): Promise<AuditEntry[]> {
    try {
      const encrypted = await fs.readFile(this.auditFile);
      return this.decrypt(encrypted) as AuditEntry[];
    } catch (error) {
      if ((error as Node).code === 'ENOENT') {
        return [];
      }
      throw error;
    }
  }

  /**
   * Append to audit log
   */
  async appendAudit(entry: AuditEntry): Promise<void> {
    const entries = await this.readAudit();
    entries.push(entry);
    const encrypted = this.encrypt(entries);
    await fs.writeFile(this.auditFile, encrypted);
  }

  /**
   * Find a node by ID
   */
  async findNode(id: string): Promise<Node | null> {
    const nodes = await this.readNodes();
    return nodes.find(n => n.id === id) || null;
  }

  /**
   * Add a new node
   */
  async addNode(node: Node): Promise<void> {
    const nodes = await this.readNodes();
    if (nodes.some(n => n.id === node.id)) {
      throw new Error(`Node with id '${node.id}' already exists`);
    }
    nodes.push(node);
    await this.writeNodes(nodes);
  }

  /**
   * Update an existing node
   */
  async updateNode(id: string, updates: Partial<Node>): Promise<Node> {
    const nodes = await this.readNodes();
    const index = nodes.findIndex(n => n.id === id);
    
    if (index === -1) {
      throw new Error(`Node with id '${id}' not found`);
    }
    
    nodes[index] = { ...nodes[index], ...updates, updatedAt: new Date() };
    await this.writeNodes(nodes);
    return nodes[index];
  }

  /**
   * Delete a node
   */
  async deleteNode(id: string): Promise<boolean> {
    const nodes = await this.readNodes();
    const index = nodes.findIndex(n => n.id === id);
    
    if (index === -1) {
      return false;
    }
    
    nodes.splice(index, 1);
    await this.writeNodes(nodes);
    return true;
  }

  /**
   * Find edges by source or target
   */
  async findEdgesByNode(nodeId: string): Promise<Edge[]> {
    const edges = await this.readEdges();
    return edges.filter(e => e.from === nodeId || e.to === nodeId);
  }

  /**
   * Add a new edge
   */
  async addEdge(edge: Edge): Promise<void> {
    const edges = await this.readEdges();
    if (edges.some(e => e.id === edge.id)) {
      throw new Error(`Edge with id '${edge.id}' already exists`);
    }
    edges.push(edge);
    await this.writeEdges(edges);
  }

  /**
   * Delete an edge
   */
  async deleteEdge(id: string): Promise<boolean> {
    const edges = await this.readEdges();
    const index = edges.findIndex(e => e.id === id);
    
    if (index === -1) {
      return false;
    }
    
    edges.splice(index, 1);
    await this.writeEdges(edges);
    return true;
  }

  /**
   * Backup encrypted data
   */
  async backup(): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupDir = path.join(this.storagePath, 'backups', timestamp);
    await fs.mkdir(backupDir, { recursive: true });
    
    const nodes = await this.readNodes();
    const edges = await this.readEdges();
    const audit = await this.readAudit();
    
    const backupData = {
      timestamp,
      nodes,
      edges,
      audit,
    };
    
    const backupPath = path.join(backupDir, 'backup.enc');
    const encrypted = this.encrypt(backupData);
    await fs.writeFile(backupPath, encrypted);
    
    return backupPath;
  }

  /**
   * Restore from backup
   */
  async restore(backupPath: string): Promise<void> {
    const encrypted = await fs.readFile(backupPath);
    const backupData = this.decrypt(encrypted) as {
      timestamp: string;
      nodes: Node[];
      edges: Edge[];
      audit: AuditEntry[];
    };
    
    await this.writeNodes(backupData.nodes);
    await this.writeEdges(backupData.edges);
    await this.writeAudit(backupData.audit);
  }

  /**
   * Verify data integrity
   */
  async verifyIntegrity(): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];
    
    try {
      const nodes = await this.readNodes();
      JSON.stringify(nodes);
    } catch (error) {
      errors.push(`Nodes file corrupted: ${(error as Error).message}`);
    }
    
    try {
      const edges = await this.readEdges();
      JSON.stringify(edges);
    } catch (error) {
      errors.push(`Edges file corrupted: ${(error as Error).message}`);
    }
    
    try {
      const audit = await this.readAudit();
      JSON.stringify(audit);
    } catch (error) {
      errors.push(`Audit file corrupted: ${(error as Error).message}`);
    }
    
    return { valid: errors.length === 0, errors };
  }

  /**
   * Rotate encryption keys (advanced feature)
   */
  async rotateKey(newEncryptionKey: string): Promise<void> {
    // Decrypt current data
    const nodes = await this.readNodes();
    const edges = await this.readEdges();
    const audit = await this.readAudit();
    
    // Temporarily store in memory
    const oldKey = this.key;
    this.key = this.deriveKey(newEncryptionKey);
    
    // Re-encrypt with new key
    await this.writeNodes(nodes);
    await this.writeEdges(edges);
    await this.writeAudit(audit);
    
    // Restore old key until we confirm success
    this.key = oldKey;
  }
}
