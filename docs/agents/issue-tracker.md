# Issue tracker: GitHub

Issues and PRDs for this repository live in GitHub Issues. Use the `gh` CLI from inside the clone so it infers the repository from the configured remote.

## Common operations

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."`
- Close: `gh issue close <number> --comment "..."`

GitHub shares numbering between issues and pull requests. Resolve an ambiguous reference with `gh pr view <number>` and fall back to `gh issue view <number>`.

## Pull requests as a triage surface

**PRs as a request surface: no.** External pull requests are reviewed as code contributions, not treated as feature-request tickets by the triage workflow.

When a skill says to publish work to the issue tracker, create a GitHub issue. When it says to fetch a ticket, use `gh issue view <number> --comments`.
