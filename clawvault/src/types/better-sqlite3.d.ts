// Type declarations for better-sqlite3
declare module 'better-sqlite3' {
  interface Database {
    exec(sql: string): void;
    pragma(statement: string): any;
    prepare(sql: string): Statement;
    transaction(fn: Function): Function;
    close(): void;
  }

  interface Statement {
    run(...params: any[]): RunResult;
    get(...params: any[]): any;
    all(...params: any[]): any[];
    iterate(...params: any[]): IterableIterator<any>;
    map(...params: any[]): Map<any, any>;
    pluck(toggleState?: boolean): this;
    bind(...params: any[]): this;
    columnNames: string[];
    reader: boolean;
  }

  interface RunResult {
    changes: number;
    lastInsertRowid: number | null;
  }
}
