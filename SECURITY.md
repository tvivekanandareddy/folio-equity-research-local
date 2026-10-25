# Credential handling

This is a local, single-user application. Start it on `127.0.0.1`; it has no login or public-service abuse controls.

- Create `.env` from the blank `.env.example` and supply only your own optional credentials.
- Do not commit `.env`, provider keys, database connection strings, downloaded reports, logs, or research history. `.gitignore` does not remove files already committed.
- Provider credentials are read by Python on the backend and are not needed in browser code.
- Review staged changes and Git history for secrets before publishing changes. If a credential is accidentally published, revoke it with the provider; deleting the file is insufficient.
- Anyone cloning the source must configure their own accounts and credentials. The repository does not grant access to the author's services.
