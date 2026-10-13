# VulnHub Writeup Pipeline

## Status

| Phase | VMs | Status |
|-------|-----|--------|
| Phase 0 (local files) | 7 | ✅ Done |
| Phase 1 (first batch) | 20 | 🔄 In Progress |
| Phase 2+ | 281+ | ⏳ Pending |

## VM Database

Full index at: `vulnhub/.vm-database.json` (308 entries from Ignitetechnologies/Vulnhub-CTF-Writeups)
Source: https://github.com/Ignitetechnologies/Vulnhub-CTF-Writeups

## Workflow per VM

1. Fetch HackingArticles article
2. Extract commands, technique steps, image URLs
3. Download key screenshots (3-5 per VM) → `images/`
4. Generate `README.md` (user's style: Step N headers, commands in blocks)
5. Generate `scripts/exploit.sh` with all commands
6. Commit

## Writing Style Guide

Based on mrhenrike's existing NOTES.md files and Medium articles:
- Header: `# VM Name — Writeup` + metadata block
- Attack chain table (one-line kill chain)
- Steps: `## Step N: Description`
- All commands in fenced code blocks
- Output shown as-is, with annotations
- Credential tables where applicable
- Brief technical explanation, no fluff

## Source priority

1. User's own Medium articles (@mrhenrike) — highest priority, personal style
2. HackingArticles (hackingarticles.in) — reference material
3. mzfr/vulnhub-writeups — additional reference
4. Other public GitHub repos — supplementary

## Medium articles to process (pending Brave browser connection)

| VM | Medium URL |
|----|-----------|
| DC Serie:6 | https://medium.com/@mrhenrike/vulnhub-dc-serie-6-walkthrough-35d2f712487 |
| Jigsaw:1 | https://medium.com/@mrhenrike/vulnhub-jigsaw-1-walkthrough-179e279f591a |
| Mission Pumpkin 1/3 | https://medium.com/@mrhenrike/vulnhub-mission-pumpkin-v1-0-1-3-garden-walkthrough-5736ddb0bd1a |
| Mission Pumpkin 2/3 | https://medium.com/@mrhenrike/vulnhub-mission-pumpkin-v1-0-2-3-raising-walkthrough-46bd43453888 |
| Mission Pumpkin 3/3 | https://medium.com/@mrhenrike/vulnhub-mission-pumpkin-v1-0-3-3-festival-walkthrough-cac7b216e26c |
| Zeus:1 | https://medium.com/@mrhenrike/vulnhub-zeus-1-walkthrough-7e2ad46c9ab9 |
| Matrix v3 | https://medium.com/@mrhenrike/vulnhub-matrix-v3-walkthrough-864db11df508 |
| Symfonos:1 | https://medium.com/@mrhenrike/vulnhub-symfonos-1-walkthrough-fdd94a1de4db |
| Unknown Device VM-1 | https://medium.com/@mrhenrike/vulnhub-unknown-device-vm-1-4011b395b7ea |
| Unknown Device VM-2 | https://medium.com/@mrhenrike/vulnhub-unknown-device-vm-2-84e612fc825d |

To process: open Brave browser (Claude Code extension installed) and run pipeline.
