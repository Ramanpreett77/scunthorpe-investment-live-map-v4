# Security and history audit

Audit run against the working tree and all reachable Git commits on 21 September 2026.

## Findings

- No literal Google API key, Apps Script secret, or write-capable Google Sheet ID was found in the current files or reachable Git history.
- `index.html` previously contained empty configuration values for a registration endpoint and a Sheet CSV URL. They were not credentials or IDs, but they have been moved to the placeholder-only `config.js`.
- The former public `Investor-Criteria-Form.html` and a hard-coded sample investor list appeared in earlier commits. The file is removed from the current tree and the public matching UI/list is removed from `index.html`. The old commits still exist in Git history until the repository history is rewritten.
- The EPC lookup previously allowed a visitor to paste an EPC API key into browser local storage. No key was present in the repository. Do not paste a personal or shared API key into the public site; use the official EPC register link or a server-side proxy with a secret store if that lookup is reintroduced.

## Required repository action

Because old commits contain the retired sample investor content, remove it from the public GitHub history if complete removal is required. Make a backup first, then use a history-rewrite tool such as `git filter-repo` to remove `Investor-Criteria-Form.html` and scrub the old investor block from historical `index.html` versions. Force-push the rewritten `main` branch only after checking the result, and invalidate any old clones. A history rewrite cannot be performed safely against GitHub from this workspace without your explicit push access.

No credential rotation is indicated by this audit because no actual API key or write-capable Sheet ID was found. If you find a real credential in GitHub's secret scanning, rotate/revoke it before deleting the file; deleting a file alone does not revoke a credential.
