# Visual Learning Module Guide

Create a self-contained `learning-module.html` for this repository that explains the architecture visually and makes the codebase easy to review later.

## Output

- `learning-module.html` — offline single-file interactive guide
- `docs/visual-learning-module-guide.md` — repeatable workflow and prompt

## Workflow

1. Discover the repo structure: source, tests, config, scripts, assets, docs.
2. Read the implementation and identify entry points, major modules, data flow, state management, persistence, networking, and error handling.
3. Extract the teaching model: what the repo does, why it exists, what patterns it uses, and what tradeoffs matter.
4. Generate visual sections: overview, architecture, data flow, key files, setup, debugging notes, extension points, and interview talking points.
5. Keep the HTML offline-first: embedded CSS, minimal JS, no CDNs, system fonts.

## Suggested HTML structure

```text
learning-module.html
├── Hero: repo name, purpose, stack
├── Overview: what it does and why it exists
├── Architecture: module map and dependency diagram
├── Data Flow: user/input/API/state/output path
├── Key Files: annotated walkthrough
├── Patterns: architecture and design patterns
├── Setup: run/test/debug notes
└── Interview Notes: tradeoffs and improvement ideas
```

## Visuals to include when appropriate

- Component hierarchy diagram
- Request/state/data flow diagram
- Build/test pipeline diagram
- Persistence map
- Error handling path
- Extension seams and refactor opportunities

## Coding-agent prompt

```text
Analyze this repository and generate a self-contained `learning-module.html` that teaches the codebase visually. Read the full repo structure, config files, source files, tests, scripts, and docs. Identify the purpose, tech stack, entry points, modules, data flow, state management, persistence, networking, and error handling. Include diagrams, key file walkthroughs, annotated snippets, setup/debugging notes, design patterns, tradeoffs, and interview talking points. Use embedded CSS and minimal JS only. Keep it specific to this repository.
```

## Quality bar

Someone should understand the repo in 10–15 minutes without opening every source file.