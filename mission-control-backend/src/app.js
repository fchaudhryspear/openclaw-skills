'use strict';

/**
 * Mission Control — Outer API handler (legacy compatibility layer).
 * Primary logic is in mission-control/src/app.js.
 * This file forwards to the inner handler for SAM local dev compatibility.
 * 
 * @module MissionControlOuter
 * @version 2.2.0
 */

const inner = require('../mission-control/src/app');

// Re-export the Lambda handler
exports.lambdaHandler = inner.lambdaHandler;
