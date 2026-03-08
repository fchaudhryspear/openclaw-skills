
// types.d.ts
/// <reference path="./node_modules/@types/node/index.d.ts" />
/// <reference path="./node_modules/@types/express/index.d.ts" />
/// <reference path="./node_modules/@types/cors/index.d.ts" />
/// <reference path="./node_modules/better-sqlite3/index.d.ts" />

// Module declarations
declare module 'better-sqlite3' {
  export class Database {
    constructor(file: string, options?: any);
    prepare(sql: string): any;
    all(sql: string, params?: any): any;
    close(): void;
  }
}

declare module 'cors' {
  function cors(options?: any): any;
  export default cors;
}
