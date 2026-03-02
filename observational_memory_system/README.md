# Observational Memory System

## Overview

This project aims to design, develop, and test a security-focused Observational Memory system. The system will capture, encrypt, store, and retrieve observational data, ensuring high levels of security, data privacy, and integrity. Best practices from ClawVault (ClosedClaw) will be incorporated to streamline development and enhance security.

## Core Principles

*   **Security First:** All design and implementation decisions prioritize security, encryption, and access control.
*   **Data Privacy:** Strict measures are in place to protect the privacy of stored observational data.
*   **Efficiency:** Leverage existing robust libraries and patterns to reduce build time without compromising security.

## Custom Security Policy

1.  **Data at Rest Encryption:** All observational memory data stored on disk MUST be encrypted using strong, modern encryption algorithms (e.g., AES-256-GCM).
2.  **Access Control:** Access to raw encrypted memory data files must be strictly controlled, allowing only the Observational Memory system daemon (or authorized processes) to read/write. File permissions should be `0600` (owner read/write only).
3.  **In-Memory Security:** Sensitive data (decrypted memory content, encryption keys) should only reside in memory for the shortest possible duration. It must be actively purged or zeroed out from memory after use.
4.  **Key Management:**
    *   Encryption keys for the observational memory data MUST NOT be stored alongside the encrypted data.
    *   Keys should be derived from a master passphrase using a robust Key Derivation Function (KDF) like `scrypt` or `argon2`.
    *   The master passphrase itself should never be stored on disk and should be provided at system startup (e.g., by the user or an external secret management system).
5.  **Auditability & Logging:** All access attempts (successful or failed) to the Observational Memory system, including key derivation and data decryption, must be logged for auditing purposes. Logs themselves must be secured.
6.  **No Plaintext Storage:** Under no circumstances should observational memory data, especially sensitive observations, be stored in plaintext on disk.
7.  **Data Minimization:** Only necessary observational data should be stored. Policies for data retention and automatic purging of old/irrelevant data should be implemented.
8.  **Integrity Checks:** Mechanisms should be in place to detect tampering or corruption of encrypted memory data.

## High-Level Architecture

The system will consist of the following main components:

1.  **Memory Capture Agent:**
    *   **Role:** Observes system events, user interactions, or other data points.
    *   **Functionality:** Collects and preprocesses observational data, then transmits it to the Memory Storage Manager.
2.  **Memory Storage Manager (Daemon):**
    *   **Role:** Core component, responsible for all data handling and security.
    *   **Functionality:**
        *   Receives raw observational data.
        *   Encrypts data using a derived key (AES-256-GCM).
        *   Stores encrypted data in the Encrypted Memory Vault.
        *   Manages access, decryption, and retrieval requests.
        *   Handles key derivation (scrypt/argon2) and secure in-memory key management.
        *   Maintains audit logs.
3.  **Encrypted Memory Vault:**
    *   **Role:** Secure persistent storage for encrypted observational memory.
    *   **Structure:** A designated directory/file structure on disk.
    *   **Security:** File permissions set to `0600`.
4.  **Memory Query/Retrieval Interface:**
    *   **Role:** Provides an API/CLI for authorized access to stored memory.
    *   **Functionality:** Communicates with the Memory Storage Manager to request and receive decrypted memory snippets.

## ClawVault (ClosedClaw) Best Practices Applied

*   **Existing Crypto Libraries:** Utilize well-vetted, secure cryptographic libraries (e.g., Node.js Crypto, Python's `cryptography`) for encryption and KDFs.
*   **Daemonization Patterns:** Implement robust daemonization, including PID file management and signal handling.
*   **Secure Configuration:** Configuration files (`config.json`) stored with `0600` permissions.
*   **Runtime Data Provisioning:** The Memory Storage Manager acts as a secure intermediary, providing decrypted memory data at runtime without exposing the raw encrypted vault or keys directly to client applications.

## Next Steps

1.  **Technology Stack Selection:** Choose appropriate programming language and libraries.
2.  **Detailed Design:** Break down each component into modules and define interfaces.
3.  **Proof of Concept:** Implement core encryption, decryption, and storage functionalities.
4.  **Testing:** Develop unit and integration tests, focusing on security aspects.
5.  **Refinement & Deployment.**
