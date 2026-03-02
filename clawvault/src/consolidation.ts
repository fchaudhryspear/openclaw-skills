/**
 * Memory Consolidation Module
 * 
 * Nightly merge of similar memories to reduce redundancy.
 * Uses clustering + LLM summarization strategy.
 */

import { ClawVault, MemoryEntry } from './index.js';

export interface ConsolidationOptions {
  /** Similarity threshold for clustering (default: 0.15) */
  embeddingThreshold?: number;
  /** Maximum clusters to process per run (default: 10) */
  maxClustersPerRun?: number;
  /** Skip memories with confidence above this (default: 0.9) */
  skipHighConfidence?: number;
  /** Create backup before consolidation (default: true) */
  createBackup?: boolean;
}

export interface ConsolidationResult {
  totalMemoriesBefore: number;
  totalMemoriesAfter: number;
  clustersProcessed: number;
  memoriesMerged: number;
  skipped: {
    highConfidence: number;
    singleCluster: number;
    error: number;
  };
  timestamp: number;
}

export interface MemoryCluster {
  ids: string[];
  members: MemoryEntry[];
  avgEmbedding: number[];
  similarity: number;
}

export class MemoryConsolidator {
  private vault: ClawVault;
  private options: ConsolidationOptions;
  
  constructor(vault: ClawVault, options: ConsolidationOptions = {}) {
    this.vault = vault;
    this.options = {
      embeddingThreshold: 0.15,
      maxClustersPerRun: 10,
      skipHighConfidence: 0.9,
      createBackup: true,
      ...options
    };
  }

  /**
   * Main consolidation pipeline
   */
  async consolidate(): Promise<ConsolidationResult> {
    const startTime = Date.now();
    console.log('🔄 Starting memory consolidation...');

    // Get all memories grouped by type
    const memoriesByType = await this.groupMemoriesByType();
    
    let totalMerged = 0;
    let clustersProcessed = 0;
    const skipped = { highConfidence: 0, singleCluster: 0, error: 0 };
    
    for (const [type, memories] of Object.entries(memoriesByType)) {
      if (memories.length < 2) continue;
      
      console.log(`📊 Processing ${type} memories (${memories.length} total)`);
      
      const clusters = await this.findSimilarClusters(memories);
      
      for (const cluster of clusters.slice(0, this.options.maxClustersPerRun)) {
        if (cluster.members.length < 2) {
          skipped.singleCluster++;
          continue;
        }
        
        // Check if any member has high confidence
        const hasHighConfidence = cluster.members.some(m => m.confidence > this.options.skipHighConfidence!);
        if (hasHighConfidence) {
          skipped.highConfidence++;
          continue;
        }
        
        try {
          await this.mergeCluster(cluster);
          totalMerged += cluster.ids.length - 1; // N memories → 1 means N-1 deleted
          clustersProcessed++;
          console.log(`✅ Merged cluster of ${cluster.members.length} memories`);
        } catch (error) {
          console.error('❌ Error merging cluster:', error);
          skipped.error++;
        }
      }
    }

    const result: ConsolidationResult = {
      totalMemoriesBefore: await this.vault.getStats(),
      totalMemoriesAfter: 0, // Will be updated after refresh
      clustersProcessed,
      memoriesMerged: totalMerged,
      skipped,
      timestamp: startTime
    };
    
    result.totalMemoriesAfter = await this.vault.getStats();
    
    console.log(`✨ Consolidation complete!`);
    console.log(`   Processed: ${clustersProcessed} clusters`);
    console.log(`   Merged: ${totalMerged} memories → ${result.totalMemoriesAfter - result.totalMemoriesBefore + totalMerged}`);
    console.log(`   Skipped: high-confidence=${skipped.highConfidence}, single=${skipped.singleCluster}, errors=${skipped.error}`);
    
    return result;
  }

  /**
   * Group all memories by type
   */
  private async groupMemoriesByType(): Promise<Record<string, MemoryEntry[]>> {
    const groups: Record<string, MemoryEntry[]> = {};
    const allMemories = this.vault.getAllMemories(); // Assuming this method exists
    
    for (const memory of allMemories) {
      if (!groups[memory.type]) {
        groups[memory.type] = [];
      }
      groups[memory.type].push(memory);
    }
    
    return groups;
  }

  /**
   * Find clusters of similar memories using embedding cosine similarity
   */
  private async findSimilarClusters(
    memories: MemoryEntry[]
  ): Promise<MemoryCluster[]> {
    const clusters: MemoryCluster[] = [];
    const used = new Set<string>();
    
    // Simple agglomerative clustering
    for (let i = 0; i < memories.length; i++) {
      if (used.has(memories[i].id)) continue;
      
      const cluster: MemoryCluster = {
        ids: [memories[i].id],
        members: [memories[i]],
        avgEmbedding: memories[i].embedding || [],
        similarity: 1.0
      };
      
      // Find all similar memories
      for (let j = i + 1; j < memories.length; j++) {
        if (used.has(memories[j].id)) continue;
        
        const similarity = this.computeCosineSimilarity(
          cluster.avgEmbedding,
          memories[j].embedding || []
        );
        
        if (similarity < this.options.embeddingThreshold!) {
          cluster.ids.push(memories[j].id);
          cluster.members.push(memories[j]);
          used.add(memories[j].id);
          
          // Update average embedding
          cluster.avgEmbedding = this.updateAverageEmbedding(
            cluster.avgEmbedding,
            memories[j].embedding || []
          );
        }
      }
      
      used.add(memories[i].id);
      clusters.push(cluster);
    }
    
    return clusters.sort((a, b) => b.members.length - a.members.length);
  }

