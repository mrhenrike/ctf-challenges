# Writing Style System — André Henrique CTF Writeups

Este diretório contém o sistema completo de estilo e templates para os writeups do repositório.
Baseado na análise de 10 artigos originais do Medium @mrhenrike.

## Arquivos

| File | Description |
|------|-------------|
| `BASELINE.md` | Análise completa do padrão de escrita: anatomia, emojis, tom, progressão narrativa, benchmark |
| `TEMPLATE.md` | Template markdown completo pronto para preencher |
| `PROMPT.md` | Prompt para usar com LLMs ao gerar ou revisar writeups |
| `MITRE_REFERENCE.md` | Referência rápida de TTPs MITRE ATT&CK, D3FEND, NIST, C2M2, CISA para CTF |
| `scripts/exploit-template.sh` | Template de script de exploração |

## Uso Rápido

1. Copiar `TEMPLATE.md` para o diretório do writeup
2. Renomear para `README.md`
3. Preencher todos os `[PLACEHOLDER]`
4. Usar `PROMPT.md` como instrução para LLM quando gerar conteúdo
5. Consultar `MITRE_REFERENCE.md` ao mapear TTPs

## Regras Absolutas

1. NUNCA usar travessão "—" em texto corrido
2. SEMPRE terminar com `Thanks guys!! (❍ᴥ❍ʋ)`
3. SEMPRE explicar o PORQUÊ antes do COMO
4. SEMPRE incluir MITRE ATT&CK mapping
5. SEMPRE incluir seção de remediação com frameworks
6. NUNCA usar HackingArticles como fonte primária