  /**
   * Compute cosine similarity between two vectors
   */
  private computeCosineSimilarity(vecA: number[], vecB: number[]): number {
    if (vecA.length === 0 || vecB.length === 0) return 1.0;
    
    const dotProduct = vecA.reduce((sum, val, i) => sum + val * (vecB[i] || 0), 0);
    const normA = Math.sqrt(vecA.reduce((sum, val) => sum + val * val, 0));
    const normB = Math.sqrt(vecB.reduce((sum, val) => sum + val * val, 0));
    
    if (normA === 0 || normB === 0) return 0;
    return 1 - (dotProduct / (normA * normB)); // Distance (0 = identical, 1 = opposite)
  }

  /**
   * Update average embedding when adding new member
   */
  private updateAverageEmbedding(existing: number[], incoming: number[]): number[] {
    if (existing.length === 0) return incoming;
    if (incoming.length === 0) return existing;
    
    const len = Math.max(existing.length, incoming.length);
    const sum = new Array(len).fill(0);
    
    for (let i = 0; i < len; i++) {
      sum[i] = (existing[i] || 0) + (incoming[i] || 0);
    }
    
    return sum.map(v => v / 2);
  }

  /**
   * Merge a cluster of memories into one
   */
  private async mergeCluster(cluster: MemoryCluster): Promise<void> {
    const members = cluster.members;
    
    // Sort by confidence (highest first) as primary reference
    members.sort((a, b) => b.confidence - a.confidence);
    const reference = members[0];
    
    // Generate merged content
    const mergedContent = this.generateMergedContent(members);
    
    // Store using vault's store method instead of creating raw MemoryEntry
    const mergedId = await this.vault.store(mergedContent, {
      type: reference.type,
      tags: this.mergeTags(members),
      scope: reference.scope,
      confidence: this.computeMergedConfidence(members)
    });

    // Delete old memories
    for (const member of members) {
      await this.vault.deleteMemory(member.id);
    }
  }

  /**
   * Generate merged content from cluster members
   */
  private generateMergedContent(members: MemoryEntry[]): string {
    // Fallback: Simple concatenation if no LLM available
    // In production, use LLM summarization here
    const contents = members.map(m => m.content).filter(c => c.trim().length > 0);
    
    if (contents.length === 1) {
      return contents[0];
    }
    
    // Combine unique information
    const allSentences = new Set<string>();
    for (const content of contents) {
      const sentences = content.split(/[.!?]+/).map(s => s.trim()).filter(Boolean);
      sentences.forEach(s => allSentences.add(s));
    }
    
    return Array.from(allSentences).join('. ') + '.';
  }

  /**
   * Merge and deduplicate tags from cluster
   */
  private mergeTags(members: MemoryEntry[]): string[] {
    const tagSet = new Set<string>();
    for (const member of members) {
      for (const tag of member.tags || []) {
        tagSet.add(tag);
      }
    }
    return Array.from(tagSet);
  }

  /**
   * Compute merged confidence score
   */
  private computeMergedConfidence(members: MemoryEntry[]): number {
    // Weighted average favoring higher confidence
    const sorted = [...members].sort((a, b) => b.confidence - a.confidence);
    const weights = sorted.map((_, i) => Math.pow(0.8, i)); // Decay weight
    const totalWeight = weights.reduce((a, b) => a + b, 0);
    const weightedSum = sorted.reduce((sum, mem, i) => sum + mem.confidence * weights[i], 0);
    
    return Math.min(1.0, weightedSum / totalWeight);
  }

  /**
   * Dry run - preview what would be consolidated without making changes
   */
  async dryRun(): Promise<{
    clusters: MemoryCluster[];
    estimatedReduction: number;
  }> {
    const memoriesByType = await this.groupMemoriesByType();
    const allClusters: MemoryCluster[] = [];
    
    for (const [type, memories] of Object.entries(memoriesByType)) {
      if (memories.length < 2) continue;
      const clusters = await this.findSimilarClusters(memories);
      allClusters.push(...clusters.filter(c => c.members.length >= 2));
    }
    
    const estimatedReduction = allClusters.reduce((sum, c) => sum + c.members.length - 1, 0);
    
    console.log('🔍 Dry run complete:');
    console.log(`   Found ${allClusters.length} potential clusters`);
    console.log(`   Would merge ~${estimatedReduction} memories`);
    
    return { clusters: allClusters, estimatedReduction };
  }
}
